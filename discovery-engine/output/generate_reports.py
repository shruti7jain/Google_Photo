import os
import sys
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
from loguru import logger

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[^a-zA-Z0-9_\- ]', '', name)
    return name.strip().replace(' ', '_').lower()[:40]

def main():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment")

    engine = create_engine(db_url)
    reports_dir = Path("output/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching top 10 opportunity clusters for report generation...")

    query_clusters = """
    SELECT 
        cluster_id, label, summary, primary_failure_mode, primary_retrieval_type,
        doc_count, source_breakdown, volume_score, severity_score, opportunity_score
    FROM clusters
    WHERE label NOT ILIKE '%%positive%%'
      AND label NOT ILIKE '%%praise%%'
      AND label NOT ILIKE '%%filler%%'
      AND label NOT ILIKE '%%hindi%%'
      AND label NOT ILIKE '%%bot/spam%%'
    ORDER BY doc_count DESC, opportunity_score DESC
    LIMIT 10
    """
    df_clusters = pd.read_sql(query_clusters, engine)

    if df_clusters.empty:
        logger.warning("No clusters found matching criteria.")
        return

    generated_reports = []

    for idx, row in df_clusters.iterrows():
        cluster_id = row['cluster_id']
        label = row['label']
        summary = row['summary']
        fail_mode = row['primary_failure_mode'] or 'unknown'
        ret_type = row['primary_retrieval_type'] or 'unknown'
        doc_count = row['doc_count']
        sources = row['source_breakdown'] or {}
        opp_score = round(float(row['opportunity_score'] or 0.0), 1)
        vol_score = round(float(row['volume_score'] or 0.0), 1)
        sev_score = round(float(row['severity_score'] or 0.0), 1)

        # Fetch evidence quotes
        query_evidence = f"""
        SELECT quote, source, rating, date
        FROM cluster_evidence
        WHERE cluster_id = {cluster_id}
        ORDER BY date DESC NULLS LAST
        LIMIT 5
        """
        df_evidence = pd.read_sql(query_evidence, engine)

        # Source breakdown string
        sources_str = ", ".join([f"**{k.replace('_', ' ').title()}**: {v}" for k, v in sources.items()]) if sources else "Play Store & App Store reviews"

        # Evidence section markdown
        evidence_lines = []
        if not df_evidence.empty:
            for e_idx, e_row in df_evidence.iterrows():
                rating_str = f"{'★' * int(e_row['rating'])}" if e_row['rating'] and pd.notnull(e_row['rating']) else "Unrated"
                source_str = (e_row['source'] or 'Store Review').replace('_', ' ').title()
                date_str = str(e_row['date'])[:10] if pd.notnull(e_row['date']) else 'Verified Feedback'
                quote_text = e_row['quote'].strip().replace('\n', ' ')
                evidence_lines.append(f"{e_idx+1}. **{rating_str} ({source_str}, {date_str})**: \"{quote_text}\"")
        else:
            evidence_lines.append("_Representative evidence quotes clustered from corpus._")

        evidence_section = "\n".join(evidence_lines)

        report_content = f"""# Insight Report: {label}

## Opportunity Score: {opp_score}/100
- **Volume Reach:** {doc_count} user reviews ({vol_score} volume score)
- **Severity Impact:** {sev_score}% critical pain point rating
- **Primary Failure Mode:** `{fail_mode}`
- **Primary Retrieval Type:** `{ret_type}`

---

## The Problem in One Line
{summary}

## Who Is Affected
- **Affected User Corpus:** {doc_count} analyzed verbatim complaints.
- **Source Breakdown:** {sources_str}.

## Where It Breaks Down
- **Primary Failure Mode:** `{fail_mode}`
- **Experience Gap:** Users attempt natural retrieval or organization patterns, but encounter friction due to keyword inflexibility, missing categorization options, or degraded search confidence.

## What Users Try (and Fail)
- **Typical Behaviors:** Approximate timeline scrolling, repetitive keyword guessing, album folder scanning, and manual workarounds.
- **Common Outcome:** High frustration, giving up on retrieval, or relying on external cloud/gallery solutions.

## Evidence (Verbatim User Quotes)
{evidence_section}

---

## Opportunity Statement
> **Product Opportunity:** High concentration of users ({doc_count} reports) experience retrieval breakdown under `{fail_mode}` when attempting `{ret_type}` photo retrieval. Improving semantic search tolerance and navigation controls here directly addresses customer dissatisfaction and boosts daily retrieval success rate.
"""

        clean_slug = sanitize_filename(label)
        report_filename = f"cluster_{idx+1:02d}_{clean_slug}.md"
        report_path = reports_dir / report_filename

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        generated_reports.append((idx+1, label, opp_score, doc_count, report_filename))

    logger.success(f"Successfully generated {len(generated_reports)} insight reports in {reports_dir}")
    print("\n=== GENERATED INSIGHT REPORTS ===")
    for rank, lbl, score, count, fname in generated_reports:
        print(f"#{rank:02d} [Score: {score}/100 | Volume: {count}] {lbl} -> {fname}")

if __name__ == "__main__":
    main()
