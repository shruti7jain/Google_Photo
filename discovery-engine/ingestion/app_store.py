import yaml
from datetime import datetime
from typing import Iterator
import pytz

from app_store_scraper import AppStore
from loguru import logger

from ingestion.base import SourceConnector
from models.schema import RawDocument, Source, DocumentMetadata

class AppStoreConnector(SourceConnector):
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        self.config = config["ingestion"]["app_store"]
        self.min_date = datetime.fromisoformat(config["project"]["min_date"])
        if self.min_date.tzinfo is None:
            self.min_date = self.min_date.replace(tzinfo=pytz.UTC)

    def fetch(self) -> Iterator[RawDocument]:
        app_id = self.config["app_id"]
        storefronts = self.config["storefronts"]
        target_count = self.config["target_count_per_storefront"]

        import requests
        
        yielded_count = 0
        pages = 10  # Apple limits RSS feed to 10 pages of 50 reviews

        for country in storefronts:
            logger.info(f"Fetching reviews from App Store (country: {country}) via RSS")
            
            for page in range(1, pages + 1):
                url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/page={page}/json"
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.status_code != 200:
                        break
                    
                    data = resp.json()
                    entries = data.get("feed", {}).get("entry", [])
                    
                    if not entries:
                        break
                        
                    # Skip the first entry if it's the app metadata rather than a review
                    if isinstance(entries, list) and len(entries) > 0 and 'author' not in entries[0]:
                        entries = entries[1:]
                        
                    for entry in entries:
                        if yielded_count >= target_count:
                            break
                            
                        # Safely extract fields from the RSS JSON format
                        try:
                            content = entry.get("content", {}).get("label", "")
                            rating_str = entry.get("im:rating", {}).get("label", "0")
                            rating = float(rating_str)
                            
                            # RSS doesn't give precise timestamps in all endpoints, but sometimes gives updated
                            date_str = entry.get("updated", {}).get("label")
                            if date_str:
                                date = datetime.fromisoformat(date_str)
                                if date.tzinfo is None:
                                    date = date.replace(tzinfo=pytz.UTC)
                                if date < self.min_date:
                                    continue
                            else:
                                date = datetime.now(pytz.UTC)
                                
                            if not content or not content.strip():
                                continue
                                
                            doc = RawDocument(
                                source=Source.APP_STORE,
                                text=content.strip(),
                                rating=rating,
                                date=date,
                                url=None,
                                metadata=DocumentMetadata(storefront=country)
                            )
                            yield doc
                            yielded_count += 1
                        except Exception as e:
                            logger.debug(f"Skipping malformed RSS entry: {e}")
                            
                except Exception as e:
                    logger.error(f"Failed to fetch App Store RSS page {page} ({country}): {e}")
                    break

        logger.success(f"AppStoreConnector yielded {yielded_count} documents.")
