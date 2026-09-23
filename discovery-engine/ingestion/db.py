import os
import json
from typing import List
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from loguru import logger

from models.schema import RawDocument

class DatabaseManager:
    def __init__(self):
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL not found in environment")
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def save_raw_documents(self, docs: List[RawDocument]) -> None:
        if not docs:
            return

        query = text("""
            INSERT INTO raw_documents 
            (id, source, text, rating, date, url, metadata, simhash, is_duplicate, duplicate_of)
            VALUES 
            (:id, :source, :text, :rating, :date, :url, :metadata, :simhash, :is_duplicate, :duplicate_of)
            ON CONFLICT (id) DO UPDATE SET
                is_duplicate = EXCLUDED.is_duplicate,
                duplicate_of = EXCLUDED.duplicate_of
        """)

        with self.Session() as session:
            try:
                for doc in docs:
                    session.execute(query, {
                        "id": doc.id,
                        "source": doc.source,
                        "text": doc.text,
                        "rating": doc.rating,
                        "date": doc.date,
                        "url": doc.url,
                        "metadata": doc.metadata.model_dump_json(),
                        "simhash": doc.simhash,
                        "is_duplicate": doc.is_duplicate,
                        "duplicate_of": doc.duplicate_of
                    })
                session.commit()
                logger.info(f"Saved {len(docs)} documents to DB.")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save documents: {e}")
                raise
