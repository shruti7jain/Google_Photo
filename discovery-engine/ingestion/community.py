import os
import yaml
from datetime import datetime
from typing import Iterator
import pytz
import re

from apify_client import ApifyClient
from loguru import logger

from ingestion.base import SourceConnector
from models.schema import RawDocument, Source, DocumentMetadata

class CommunityConnector(SourceConnector):
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        self.config = config["ingestion"]["community"]
        self.min_date = datetime.fromisoformat(config["project"]["min_date"])
        if self.min_date.tzinfo is None:
            self.min_date = self.min_date.replace(tzinfo=pytz.UTC)
        
        token = os.getenv("APIFY_API_TOKEN")
        if not token:
            raise ValueError("APIFY_API_TOKEN not found in environment.")
        self.client = ApifyClient(token=token)

    def fetch(self) -> Iterator[RawDocument]:
        actor = self.config["apify_actor"]
        start_url = self.config["start_url"]
        max_pages = self.config["max_crawl_pages"]
        keywords = self.config["keywords"]

        logger.info(f"Fetching Community data using Apify actor: {actor}")

        # Execute Apify Actor
        run_input = {
            "startUrls": [{"url": start_url}],
            "maxCrawlPages": max_pages,
            # Regex for keywords
            "pageFilter": "|".join(keywords) if keywords else None
        }
        
        try:
            run = self.client.actor(actor).call(run_input=run_input)
            dataset = self.client.dataset(run.default_dataset_id)
        except Exception as e:
            logger.error(f"Failed to fetch from Community via Apify: {e}")
            return

        yielded_count = 0
        for item in dataset.iterate_items():
            content = item.get("text") or item.get("markdown")
            if not content or not content.strip():
                continue
                
            # Filter if keywords provided, since pageFilter might not strictly apply depending on crawler config
            if keywords and not any(k.lower() in content.lower() for k in keywords):
                continue
            
            doc = RawDocument(
                source=Source.COMMUNITY,
                text=content.strip(),
                rating=None,
                date=None,  # Community threads scrape often miss explicit structure for dates
                url=item.get("url"),
                metadata=DocumentMetadata()
            )
            yield doc
            yielded_count += 1
            
        logger.success(f"CommunityConnector yielded {yielded_count} documents.")
