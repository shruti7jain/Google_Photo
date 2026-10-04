import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Discovery Engine API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
db_url = os.getenv("DATABASE_URL", "")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(db_url, connect_args={"connect_timeout": 3}) if db_url else None
db_is_reachable = True if engine else False

class ChatRequest(BaseModel):
    query: str


# ── Taxonomy: failure modes → hypothesis discovery zones ─────────────────────
# These groupings are discovery-stage patterns, NOT validated findings.
# Each zone maps to a hypothesis that was later validated through primary research.

FAILURE_ZONE_MAP = {
    "first_search_gap": {
        "label": "First Search Gap",
        "hypothesis": "H1",
        "description": "Memory is present but cannot be translated into a useful first search attempt",
        "signal": "Meaningful memory → weak first search expression",
        "modes": ["search_vocabulary_mismatch", "temporal_ambiguity", "location_imprecision", "visual_only_memory"],
        "color_class": "error",
    },
    "search_match_gap": {
        "label": "Search Match Gap",
        "hypothesis": "H2",
        "description": "A searchable clue exists, but results are too broad or poorly organized to isolate the photo",
        "signal": "Searchable clue → weak result match",
        "modes": ["no_album_structure", "wrong_confidence_signal"],
        "color_class": "secondary",
    },
    "refinement_gap": {
        "label": "Refinement Gap",
        "hypothesis": "H3",
        "description": "After a failed search, user cannot determine which clue to try next",
        "signal": "Failed search → unclear next clue",
        "modes": ["search_ux_breakdown"],
        "color_class": "tertiary",
    },
}

FAILURE_MODE_LABELS = {
    "search_vocabulary_mismatch": "Search Vocabulary Mismatch",
    "temporal_ambiguity": "Temporal Ambiguity",
    "location_imprecision": "Location Imprecision",
    "visual_only_memory": "Visual-Only Memory",
    "no_album_structure": "No Album Structure",
    "wrong_confidence_signal": "Wrong Confidence Signal",
    "search_ux_breakdown": "Search UX Breakdown",
    "data_loss": "Data Loss",
    "unknown": "Unknown",
}

RETRIEVAL_TYPE_LABELS = {
    "person_based": "People",
    "location_based": "Place / Location",
    "event_based": "Story / Experience",
    "object_based": "Object",
    "time_based": "Roughly When",
    "emotion_based": "Emotion / Feeling",
    "unknown": "Unknown",
}

OUTCOME_LABELS = {
    "failed": "Retrieval Failed",
    "partial": "Partial Result",
    "succeeded": "Retrieved Successfully",
    "unknown": "Outcome Unknown",
}

BEHAVIOR_LABELS = {
    "approximate_date_browsing": "Browsed by approximate date",
    "keyword_guessing": "Tried different keywords",
    "album_scanning": "Scanned albums manually",
    "asked_someone_else": "Asked someone else",
    "gave_up": "Gave up",
    "used_third_party_tool": "Used a third-party tool",
    "unknown_browsing": "Browsed without clear strategy",
}

SOURCE_LABELS = {
    "play_store": "Play Store",
    "app_store": "App Store",
    "reddit": "Reddit",
    "community": "Community",
}


# ── Safe query wrapper ────────────────────────────────────────────────────────

def safe_query(fn, default):
    """Run fn(); on any exception return default. Prevents a dead DB table
    from crashing the entire dashboard."""
    try:
        return fn()
    except Exception:
        return default


# ── Section 1: Pipeline counts ────────────────────────────────────────────────

def _fetch_pipeline_counts():
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
                COUNT(*) AS total_raw,
                SUM(CASE WHEN is_duplicate = false THEN 1 ELSE 0 END) AS total_filtered
            FROM raw_documents
        """)).fetchone()
    total_raw = int(row[0]) if row else 4128
    total_filtered = int(row[1]) if row else 2638
    # 1,241 is derived from the pipeline ratio (47.0 % of 2,638 search-relevant records).
    # It is NOT a live count from a tagged_documents WHERE clause.
    total_retrieval_relevant = int(total_filtered * (1241 / 2638))
    return total_raw, total_filtered, total_retrieval_relevant


def _fetch_source_breakdown():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT source, COUNT(*) AS cnt
            FROM raw_documents
            WHERE is_duplicate = false
            GROUP BY source
            ORDER BY cnt DESC
        """)).fetchall()
    return {row[0]: int(row[1]) for row in rows}


# ── Section 2: What users remember ───────────────────────────────────────────

def _fetch_memory_cues(denominator: int):
    """
    Distribution of memory cue sub-fields across retrieval-relevant tagged_documents.
    Only high-confidence records (failure_confidence >= 0.6); data_loss excluded.
    Returns None if tagged_documents has no qualifying rows.
    """
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
              SUM(CASE WHEN memory_cue IS NOT NULL
                        AND memory_cue->>'remembered_people' IS NOT NULL
                        AND memory_cue->>'remembered_people' NOT IN ('null','')
                   THEN 1 ELSE 0 END) AS person_based,
              SUM(CASE WHEN memory_cue IS NOT NULL
                        AND memory_cue->>'remembered_location' IS NOT NULL
                        AND memory_cue->>'remembered_location' NOT IN ('null','')
                   THEN 1 ELSE 0 END) AS location_based,
              SUM(CASE WHEN memory_cue IS NOT NULL
                        AND memory_cue->>'remembered_time' IS NOT NULL
                        AND memory_cue->>'remembered_time' NOT IN ('null','')
                   THEN 1 ELSE 0 END) AS time_based,
              SUM(CASE WHEN memory_cue IS NOT NULL
                        AND memory_cue->>'remembered_object' IS NOT NULL
                        AND memory_cue->>'remembered_object' NOT IN ('null','')
                   THEN 1 ELSE 0 END) AS object_based,
              SUM(CASE WHEN memory_cue IS NOT NULL
                        AND memory_cue->>'remembered_emotion' IS NOT NULL
                        AND memory_cue->>'remembered_emotion' NOT IN ('null','')
                   THEN 1 ELSE 0 END) AS emotion_based,
              COUNT(*) AS total_tagged
            FROM tagged_documents
            WHERE (primary_failure_mode IS NULL OR primary_failure_mode != 'data_loss')
              AND failure_confidence >= 0.6
              AND memory_cue IS NOT NULL
        """)).fetchone()

    if not row or int(row[5] or 0) == 0:
        return None

    total = int(row[5])
    denom = denominator if denominator > 0 else total

    cues = [
        {"key": "person_based",   "label": "People",           "icon": "group",                "count": int(row[0] or 0)},
        {"key": "location_based", "label": "Place / Location",  "icon": "location_on",          "count": int(row[1] or 0)},
        {"key": "time_based",     "label": "Roughly When",      "icon": "schedule",             "count": int(row[2] or 0)},
        {"key": "object_based",   "label": "Object",            "icon": "category",             "count": int(row[3] or 0)},
        {"key": "emotion_based",  "label": "Emotion / Feeling", "icon": "sentiment_satisfied",  "count": int(row[4] or 0)},
    ]
    for c in cues:
        c["pct"] = round(c["count"] / denom * 100, 1) if denom > 0 else 0.0
    cues.sort(key=lambda x: x["count"], reverse=True)

    return {
        "cues": cues,
        "total_tagged": total,
        "denominator": denom,
        "denominator_label": f"{denom:,} retrieval-relevant records",
        "note": "AI-extracted cues from public reviews. Labels reflect canonical classifier taxonomy.",
    }


# ── Section 3: Where retrieval breaks ────────────────────────────────────────

def _fetch_failure_zones(denominator: int):
    """
    Group primary_failure_mode into H1/H2/H3 discovery zones.
    Excludes data_loss and unknown; requires failure_confidence >= 0.6.
    Returns None if tagged_documents has no qualifying rows.
    """
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT primary_failure_mode, COUNT(*) AS cnt
            FROM tagged_documents
            WHERE primary_failure_mode IS NOT NULL
              AND primary_failure_mode NOT IN ('data_loss','unknown')
              AND failure_confidence >= 0.6
            GROUP BY primary_failure_mode
            ORDER BY cnt DESC
        """)).fetchall()

    if not rows:
        return None

    mode_counts = {row[0]: int(row[1]) for row in rows}
    total_classified = sum(mode_counts.values())
    denom = denominator if denominator > 0 else total_classified

    zones = []
    for zone_key, z in FAILURE_ZONE_MAP.items():
        zone_count = sum(mode_counts.get(m, 0) for m in z["modes"])
        mode_detail = [
            {
                "mode": m,
                "label": FAILURE_MODE_LABELS.get(m, m),
                "count": mode_counts.get(m, 0),
            }
            for m in z["modes"]
            if mode_counts.get(m, 0) > 0
        ]
        zones.append({
            "key": zone_key,
            "label": z["label"],
            "hypothesis": z["hypothesis"],
            "description": z["description"],
            "signal": z["signal"],
            "color_class": z["color_class"],
            "count": zone_count,
            "pct": round(zone_count / denom * 100, 1) if denom > 0 else 0.0,
            "modes": mode_detail,
        })

    return {
        "zones": zones,
        "total_classified": total_classified,
        "denominator": denom,
        "note": "Discovery pattern — requires primary validation",
    }


def _fetch_retrieval_type_dist(denominator: int):
    """Distribution of retrieval_types array elements across retrieval-relevant records."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT rt, COUNT(*) AS cnt
            FROM (
                SELECT UNNEST(retrieval_types) AS rt
                FROM tagged_documents
                WHERE retrieval_confidence >= 0.6
                  AND (primary_failure_mode IS NULL OR primary_failure_mode != 'data_loss')
            ) sub
            WHERE rt != 'unknown'
            GROUP BY rt
            ORDER BY cnt DESC
        """)).fetchall()

    if not rows:
        return []

    total = sum(int(r[1]) for r in rows)
    denom = denominator if denominator > 0 else total
    return [
        {
            "key": row[0],
            "label": RETRIEVAL_TYPE_LABELS.get(row[0], row[0]),
            "count": int(row[1]),
            "pct": round(int(row[1]) / denom * 100, 1) if denom > 0 else 0.0,
        }
        for row in rows
    ]


# ── Section 4: Verbatim evidence cards ───────────────────────────────────────

def _fetch_evidence_cards():
    """
    Structured evidence cards from tagged_documents with full Quote → Behavior → Problem trace.
    Filters: failure_confidence >= 0.6, text length >= 50, excludes data_loss and unknown.
    """
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                text_original, source, date,
                retrieval_types, primary_failure_mode,
                failure_evidence_quote, memory_cue, search_behavior,
                retrieval_description, failure_confidence
            FROM tagged_documents
            WHERE primary_failure_mode IS NOT NULL
              AND primary_failure_mode NOT IN ('data_loss','unknown')
              AND failure_confidence >= 0.6
              AND LENGTH(text_original) >= 50
            ORDER BY failure_confidence DESC
            LIMIT 60
        """)).fetchall()

    cards = []
    for row in rows:
        (text_original, source, date_val, retrieval_types_val, primary_fm,
         failure_quote, memory_cue_raw, search_behavior_raw,
         retrieval_desc, fail_conf) = row

        # ── Parse search_behavior JSONB ──
        outcome, behaviors, workaround = "unknown", [], False
        if search_behavior_raw:
            try:
                sb = (json.loads(search_behavior_raw)
                      if isinstance(search_behavior_raw, str)
                      else search_behavior_raw)
                outcome = sb.get("outcome", "unknown")
                behaviors = [
                    BEHAVIOR_LABELS.get(b, b)
                    for b in sb.get("behaviors", [])
                    if b not in ("unknown_browsing", "unknown")
                ]
                workaround = bool(sb.get("workaround_used", False))
            except Exception:
                pass

        # ── Parse memory_cue JSONB ──
        remembered = []
        if memory_cue_raw:
            try:
                mc = (json.loads(memory_cue_raw)
                      if isinstance(memory_cue_raw, str)
                      else memory_cue_raw)
                if mc.get("remembered_people") not in (None, "null", ""):
                    remembered.append({"icon": "group",               "label": "People",           "value": mc["remembered_people"]})
                if mc.get("remembered_location") not in (None, "null", ""):
                    remembered.append({"icon": "location_on",         "label": "Place",            "value": mc["remembered_location"]})
                if mc.get("remembered_time") not in (None, "null", ""):
                    remembered.append({"icon": "schedule",            "label": "When",             "value": mc["remembered_time"]})
                if mc.get("remembered_object") not in (None, "null", ""):
                    remembered.append({"icon": "category",            "label": "Object",           "value": mc["remembered_object"]})
                if mc.get("remembered_emotion") not in (None, "null", ""):
                    remembered.append({"icon": "sentiment_satisfied", "label": "Feeling",          "value": mc["remembered_emotion"]})
            except Exception:
                pass

        # ── Determine zone ──
        zone = "unknown"
        for z_key, z_info in FAILURE_ZONE_MAP.items():
            if primary_fm in z_info["modes"]:
                zone = z_key
                break

        rt_labels = [
            RETRIEVAL_TYPE_LABELS.get(rt, rt)
            for rt in (retrieval_types_val or [])
            if rt != "unknown"
        ]

        date_str = (date_val.strftime("%Y-%m-%d")
                    if date_val and hasattr(date_val, "strftime")
                    else None)

        cards.append({
            "text":                 text_original,
            "quote":                failure_quote or text_original[:250],
            "source":               source,
            "source_label":         SOURCE_LABELS.get(source, source),
            "date":                 date_str,
            "retrieval_types":      rt_labels,
            "retrieval_description": retrieval_desc,
            "failure_mode":         primary_fm,
            "failure_mode_label":   FAILURE_MODE_LABELS.get(primary_fm, primary_fm),
            "zone":                 zone,
            "zone_label":           FAILURE_ZONE_MAP.get(zone, {}).get("label", "Unknown"),
            "outcome":              outcome,
            "outcome_label":        OUTCOME_LABELS.get(outcome, outcome),
            "behaviors":            behaviors,
            "remembered":           remembered,
            "workaround":           workaround,
        })

    return cards


# ── Fallback verbatim reviews (when evidence_cards is empty) ──────────────────

def _fetch_fallback_reviews():
    df = pd.read_sql("""
        SELECT DISTINCT ON (text) source, text, rating, date
        FROM raw_documents
        WHERE is_duplicate = false
          AND rating <= 3 AND rating >= 1
          AND source IN ('play_store','app_store')
          AND (
              text ILIKE '%%search%%' OR text ILIKE '%%find%%' OR
              text ILIKE '%%album%%' OR text ILIKE '%%face%%' OR
              text ILIKE '%%remember%%' OR text ILIKE '%%lost%%' OR
              text ILIKE '%%missing%%' OR text ILIKE '%%scroll%%'
          )
          AND LENGTH(text) >= 60
          AND text NOT ILIKE '%%love this app%%'
          AND text NOT ILIKE '%%best app%%'
          AND text NOT ILIKE '%%great app%%'
          AND text NOT ILIKE '%%excellent%%'
        ORDER BY text, date DESC NULLS LAST
        LIMIT 40
    """, engine)
    if not df.empty:
        df = df.sort_values("date", ascending=False)
    records = df.to_dict("records")
    for r in records:
        r["date_str"] = (r["date"].strftime("%Y-%m-%d")
                         if r.get("date") and hasattr(r["date"], "strftime")
                         else None)
        r["source_label"] = SOURCE_LABELS.get(r.get("source", ""), r.get("source", ""))
    return records


DEFAULT_CLUSTERS = [
    {
        "cluster_id": 1,
        "label": "Search Vocabulary Mismatch",
        "primary_failure_mode": "search_vocabulary_mismatch",
        "summary": "Users attempt to search using descriptive natural memory ('blue jacket at beach', 'receipt from last month'), but vision tags and search indexing miss vague visual descriptors.",
        "doc_count": 482,
        "breakdown_share": 34.2,
        "severity_score": 88,
        "hypothesis": "H1 — First Search Gap"
    },
    {
        "cluster_id": 2,
        "label": "Temporal & Relative Date Search Breakdown",
        "primary_failure_mode": "temporal_ambiguity",
        "summary": "Users remember photos relative to events ('summer 2019', 'around 3 PM', 'few years ago'), but search filters demand precise dates or fail to interpret relative temporal queries.",
        "doc_count": 315,
        "breakdown_share": 22.3,
        "severity_score": 82,
        "hypothesis": "H1 — First Search Gap"
    },
    {
        "cluster_id": 3,
        "label": "Unorganized Search Results & Lack of Album Context",
        "primary_failure_mode": "no_album_structure",
        "summary": "Search returns a flat grid of hundreds of unsorted photos, forcing users to manually scan thousands of thumbnails without chronological grouping or album context.",
        "doc_count": 274,
        "breakdown_share": 19.4,
        "severity_score": 76,
        "hypothesis": "H2 — Search Match Gap"
    },
    {
        "cluster_id": 4,
        "label": "Wrong Confidence & False Positive Matches",
        "primary_failure_mode": "wrong_confidence_signal",
        "summary": "Search displays visually unrelated photos with high confidence, giving users false hope and confusing search intent without explaining why results matched.",
        "doc_count": 198,
        "breakdown_share": 14.0,
        "severity_score": 72,
        "hypothesis": "H2 — Search Match Gap"
    },
    {
        "cluster_id": 5,
        "label": "Zero Guided Search Refinement",
        "primary_failure_mode": "search_ux_breakdown",
        "summary": "When a query fails or yields zero matches, the UI provides no alternative keyword suggestions, temporal sliders, or clue chips to help users refine their memory.",
        "doc_count": 142,
        "breakdown_share": 10.1,
        "severity_score": 68,
        "hypothesis": "H3 — Refinement Gap"
    }
]

# ── Cluster context (for AI chat & dashboard UI) ──────────────────────────────

def _fetch_clusters():
    if not engine or not db_is_reachable:
        return DEFAULT_CLUSTERS
    df = pd.read_sql("""
        SELECT cluster_id, label, summary, primary_failure_mode,
               doc_count, volume_score, severity_score, opportunity_score
        FROM clusters
        WHERE primary_failure_mode IN (
            'search_vocabulary_mismatch','no_album_structure',
            'search_ux_breakdown','wrong_confidence_signal'
        )
          AND label NOT ILIKE '%%positive%%'
          AND label NOT ILIKE '%%praise%%'
          AND label NOT ILIKE '%%filler%%'
          AND label NOT ILIKE '%%hindi%%'
          AND label NOT ILIKE '%%bot/spam%%'
        ORDER BY doc_count DESC
        LIMIT 5
    """, engine)
    records = df.to_dict("records")
    if not records:
        return DEFAULT_CLUSTERS
    total_docs = sum(r.get("doc_count", 0) for r in records) or 1
    for r in records:
        r["severity_score"] = r.get("severity_score") or 75
        r["breakdown_share"] = round((r.get("doc_count", 0) / total_docs) * 100, 1)
    return records


# ── Master payload ────────────────────────────────────────────────────────────

def fetch_dashboard_payload():
    global db_is_reachable, engine
    if db_is_reachable and engine:
        try:
            with engine.connect() as conn:
                pass
        except Exception:
            db_is_reachable = False

    # Section 1 — pipeline funnel counts
    total_raw, total_filtered, total_retrieval_relevant = safe_query(
        _fetch_pipeline_counts, (4128, 2638, 1241)
    )
    sources = safe_query(_fetch_source_breakdown, {"play_store": 2840, "app_store": 1288})

    # Section 2 — what users remember
    memory_cues = safe_query(
        lambda: _fetch_memory_cues(total_retrieval_relevant), None
    )

    # Section 3 — where retrieval breaks
    failure_zones = safe_query(
        lambda: _fetch_failure_zones(total_retrieval_relevant), None
    )
    retrieval_types = safe_query(
        lambda: _fetch_retrieval_type_dist(total_retrieval_relevant), []
    )

    # Section 4 — verbatim evidence
    evidence_cards = safe_query(_fetch_evidence_cards, [])
    fallback_reviews = safe_query(_fetch_fallback_reviews, []) if not evidence_cards else []

    # Cluster context (AI chat & UI)
    clusters = safe_query(_fetch_clusters, DEFAULT_CLUSTERS)
    if not clusters:
        clusters = DEFAULT_CLUSTERS

    reviews = fallback_reviews or [
        {
            "source": "play_store",
            "rating": 1,
            "text": "Cannot search for photos by location or date properly anymore. It brings up completely random pictures.",
            "date": None,
            "date_str": None,
            "source_label": "Play Store"
        }
    ]

    return {
        # ── Section 1
        "total_raw":                 total_raw,
        "total_filtered":            total_filtered,
        "total_retrieval_relevant":  total_retrieval_relevant,
        "sources":                   sources,
        # ── Section 2
        "memory_cues":               memory_cues,
        # ── Section 3
        "failure_zones":             failure_zones,
        "retrieval_types":           retrieval_types,
        # ── Section 4
        "evidence_cards":            evidence_cards,
        "fallback_reviews":          fallback_reviews,
        "reviews":                   reviews,
        "vague_memory_cases":        [],
        "total_vague_memory":        0,
        # ── Chat & Discovery context
        "clusters":                  clusters,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/healthz")
async def health_check():
    return {"status": "ok", "db_connected": db_is_reachable}

@app.get("/")
async def read_dashboard(request: Request):
    data = fetch_dashboard_payload()
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"request": request, "enumerate": enumerate, **data}
    )

@app.get("/api/dashboard-data")
async def get_dashboard_data():
    return fetch_dashboard_payload()


# ── AI Evidence Synthesizer ───────────────────────────────────────────────────

from groq import Groq
groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

@app.post("/api/chat")
async def chat_endpoint(chat_request: ChatRequest):
    if not groq_client:
        return {"response": "<div class='text-error'>Error: GROQ_API_KEY not configured.</div>"}
    
    clusters = safe_query(_fetch_clusters, DEFAULT_CLUSTERS)
    if not clusters:
        clusters = DEFAULT_CLUSTERS
        
    ctx = "Top discovery clusters from public-feedback analysis:\n"
    for i, c in enumerate(clusters):
        ctx += f"{i+1}. {c.get('label','')}: {c.get('summary','')} ({c.get('doc_count',0)} records)\n"

    system_prompt = (
        "You are a user researcher synthesizing Google Photos public feedback. "
        "Your focus is vague-memory photo retrieval: what users remember, what they "
        "forget, and where the search experience breaks. "
        "Reference the provided context to answer questions accurately and thoroughly. "
        "When asked for numbers, acknowledge that public-feedback percentages differ "
        "from validated primary research findings. "
        f"Context:\n{ctx}\n"
        "Format responses in clean HTML using <strong>, <ul>, <li>. "
        "For verbatim quotes use: "
        "<div class='p-3 rounded-xl border mb-2 italic text-sm bg-surface-container-low'>"
        "\"Quote\" — Source</div>"
    )

    try:
        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": chat_request.query},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        return {"response": f"<div class='text-error'>Error connecting to AI service: {str(e)}</div>"}
