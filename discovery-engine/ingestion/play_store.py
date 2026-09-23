import yaml
from datetime import datetime
from typing import Iterator

from google_play_scraper import reviews, Sort
from loguru import logger

from ingestion.base import SourceConnector
from models.schema import RawDocument, Source, DocumentMetadata

class PlayStoreConnector(SourceConnector):
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        self.config = config["ingestion"]["play_store"]
        self.min_date = datetime.fromisoformat(config["project"]["min_date"])

    def fetch(self) -> Iterator[RawDocument]:
        app_id = self.config["app_id"]
        target_count = self.config["target_count"]
        sort_val = Sort.NEWEST if self.config["sort"] == "NEWEST" else Sort.MOST_RELEVANT
        country = self.config["country"]
        lang = self.config["lang"]

        logger.info(f"Fetching up to {target_count} reviews from Play Store ({app_id})")

        # google-play-scraper's `reviews` method returns a list of reviews and a continuation token
        try:
            result, continuation_token = reviews(
                app_id,
                lang=lang,
                country=country,
                sort=sort_val,
                count=target_count
            )
        except Exception as e:
            logger.error(f"Failed to fetch from Play Store: {e}")
            return

        yielded_count = 0
        for item in result:
            date = item.get("at")
            if date and date < self.min_date:
                continue
            
            # Content shouldn't be empty, skip if it is
            content = item.get("content")
            if not content or not content.strip():
                continue

            doc = RawDocument(
                source=Source.PLAY_STORE,
                text=content.strip(),
                rating=float(item.get("score")),
                date=date,
                url=None, # no direct URL for individual play store reviews easily available
                metadata=DocumentMetadata(
                    upvotes=item.get("thumbsUpCount"),
                    app_version=item.get("reviewCreatedVersion")
                )
            )
            yield doc
            yielded_count += 1

        logger.success(f"PlayStoreConnector yielded {yielded_count} documents.")
