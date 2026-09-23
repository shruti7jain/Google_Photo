import os
import yaml
from datetime import datetime
from typing import Iterator
import pytz

from apify_client import ApifyClient
from loguru import logger

from ingestion.base import SourceConnector
from models.schema import RawDocument, Source, DocumentMetadata

class RedditConnector(SourceConnector):
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        self.config = config["ingestion"]["reddit"]
        self.min_date = datetime.fromisoformat(config["project"]["min_date"])
        if self.min_date.tzinfo is None:
            self.min_date = self.min_date.replace(tzinfo=pytz.UTC)
        
        token = os.getenv("APIFY_API_TOKEN")
        if not token:
            raise ValueError("APIFY_API_TOKEN not found in environment.")
        self.client = ApifyClient(token=token)

    def fetch(self) -> Iterator[RawDocument]:
        actor = self.config["apify_actor"]
        queries = self.config["search_queries"]
        max_items = self.config["max_items"]

        logger.info(f"Fetching Reddit data using Apify actor: {actor}")

        # Execute Apify Actor
        run_input = {
            "searches": queries,
            "maxItems": max_items,
            "type": "posts",
            "sort": "new",
        }
        
        try:
            run = self.client.actor(actor).call(run_input=run_input)
            dataset = self.client.dataset(run.default_dataset_id)
        except Exception as e:
            logger.error(f"Failed to fetch from Reddit via Apify: {e}")
            return

        yielded_count = 0
        for item in dataset.iterate_items():
            date_str = item.get("createdAt")
            if not date_str:
                continue
            
            try:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                date = None
            
            if date and date < self.min_date:
                continue
            
            content = item.get("body") or item.get("title")
            if not content or not content.strip():
                continue

            metadata = DocumentMetadata(
                upvotes=item.get("upvotes") or item.get("score"),
                reply_count=item.get("numComments"),
                is_thread_starter=item.get("dataType") == "post",
                subreddit=item.get("subreddit")
            )
            
            doc = RawDocument(
                source=Source.REDDIT,
                text=content.strip(),
                rating=None,  # Reddit doesn't have 1-5 star ratings
                date=date,
                url=item.get("url"),
                metadata=metadata
            )
            yield doc
            yielded_count += 1
            
        logger.success(f"RedditConnector yielded {yielded_count} documents.")
