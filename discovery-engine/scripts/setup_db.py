"""
scripts/setup_db.py
────────────────────────────────────────────────────────────────
Creates all PostgreSQL tables required by the pipeline.
Run once before the first ingestion:

    python scripts/setup_db.py

Requires DATABASE_URL in .env and the pgvector extension installed
in your PostgreSQL instance:

    CREATE EXTENSION IF NOT EXISTS vector;
"""

import os
import sys

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL not set in .env — aborting.")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────
# DDL Statements
# ──────────────────────────────────────────────────────────────

DDL = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ── raw_documents ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_documents (
    id               TEXT PRIMARY KEY,
    source           TEXT NOT NULL,
    text             TEXT NOT NULL,
    rating           NUMERIC(2,1),
    date             TIMESTAMPTZ,
    url              TEXT,
    metadata         JSONB DEFAULT '{}',
    simhash          TEXT,
    is_duplicate     BOOLEAN DEFAULT FALSE,
    duplicate_of     TEXT,
    ingested_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_source ON raw_documents(source);
CREATE INDEX IF NOT EXISTS idx_raw_date   ON raw_documents(date);
CREATE INDEX IF NOT EXISTS idx_raw_simhash ON raw_documents(simhash);

-- ── processed_documents ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS processed_documents (
    raw_doc_id              TEXT PRIMARY KEY REFERENCES raw_documents(id),
    source                  TEXT NOT NULL,
    text_clean              TEXT NOT NULL,
    text_original           TEXT NOT NULL,
    language                TEXT,
    language_confidence     NUMERIC(4,3),
    processing_status       TEXT DEFAULT 'pending',
    is_relevant             BOOLEAN,
    relevance_confidence    NUMERIC(4,3),
    chunks                  JSONB DEFAULT '[]',
    chunk_count             INTEGER DEFAULT 0,
    embedding               vector(384),          -- all-MiniLM-L6-v2 dimension
    embedding_model         TEXT,
    rating                  NUMERIC(2,1),
    date                    TIMESTAMPTZ,
    url                     TEXT,
    processed_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proc_status    ON processed_documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_proc_relevant  ON processed_documents(is_relevant);
CREATE INDEX IF NOT EXISTS idx_proc_embedding ON processed_documents USING hnsw (embedding vector_cosine_ops);

-- ── tagged_documents ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tagged_documents (
    processed_doc_id        TEXT PRIMARY KEY REFERENCES processed_documents(raw_doc_id),
    source                  TEXT NOT NULL,
    text_original           TEXT NOT NULL,
    rating                  NUMERIC(2,1),
    date                    TIMESTAMPTZ,
    url                     TEXT,

    -- Analyzer A: Retrieval Pattern
    retrieval_types         TEXT[],
    retrieval_description   TEXT,
    retrieval_confidence    NUMERIC(4,3),

    -- Analyzer B: Memory Cue
    memory_cue              JSONB,

    -- Analyzer C: Failure Mode
    failure_modes           TEXT[],
    primary_failure_mode    TEXT,
    failure_evidence_quote  TEXT,
    failure_confidence      NUMERIC(4,3),
    is_data_loss            BOOLEAN DEFAULT FALSE,

    -- Analyzer D: Search Behavior
    search_behavior         JSONB,

    -- QA
    needs_review            BOOLEAN DEFAULT FALSE,
    low_confidence_dimensions TEXT[],
    vagueness_high          BOOLEAN DEFAULT FALSE,

    tagged_at               TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tagged_failure ON tagged_documents(primary_failure_mode);
CREATE INDEX IF NOT EXISTS idx_tagged_review  ON tagged_documents(needs_review);

-- ── clusters ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clusters (
    cluster_id          INTEGER NOT NULL,
    run_id              TEXT NOT NULL,
    label               TEXT,
    summary             TEXT,
    primary_failure_mode TEXT,
    primary_retrieval_type TEXT,
    doc_count           INTEGER,
    source_breakdown    JSONB DEFAULT '{}',
    volume_score        NUMERIC(5,2),
    severity_score      NUMERIC(5,2),
    novelty_score       NUMERIC(5,2),
    opportunity_score   NUMERIC(5,2),
    centroid_x          NUMERIC(10,6),
    centroid_y          NUMERIC(10,6),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (cluster_id, run_id)
);

CREATE INDEX IF NOT EXISTS idx_cluster_score  ON clusters(opportunity_score DESC);
CREATE INDEX IF NOT EXISTS idx_cluster_run    ON clusters(run_id);

-- ── cluster_evidence ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cluster_evidence (
    id              SERIAL PRIMARY KEY,
    cluster_id      INTEGER NOT NULL,
    run_id          TEXT NOT NULL,
    doc_id          TEXT NOT NULL,
    quote           TEXT NOT NULL,
    source          TEXT,
    rating          NUMERIC(2,1),
    date            TIMESTAMPTZ,
    url             TEXT,
    upvotes         INTEGER,
    FOREIGN KEY (cluster_id, run_id) REFERENCES clusters(cluster_id, run_id)
);

CREATE INDEX IF NOT EXISTS idx_evidence_cluster ON cluster_evidence(cluster_id, run_id);

-- ── failed_documents (quarantine table) ──────────────────────
CREATE TABLE IF NOT EXISTS failed_documents (
    id              SERIAL PRIMARY KEY,
    stage           TEXT NOT NULL,     -- 'ingestion' | 'preprocessing' | 'analysis'
    raw_text        TEXT,
    error_message   TEXT,
    source          TEXT,
    failed_at       TIMESTAMPTZ DEFAULT NOW()
);
"""


def main() -> None:
    engine = create_engine(DATABASE_URL)
    logger.info(f"Connecting to database: {DATABASE_URL.split('@')[-1]}")  # hide credentials

    with engine.connect() as conn:
        logger.info("Running DDL migrations...")
        conn.execute(text(DDL))
        conn.commit()
        logger.success("✅ All tables created successfully.")

    logger.info("Schema setup complete. You can now run ingestion.")


if __name__ == "__main__":
    main()
