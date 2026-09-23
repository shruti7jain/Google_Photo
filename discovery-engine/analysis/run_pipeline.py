import os
import time
import argparse
from typing import List, Optional
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv

from analysis.db import AnalysisDatabaseManager
from analysis.prompt_runner import PromptRunner
from models.schema import (
    TaggedDocument, MemoryCueProfile, SearchBehaviorProfile,
    RetrievalType, FailureMode
)

class UnifiedAnalysisOutput(BaseModel):
    retrieval_types: List[RetrievalType] = Field(default_factory=list)
    retrieval_description: Optional[str] = None
    retrieval_confidence: float = Field(default=0.0)

    memory_cue: Optional[MemoryCueProfile] = None

    failure_modes: List[FailureMode] = Field(default_factory=list)
    primary_failure_mode: Optional[FailureMode] = None
    failure_evidence_quote: Optional[str] = None
    failure_confidence: float = Field(default=0.0)
    is_data_loss: bool = False

    search_behavior: Optional[SearchBehaviorProfile] = None

def main():
    parser = argparse.ArgumentParser(description="AI Analysis Layer (Phase 3)")
    parser.add_argument("--limit", type=int, default=100, help="Number of documents to process in this run")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch commit size")
    args = parser.parse_args()

    load_dotenv()
    logger.info(f"Starting Unified AI Analysis Layer (Phase 3) - Target Limit: {args.limit}")

    db = AnalysisDatabaseManager()
    runner = PromptRunner()

    processed_count = 0
    while processed_count < args.limit:
        fetch_size = min(args.batch_size, args.limit - processed_count)
        docs = db.fetch_unprocessed_documents(limit=fetch_size)
        if not docs:
            logger.info("No more unprocessed documents found. Analysis complete!")
            break

        logger.info(f"Processing batch of {len(docs)} documents ({processed_count}/{args.limit} done)...")
        tagged_batch = []

        for doc in docs:
            text_original = doc['text_original']
            try:
                prompt = runner.load_prompt("prompts/unified_analyzer.txt", text=text_original)
                res: UnifiedAnalysisOutput = runner.run_prompt(prompt, UnifiedAnalysisOutput)

                # QA flags
                conf_scores = [
                    res.retrieval_confidence,
                    res.failure_confidence,
                ]
                if res.memory_cue:
                    conf_scores.append(res.memory_cue.confidence)
                if res.search_behavior:
                    conf_scores.append(res.search_behavior.confidence)

                needs_review = any(c < 0.6 for c in conf_scores)
                low_conf_dims = []
                if res.retrieval_confidence < 0.6:
                    low_conf_dims.append("retrieval_pattern")
                if res.memory_cue and res.memory_cue.confidence < 0.6:
                    low_conf_dims.append("memory_cue")
                if res.failure_confidence < 0.6:
                    low_conf_dims.append("failure_mode")
                if res.search_behavior and res.search_behavior.confidence < 0.6:
                    low_conf_dims.append("search_behavior")

                vagueness_high = True
                if res.memory_cue:
                    vagueness_high = not any([
                        res.memory_cue.remembered_time,
                        res.memory_cue.remembered_location,
                        res.memory_cue.remembered_people,
                        res.memory_cue.remembered_object,
                        res.memory_cue.remembered_emotion
                    ])

                tagged_doc = TaggedDocument(
                    processed_doc_id=doc['raw_doc_id'],
                    source=doc['source'],
                    text_original=text_original,
                    rating=doc.get('rating'),
                    date=doc.get('date'),
                    url=doc.get('url'),
                    retrieval_types=res.retrieval_types,
                    retrieval_description=res.retrieval_description,
                    retrieval_confidence=res.retrieval_confidence,
                    memory_cue=res.memory_cue,
                    failure_modes=res.failure_modes,
                    primary_failure_mode=res.primary_failure_mode,
                    failure_evidence_quote=res.failure_evidence_quote,
                    failure_confidence=res.failure_confidence,
                    is_data_loss=res.is_data_loss,
                    search_behavior=res.search_behavior,
                    needs_review=needs_review,
                    low_confidence_dimensions=low_conf_dims,
                    vagueness_high=vagueness_high
                )
                tagged_batch.append(tagged_doc)
            except Exception as e:
                logger.error(f"Failed to process document {doc['raw_doc_id']}: {e}")
                continue

            # Polite pause to avoid hitting aggressive burst rate limits
            time.sleep(0.5)

        if tagged_batch:
            db.save_tagged_documents(tagged_batch)
            processed_count += len(tagged_batch)
            logger.success(f"Saved {len(tagged_batch)} tagged documents (Total so far: {processed_count}).")

    logger.info(f"Phase 3 batch finished. Total processed in this run: {processed_count}")

if __name__ == "__main__":
    main()
