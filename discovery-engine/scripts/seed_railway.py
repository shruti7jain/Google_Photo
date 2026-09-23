import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from loguru import logger

def main():
    load_dotenv()
    local_db = os.getenv("DATABASE_URL")
    target_db = sys.argv[1] if len(sys.argv) > 1 else None

    if not target_db:
        logger.error("Usage: python scripts/seed_railway.py <RAILWAY_DATABASE_URL>")
        logger.info("Example: python scripts/seed_railway.py postgresql://postgres:password@roundhouse.proxy.rlwy.net:12345/railway")
        return

    logger.info("Connecting to local database to read clusters and reviews...")
    local_engine = create_engine(local_db)

    # 1. Read local tables
    df_clusters = pd.read_sql("SELECT * FROM clusters", local_engine)
    df_evidence = pd.read_sql("SELECT * FROM cluster_evidence", local_engine)
    df_reviews = pd.read_sql("SELECT * FROM raw_documents WHERE rating <= 3 LIMIT 200", local_engine)

    logger.info(f"Read {len(df_clusters)} clusters, {len(df_evidence)} evidence quotes, {len(df_reviews)} sample reviews.")

    # 2. Connect to Railway target database
    logger.info(f"Connecting to Railway PostgreSQL database...")
    target_engine = create_engine(target_db)

    # 3. Create tables if not exist
    create_tables_sql = """
    CREATE TABLE IF NOT EXISTS clusters (
        cluster_id INTEGER PRIMARY KEY,
        run_id TEXT,
        label TEXT,
        summary TEXT,
        primary_failure_mode TEXT,
        primary_retrieval_type TEXT,
        doc_count INTEGER,
        source_breakdown JSONB,
        volume_score FLOAT,
        severity_score FLOAT,
        novelty_score FLOAT,
        opportunity_score FLOAT,
        centroid_x FLOAT,
        centroid_y FLOAT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS cluster_evidence (
        id SERIAL PRIMARY KEY,
        cluster_id INTEGER,
        doc_id TEXT,
        quote TEXT,
        source TEXT,
        rating FLOAT,
        date TIMESTAMPTZ,
        url TEXT,
        upvotes INTEGER
    );

    CREATE TABLE IF NOT EXISTS raw_documents (
        id TEXT PRIMARY KEY,
        source TEXT,
        text TEXT,
        rating FLOAT,
        date TIMESTAMPTZ,
        url TEXT,
        metadata JSONB,
        simhash TEXT,
        is_duplicate BOOLEAN DEFAULT FALSE,
        duplicate_of TEXT,
        ingested_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS processed_documents (
        raw_doc_id TEXT PRIMARY KEY,
        source TEXT,
        text_clean TEXT,
        text_original TEXT,
        language TEXT,
        language_confidence FLOAT,
        processing_status TEXT,
        is_relevant BOOLEAN,
        relevance_confidence FLOAT,
        chunks TEXT[],
        chunk_count INTEGER,
        rating FLOAT,
        date TIMESTAMPTZ,
        url TEXT,
        processed_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS tagged_documents (
        processed_doc_id TEXT PRIMARY KEY,
        source TEXT,
        text_original TEXT,
        rating FLOAT,
        date TIMESTAMPTZ,
        url TEXT,
        retrieval_types TEXT[],
        retrieval_description TEXT,
        retrieval_confidence NUMERIC,
        memory_cue JSONB,
        failure_modes TEXT[],
        primary_failure_mode TEXT,
        failure_evidence_quote TEXT,
        failure_confidence NUMERIC,
        is_data_loss BOOLEAN,
        search_behavior JSONB,
        needs_review BOOLEAN,
        low_confidence_dimensions TEXT[],
        vagueness_high BOOLEAN,
        tagged_at TIMESTAMPTZ DEFAULT NOW()
    );
    """

    with target_engine.begin() as conn:
        conn.execute(text(create_tables_sql))
    logger.success("✓ Created all database schemas in Railway PostgreSQL.")

    # 4. Insert data into target
    df_clusters.to_sql("clusters", target_engine, if_exists="replace", index=False)
    logger.success(f"✓ Seeded {len(df_clusters)} clusters into Railway.")

    df_evidence.to_sql("cluster_evidence", target_engine, if_exists="replace", index=False)
    logger.success(f"✓ Seeded {len(df_evidence)} cluster evidence quotes into Railway.")

    df_reviews.to_sql("raw_documents", target_engine, if_exists="append", index=False)
    logger.success(f"✓ Seeded {len(df_reviews)} sample verbatim reviews into Railway.")

    logger.success("★ Railway Database Seed Complete! Your cloud database is now fully populated.")

if __name__ == "__main__":
    main()
