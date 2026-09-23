"""
tests/test_schema.py
────────────────────────────────────────────────────────────────
Unit tests for all Pydantic models in models/schema.py.

Run with:
    python -m pytest tests/test_schema.py -v

Phase 0 success criterion: all tests pass before moving to Phase 1.
"""

import pytest
from pydantic import ValidationError

from models.schema import (
    ClusterEvidence,
    DocumentMetadata,
    FailureMode,
    MemoryCueProfile,
    OpportunityCluster,
    Outcome,
    ProcessedDocument,
    ProcessingStatus,
    RawDocument,
    RetrievalType,
    SearchBehavior,
    SearchBehaviorProfile,
    Source,
    TaggedDocument,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def valid_raw_doc() -> dict:
    return {
        "source": "play_store",
        "text": "I can't find the photo from my Goa trip last year. Search is useless.",
        "rating": 2.0,
        "date": "2024-03-15T00:00:00Z",
        "url": "https://play.google.com/store/apps/details?id=com.google.android.apps.photos",
        "metadata": {
            "upvotes": None,
            "reply_count": None,
            "is_thread_starter": None,
            "app_version": "6.81",
        },
    }


@pytest.fixture
def valid_reddit_doc() -> dict:
    return {
        "source": "reddit",
        "text": "Anyone else struggling to find old photos in Google Photos? I remember it was from Christmas but I can't locate it.",
        "rating": None,
        "metadata": {
            "upvotes": 142,
            "reply_count": 23,
            "is_thread_starter": True,
            "subreddit": "googlephotos",
        },
    }


# ──────────────────────────────────────────────────────────────
# RawDocument Tests
# ──────────────────────────────────────────────────────────────

class TestRawDocument:
    def test_valid_play_store_doc(self, valid_raw_doc):
        doc = RawDocument(**valid_raw_doc)
        assert doc.source == "play_store"
        assert doc.rating == 2.0
        assert doc.id is not None  # auto-generated UUID

    def test_valid_reddit_doc_no_rating(self, valid_reddit_doc):
        doc = RawDocument(**valid_reddit_doc)
        assert doc.source == "reddit"
        assert doc.rating is None

    def test_id_auto_generated(self, valid_raw_doc):
        doc1 = RawDocument(**valid_raw_doc)
        doc2 = RawDocument(**valid_raw_doc)
        assert doc1.id != doc2.id  # each gets a unique UUID

    def test_text_is_stripped(self, valid_raw_doc):
        valid_raw_doc["text"] = "   leading spaces   "
        doc = RawDocument(**valid_raw_doc)
        assert doc.text == "leading spaces"

    def test_empty_text_raises(self, valid_raw_doc):
        valid_raw_doc["text"] = "   "
        with pytest.raises(ValidationError, match="text must not be empty"):
            RawDocument(**valid_raw_doc)

    def test_empty_string_text_raises(self, valid_raw_doc):
        valid_raw_doc["text"] = ""
        with pytest.raises(ValidationError):
            RawDocument(**valid_raw_doc)

    def test_rating_below_range_raises(self, valid_raw_doc):
        valid_raw_doc["rating"] = 0.5
        with pytest.raises(ValidationError):
            RawDocument(**valid_raw_doc)

    def test_rating_above_range_raises(self, valid_raw_doc):
        valid_raw_doc["rating"] = 5.5
        with pytest.raises(ValidationError):
            RawDocument(**valid_raw_doc)

    def test_invalid_source_raises(self, valid_raw_doc):
        valid_raw_doc["source"] = "twitter"
        with pytest.raises(ValidationError):
            RawDocument(**valid_raw_doc)

    def test_all_sources_are_valid(self, valid_raw_doc):
        for src in ["play_store", "app_store", "reddit", "community"]:
            valid_raw_doc["source"] = src
            doc = RawDocument(**valid_raw_doc)
            assert doc.source == src

    def test_is_duplicate_defaults_false(self, valid_raw_doc):
        doc = RawDocument(**valid_raw_doc)
        assert doc.is_duplicate is False


# ──────────────────────────────────────────────────────────────
# Source Enum Tests
# ──────────────────────────────────────────────────────────────

class TestSourceEnum:
    def test_all_source_values(self):
        assert Source.PLAY_STORE == "play_store"
        assert Source.APP_STORE == "app_store"
        assert Source.REDDIT == "reddit"
        assert Source.COMMUNITY == "community"


# ──────────────────────────────────────────────────────────────
# RetrievalType Enum Tests
# ──────────────────────────────────────────────────────────────

class TestRetrievalTypeEnum:
    def test_all_types_defined(self):
        types = [e.value for e in RetrievalType]
        assert "event_based" in types
        assert "person_based" in types
        assert "location_based" in types
        assert "object_based" in types
        assert "time_based" in types
        assert "emotion_based" in types
        assert "unknown" in types


# ──────────────────────────────────────────────────────────────
# FailureMode Enum Tests
# ──────────────────────────────────────────────────────────────

class TestFailureModeEnum:
    def test_all_failure_modes_defined(self):
        modes = [e.value for e in FailureMode]
        assert "search_vocabulary_mismatch" in modes
        assert "temporal_ambiguity" in modes
        assert "location_imprecision" in modes
        assert "no_album_structure" in modes
        assert "visual_only_memory" in modes
        assert "search_ux_breakdown" in modes
        assert "wrong_confidence_signal" in modes
        assert "data_loss" in modes
        assert "unknown" in modes


# ──────────────────────────────────────────────────────────────
# ProcessedDocument Tests
# ──────────────────────────────────────────────────────────────

class TestProcessedDocument:
    def test_valid_processed_doc(self):
        doc = ProcessedDocument(
            raw_doc_id="test-uuid-123",
            source="play_store",
            text_clean="can't find the photo from goa trip last year",
            text_original="I can't find the photo from my Goa trip last year!",
            language="en",
            language_confidence=0.99,
            processing_status="relevant",
            is_relevant=True,
            relevance_confidence=0.92,
            chunks=["can't find the photo from goa trip last year"],
        )
        assert doc.chunk_count == 1
        assert doc.processing_status == "relevant"

    def test_chunk_count_auto_calculated(self):
        doc = ProcessedDocument(
            raw_doc_id="uuid",
            source="reddit",
            text_clean="some text",
            text_original="Some text",
            chunks=["chunk one", "chunk two", "chunk three"],
        )
        assert doc.chunk_count == 3

    def test_default_status_is_pending(self):
        doc = ProcessedDocument(
            raw_doc_id="uuid",
            source="community",
            text_clean="help",
            text_original="help",
        )
        assert doc.processing_status == "pending"


# ──────────────────────────────────────────────────────────────
# MemoryCueProfile Tests
# ──────────────────────────────────────────────────────────────

class TestMemoryCueProfile:
    def test_all_none_is_valid(self):
        """A vague complaint with no extractable memory cues is still valid."""
        profile = MemoryCueProfile(confidence=0.3)
        assert profile.remembered_time is None
        assert profile.forgotten == []

    def test_partial_memory(self):
        profile = MemoryCueProfile(
            remembered_time="last Christmas",
            remembered_location="Goa",
            forgotten=["exact date", "album name"],
            confidence=0.85,
        )
        assert profile.remembered_location == "Goa"
        assert len(profile.forgotten) == 2

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            MemoryCueProfile(confidence=1.5)


# ──────────────────────────────────────────────────────────────
# TaggedDocument Tests
# ──────────────────────────────────────────────────────────────

class TestTaggedDocument:
    def test_minimal_tagged_doc(self):
        doc = TaggedDocument(
            processed_doc_id="proc-uuid",
            source="play_store",
            text_original="I can't find my old photos.",
        )
        assert doc.needs_review is False
        assert doc.is_data_loss is False
        assert doc.retrieval_types == []

    def test_data_loss_flagged(self):
        doc = TaggedDocument(
            processed_doc_id="proc-uuid",
            source="reddit",
            text_original="Google Photos deleted all my photos!",
            failure_modes=["data_loss"],
            primary_failure_mode="data_loss",
            is_data_loss=True,
        )
        assert doc.is_data_loss is True

    def test_multiple_retrieval_types(self):
        doc = TaggedDocument(
            processed_doc_id="proc-uuid",
            source="community",
            text_original="Photo of my mom at our Goa trip.",
            retrieval_types=["person_based", "location_based", "event_based"],
        )
        assert len(doc.retrieval_types) == 3


# ──────────────────────────────────────────────────────────────
# SearchBehaviorProfile Tests
# ──────────────────────────────────────────────────────────────

class TestSearchBehaviorProfile:
    def test_default_outcome_unknown(self):
        profile = SearchBehaviorProfile()
        assert profile.outcome == "unknown"
        assert profile.workaround_used is False

    def test_gave_up_outcome(self):
        profile = SearchBehaviorProfile(
            behaviors=["keyword_guessing", "gave_up"],
            outcome="failed",
            evidence_quote="I tried everything and just gave up.",
            confidence=0.88,
        )
        assert "gave_up" in profile.behaviors
        assert profile.outcome == "failed"


# ──────────────────────────────────────────────────────────────
# OpportunityCluster Tests
# ──────────────────────────────────────────────────────────────

class TestOpportunityCluster:
    def test_valid_cluster(self):
        cluster = OpportunityCluster(
            cluster_id=1,
            run_id="run_20240915",
            label="Users can't find photos by vague time references",
            summary=(
                "Users recall photos by approximate time ('last Christmas') "
                "but current search requires exact dates."
            ),
            primary_failure_mode="temporal_ambiguity",
            primary_retrieval_type="time_based",
            doc_count=87,
            source_breakdown={"play_store": 50, "reddit": 25, "community": 12},
            volume_score=72.0,
            severity_score=68.0,
            novelty_score=80.0,
            opportunity_score=72.0,
            top_evidence=[
                ClusterEvidence(
                    doc_id="doc-1",
                    quote="I knew it was from last Christmas but couldn't find it at all.",
                    source="play_store",
                    rating=2.0,
                )
            ],
        )
        assert cluster.opportunity_score == 72.0
        assert len(cluster.top_evidence) == 1

    def test_score_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            OpportunityCluster(
                cluster_id=1,
                run_id="run_test",
                label="test",
                summary="test",
                doc_count=10,
                volume_score=110.0,  # > 100 — invalid
                severity_score=50.0,
                novelty_score=50.0,
                opportunity_score=70.0,
            )
