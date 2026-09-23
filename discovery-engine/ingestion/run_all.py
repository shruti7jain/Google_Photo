import os
from loguru import logger
from dotenv import load_dotenv
import itertools

from ingestion.play_store import PlayStoreConnector
from ingestion.app_store import AppStoreConnector
from ingestion.reddit import RedditConnector
from ingestion.community import CommunityConnector
from ingestion.deduplicator import Deduplicator
from ingestion.db import DatabaseManager

def main():
    load_dotenv()
    logger.info("Starting Data Ingestion (Phase 1)")

    # Initialize Connectors
    connectors = [
        PlayStoreConnector(),
        AppStoreConnector(),
    ]
    
    # Only initialize Apify connectors if we have the token
    if os.getenv("APIFY_API_TOKEN"):
        connectors.extend([
            RedditConnector(),
            CommunityConnector()
        ])
    else:
        logger.warning("APIFY_API_TOKEN not found, skipping Reddit and Community scraping.")

    deduplicator = Deduplicator()
    db_manager = DatabaseManager()

    total_fetched = 0
    total_saved = 0
    duplicates = 0

    batch_size = 500
    batch = []

    for connector in connectors:
        source_name = connector.__class__.__name__
        logger.info(f"--- Running {source_name} ---")
        
        try:
            for raw_doc in connector.fetch():
                total_fetched += 1
                processed_doc = deduplicator.process_document(raw_doc)
                
                if processed_doc.is_duplicate:
                    duplicates += 1
                
                batch.append(processed_doc)
                
                if len(batch) >= batch_size:
                    db_manager.save_raw_documents(batch)
                    total_saved += len(batch)
                    batch = []
                    
        except Exception as e:
            logger.error(f"Error while fetching from {source_name}: {e}")

    # Save remaining
    if batch:
        db_manager.save_raw_documents(batch)
        total_saved += len(batch)

    logger.info("--- Ingestion Complete ---")
    logger.info(f"Total fetched: {total_fetched}")
    logger.info(f"Duplicates found: {duplicates} ({(duplicates/total_fetched*100) if total_fetched > 0 else 0:.1f}%)")
    logger.info(f"Total saved to DB: {total_saved}")

if __name__ == "__main__":
    main()
