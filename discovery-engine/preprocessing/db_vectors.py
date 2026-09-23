import os
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from loguru import logger
import json

class VectorDBManager:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL not set in environment")
        self.engine = create_engine(self.db_url)

    def fetch_unprocessed_documents(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Fetch raw documents that haven't been processed yet."""
        query = text("""
            SELECT id, source, text, rating, date, url
            FROM raw_documents
            WHERE is_duplicate = FALSE
              AND id NOT IN (SELECT raw_doc_id FROM processed_documents)
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"limit": limit})
            return [dict(row._mapping) for row in result]

    def save_processed_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Save batch of processed documents including their embeddings."""
        if not documents:
            return
            
        query = text("""
            INSERT INTO processed_documents 
                (raw_doc_id, source, text_clean, text_original, chunks, chunk_count, 
                 embedding, embedding_model, rating, date, url, processing_status)
            VALUES 
                (:raw_doc_id, :source, :text_clean, :text_original, :chunks, :chunk_count,
                 :embedding, :embedding_model, :rating, :date, :url, 'completed')
            ON CONFLICT (raw_doc_id) DO UPDATE SET
                text_clean = EXCLUDED.text_clean,
                chunks = EXCLUDED.chunks,
                chunk_count = EXCLUDED.chunk_count,
                embedding = EXCLUDED.embedding,
                processing_status = 'completed',
                processed_at = NOW()
        """)
        
        # Serialize lists to JSON string for the JSONB column
        for doc in documents:
            if isinstance(doc.get('chunks'), list):
                doc['chunks'] = json.dumps(doc['chunks'])
            else:
                doc['chunks'] = '[]'
                
        with self.engine.begin() as conn:
            conn.execute(query, documents)
