import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.resolve()

def run_command(name: str, cmd: list[str]) -> bool:
    logger.info(f"========== Starting: {name} ==========")
    start = time.time()
    try:
        subprocess.run(
            cmd,
            check=True,
            text=True,
            cwd=str(PROJECT_ROOT)
        )
        elapsed = time.time() - start
        logger.success(f"========== Finished: {name} in {elapsed:.1f}s ==========\n")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"========== FAILED: {name} (Exit code {e.returncode}) ==========\n")
        return False

def check_status():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment!")
        return

    from sqlalchemy import create_engine
    import pandas as pd

    engine = create_engine(db_url)
    logger.info("=== Discovery Engine Pipeline Health & Table Counts ===")
    tables = [
        ("Phase 1: Ingestion", "raw_documents"),
        ("Phase 2: Preprocessing", "processed_documents"),
        ("Phase 3: AI Tagging", "tagged_documents"),
        ("Phase 4: Clusters", "clusters"),
        ("Phase 4: Evidence Quotes", "cluster_evidence"),
    ]

    for phase_name, tbl in tables:
        try:
            cnt = pd.read_sql(f"SELECT count(*) as c FROM {tbl}", engine).iloc[0]['c']
            logger.info(f"  ✓ {phase_name:<25} [{tbl}]: {cnt:,} records")
        except Exception as e:
            logger.warning(f"  ✗ {phase_name:<25} [{tbl}]: Table missing or inaccessible ({e})")

    reports_dir = PROJECT_ROOT / "output" / "reports"
    report_count = len(list(reports_dir.glob("*.md"))) if reports_dir.exists() else 0
    logger.info(f"  ✓ Phase 5: Insight Reports    [output/reports]: {report_count} generated reports")

def main():
    parser = argparse.ArgumentParser(description="Discovery Engine Master Pipeline Runner")
    parser.add_argument("--phase", choices=["1", "2", "3", "4", "5", "all"], default="all",
                        help="Run a specific pipeline phase (1=Ingestion, 2=Preprocessing, 3=AI Tagging, 4=Clustering, 5=Reports, all=All)")
    parser.add_argument("--status", action="store_true", help="Display database record counts and health status")
    parser.add_argument("--limit", type=int, default=100, help="Document limit for Phase 3 tagging")
    args = parser.parse_args()

    if args.status:
        check_status()
        return

    logger.info(f"Running Discovery Engine Pipeline (Target Phase: {args.phase})")
    start_time = time.time()

    py = sys.executable

    phase_map = {
        "1": ("Phase 1: Data Ingestion", [py, "-m", "ingestion.run_all"]),
        "2": ("Phase 2: Preprocessing & Embedding", [py, "-m", "preprocessing.run"]),
        "3": ("Phase 3: AI Analysis Layer", [py, "-m", "analysis.run_pipeline", "--limit", str(args.limit)]),
        "4": ("Phase 4: Synthesis & Clustering", [py, "-m", "synthesis.run_pipeline"]),
        "5": ("Phase 5: Insight Reports Generation", [py, "output/generate_reports.py"]),
    }

    if args.phase == "all":
        phases_to_run = ["1", "2", "3", "4", "5"]
    else:
        phases_to_run = [args.phase]

    for p in phases_to_run:
        name, cmd = phase_map[p]
        success = run_command(name, cmd)
        if not success:
            logger.error(f"Pipeline stopped early due to failure in {name}")
            sys.exit(1)

    duration = time.time() - start_time
    logger.success(f"Pipeline finished successfully in {duration:.1f} seconds!")

if __name__ == "__main__":
    main()
