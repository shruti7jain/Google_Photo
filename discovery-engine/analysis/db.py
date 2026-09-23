import os
import json
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from loguru import logger
from models.schema import TaggedDocument

class AnalysisDatabaseManager:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL not set in environment")
        self.engine = create_engine(self.db_url)
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        query = text("""
            CREATE TABLE IF NOT EXISTS tagged_documents (
                processed_doc_id TEXT PRIMARY KEY,
                source TEXT,
                text_original TEXT,
                rating FLOAT,
                date TIMESTAMP,
                url TEXT,
                retrieval_types JSONB,
                retrieval_description TEXT,
                retrieval_confidence FLOAT,
                memory_cue JSONB,
                failure_modes JSONB,
                primary_failure_mode TEXT,
                failure_evidence_quote TEXT,
                failure_confidence FLOAT,
                is_data_loss BOOLEAN,
                search_behavior JSONB,
                needs_review BOOLEAN,
                low_confidence_dimensions JSONB,
                vagueness_high BOOLEAN,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        with self.engine.begin() as conn:
            conn.execute(query)

    def fetch_unprocessed_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        query = text("""
            SELECT raw_doc_id, source, text_original, rating, date, url
            FROM processed_documents
            WHERE raw_doc_id NOT IN (SELECT processed_doc_id FROM tagged_documents)
            LIMIT :limit
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query, {"limit": limit})
            return [dict(row._mapping) for row in result]

    def save_tagged_documents(self, documents: List[TaggedDocument]) -> None:
        if not documents:
            return

        query = text("""
            INSERT INTO tagged_documents 
                (processed_doc_id, source, text_original, rating, date, url,
                 retrieval_types, retrieval_description, retrieval_confidence,
                 memory_cue, failure_modes, primary_failure_mode, failure_evidence_quote,
                 failure_confidence, is_data_loss, search_behavior, needs_review,
                 low_confidence_dimensions, vagueness_high)
            VALUES 
                (:processed_doc_id, :source, :text_original, :rating, :date, :url,
                 :retrieval_types, :retrieval_description, :retrieval_confidence,
                 :memory_cue, :failure_modes, :primary_failure_mode, :failure_evidence_quote,
                 :failure_confidence, :is_data_loss, :search_behavior, :needs_review,
                 :low_confidence_dimensions, :vagueness_high)
            ON CONFLICT (processed_doc_id) DO UPDATE SET
                retrieval_types = EXCLUDED.retrieval_types,
                retrieval_description = EXCLUDED.retrieval_description,
                retrieval_confidence = EXCLUDED.retrieval_confidence,
                memory_cue = EXCLUDED.memory_cue,
                failure_modes = EXCLUDED.failure_modes,
                primary_failure_mode = EXCLUDED.primary_failure_mode,
                failure_evidence_quote = EXCLUDED.failure_evidence_quote,
                failure_confidence = EXCLUDED.failure_confidence,
                is_data_loss = EXCLUDED.is_data_loss,
                search_behavior = EXCLUDED.search_behavior,
                needs_review = EXCLUDED.needs_review,
                low_confidence_dimensions = EXCLUDED.low_confidence_dimensions,
                vagueness_high = EXCLUDED.vagueness_high
        """)

        params = []
        for doc in documents:
            params.append({
                "processed_doc_id": doc.processed_doc_id,
                "source": doc.source,
                "text_original": doc.text_original,
                "rating": doc.rating,
                "date": doc.date,
                "url": doc.url,
                "retrieval_types": [str(t) for t in doc.retrieval_types] if doc.retrieval_types else [],
                "retrieval_description": doc.retrieval_description,
                "retrieval_confidence": doc.retrieval_confidence,
                "memory_cue": doc.memory_cue.model_dump_json() if doc.memory_cue else None,
                "failure_modes": [str(m) for m in doc.failure_modes] if doc.failure_modes else [],
                "primary_failure_mode": str(doc.primary_failure_mode) if doc.primary_failure_mode else None,
                "failure_evidence_quote": doc.failure_evidence_quote,
                "failure_confidence": doc.failure_confidence,
                "is_data_loss": doc.is_data_loss,
                "search_behavior": doc.search_behavior.model_dump_json() if doc.search_behavior else None,
                "needs_review": doc.needs_review,
                "low_confidence_dimensions": [str(d) for d in doc.low_confidence_dimensions] if doc.low_confidence_dimensions else [],
                "vagueness_high": doc.vagueness_high
            })

        with self.engine.begin() as conn:
            conn.execute(query, params)
