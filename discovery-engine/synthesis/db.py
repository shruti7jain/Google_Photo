import os
import json
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from loguru import logger
from models.schema import OpportunityCluster, ClusterEvidence

class SynthesisDatabaseManager:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL not set")
        self.engine = create_engine(self.db_url)
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        query = text("""
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
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS cluster_evidence (
                id SERIAL PRIMARY KEY,
                cluster_id INTEGER,
                doc_id TEXT,
                quote TEXT,
                source TEXT,
                rating FLOAT,
                date TIMESTAMP,
                url TEXT,
                upvotes INTEGER,
                FOREIGN KEY(cluster_id) REFERENCES clusters(cluster_id)
            );
        """)
        with self.engine.begin() as conn:
            conn.execute(query)

    def fetch_embedded_documents(self) -> List[Dict[str, Any]]:
        query = text("""
            SELECT raw_doc_id, source, text_original, rating, date, url, embedding
            FROM processed_documents
            WHERE embedding IS NOT NULL
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query)
            docs = []
            for row in result:
                d = dict(row._mapping)
                if isinstance(d['embedding'], str):
                    d['embedding'] = json.loads(d['embedding'])
                docs.append(d)
            return docs

    def save_clusters(self, clusters: List[OpportunityCluster]) -> None:
        if not clusters:
            return
            
        cluster_query = text("""
            INSERT INTO clusters 
                (cluster_id, run_id, label, summary, primary_failure_mode, primary_retrieval_type,
                 doc_count, source_breakdown, volume_score, severity_score, novelty_score,
                 opportunity_score, centroid_x, centroid_y)
            VALUES 
                (:cluster_id, :run_id, :label, :summary, :primary_failure_mode, :primary_retrieval_type,
                 :doc_count, :source_breakdown, :volume_score, :severity_score, :novelty_score,
                 :opportunity_score, :centroid_x, :centroid_y)
            ON CONFLICT (cluster_id) DO UPDATE SET
                label = EXCLUDED.label,
                summary = EXCLUDED.summary,
                primary_failure_mode = EXCLUDED.primary_failure_mode,
                primary_retrieval_type = EXCLUDED.primary_retrieval_type,
                doc_count = EXCLUDED.doc_count,
                source_breakdown = EXCLUDED.source_breakdown,
                opportunity_score = EXCLUDED.opportunity_score,
                centroid_x = EXCLUDED.centroid_x,
                centroid_y = EXCLUDED.centroid_y
        """)

        evidence_query = text("""
            INSERT INTO cluster_evidence 
                (cluster_id, doc_id, quote, source, rating, date, url, upvotes)
            VALUES 
                (:cluster_id, :doc_id, :quote, :source, :rating, :date, :url, :upvotes)
        """)

        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM cluster_evidence"))
            
            for cluster in clusters:
                conn.execute(cluster_query, {
                    "cluster_id": cluster.cluster_id,
                    "run_id": cluster.run_id,
                    "label": cluster.label,
                    "summary": cluster.summary,
                    "primary_failure_mode": cluster.primary_failure_mode.value if hasattr(cluster.primary_failure_mode, 'value') else cluster.primary_failure_mode,
                    "primary_retrieval_type": cluster.primary_retrieval_type.value if hasattr(cluster.primary_retrieval_type, 'value') else cluster.primary_retrieval_type,
                    "doc_count": cluster.doc_count,
                    "source_breakdown": json.dumps(cluster.source_breakdown),
                    "volume_score": cluster.volume_score,
                    "severity_score": cluster.severity_score,
                    "novelty_score": cluster.novelty_score,
                    "opportunity_score": cluster.opportunity_score,
                    "centroid_x": cluster.centroid_x,
                    "centroid_y": cluster.centroid_y
                })
                
                for ev in cluster.top_evidence:
                    conn.execute(evidence_query, {
                        "cluster_id": cluster.cluster_id,
                        "doc_id": ev.doc_id,
                        "quote": ev.quote,
                        "source": ev.source,
                        "rating": ev.rating,
                        "date": ev.date,
                        "url": ev.url,
                        "upvotes": ev.upvotes
                    })
