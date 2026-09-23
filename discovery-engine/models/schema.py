"""
models/schema.py
─────────────────────────────────────────────────────────────────
Canonical Pydantic data models (common data contract) shared
across all pipeline layers:

    ┌─────────────┐
    │  RawDocument │  ← produced by ingestion layer
    └──────┬──────┘
           │
    ┌──────▼──────────┐
    │ ProcessedDocument│  ← produced by preprocessing layer
    └──────┬──────────┘
           │
    ┌──────▼──────┐
    │ TaggedDocument│  ← produced by analysis layer
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  ClusterDoc  │  ← produced by synthesis layer
    └─────────────┘

All downstream stages MUST accept and produce these models.
Do NOT define ad-hoc dicts in individual modules.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ──────────────────────────────────────────────────────────────
# Enums (mirrors config.yaml values — keep in sync)
# ──────────────────────────────────────────────────────────────

class Source(str, Enum):
    PLAY_STORE = "play_store"
    APP_STORE = "app_store"
    REDDIT = "reddit"
    COMMUNITY = "community"


class RetrievalType(str, Enum):
    EVENT_BASED = "event_based"
    PERSON_BASED = "person_based"
    LOCATION_BASED = "location_based"
    OBJECT_BASED = "object_based"
    TIME_BASED = "time_based"
    EMOTION_BASED = "emotion_based"
    UNKNOWN = "unknown"


class FailureMode(str, Enum):
    SEARCH_VOCABULARY_MISMATCH = "search_vocabulary_mismatch"
    TEMPORAL_AMBIGUITY = "temporal_ambiguity"
    LOCATION_IMPRECISION = "location_imprecision"
    NO_ALBUM_STRUCTURE = "no_album_structure"
    VISUAL_ONLY_MEMORY = "visual_only_memory"
    SEARCH_UX_BREAKDOWN = "search_ux_breakdown"
    WRONG_CONFIDENCE_SIGNAL = "wrong_confidence_signal"
    DATA_LOSS = "data_loss"
    UNKNOWN = "unknown"


class SearchBehavior(str, Enum):
    APPROXIMATE_DATE_BROWSING = "approximate_date_browsing"
    KEYWORD_GUESSING = "keyword_guessing"
    ALBUM_SCANNING = "album_scanning"
    ASKED_SOMEONE_ELSE = "asked_someone_else"
    GAVE_UP = "gave_up"
    USED_THIRD_PARTY_TOOL = "used_third_party_tool"
    UNKNOWN_BROWSING = "unknown_browsing"


class Outcome(str, Enum):
    FAILED = "failed"
    PARTIAL = "partial"
    SUCCEEDED = "succeeded"
    UNKNOWN = "unknown"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
    UNCERTAIN = "uncertain"
    FAILED = "failed"


# ──────────────────────────────────────────────────────────────
# 1. RawDocument — produced by ingestion layer
# ──────────────────────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    """Source-specific metadata, all fields optional."""
    upvotes: Optional[int] = None
    reply_count: Optional[int] = None
    is_thread_starter: Optional[bool] = None
    app_version: Optional[str] = None
    storefront: Optional[str] = None           # App Store country code
    subreddit: Optional[str] = None            # Reddit subreddit name
    extra: Optional[dict[str, Any]] = None     # Catch-all for unexpected fields


class RawDocument(BaseModel):
    """
    Canonical schema for every ingested document.
    All four source connectors must produce this model.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: Source
    text: str
    rating: Optional[float] = Field(
        default=None,
        ge=1.0, le=5.0,
        description="Star rating (1–5). Null for Reddit/Community."
    )
    date: Optional[datetime] = None
    url: Optional[str] = None
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)

    # Populated during deduplication
    simhash: Optional[str] = None
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None        # id of the canonical document

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must not be empty or whitespace-only")
        return v.strip()

    @field_validator("rating")
    @classmethod
    def rating_only_for_reviews(cls, v: Optional[float]) -> Optional[float]:
        # Rating is valid only for store reviews; Reddit/Community should pass None
        return v

    model_config = {"use_enum_values": True}


# ──────────────────────────────────────────────────────────────
# 2. ProcessedDocument — produced by preprocessing layer
# ──────────────────────────────────────────────────────────────

class ProcessedDocument(BaseModel):
    """
    Extends RawDocument with preprocessing outputs:
    language detection, relevance classification, chunks, embedding.
    """
    # ── Core reference ──────────────────────────────────────
    raw_doc_id: str                            # FK → RawDocument.id
    source: Source
    text_clean: str                            # Normalised text (HTML stripped, encoding fixed)
    text_original: str                         # Preserved verbatim original for evidence display

    # ── Language ─────────────────────────────────────────────
    language: Optional[str] = None             # ISO 639-1 code, e.g. "en"
    language_confidence: Optional[float] = None

    # ── Relevance classification ──────────────────────────────
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    is_relevant: Optional[bool] = None
    relevance_confidence: Optional[float] = None

    # ── Chunking ─────────────────────────────────────────────
    chunks: list[str] = Field(default_factory=list)
    chunk_count: int = 0

    # ── Embedding ────────────────────────────────────────────
    embedding: Optional[list[float]] = None    # Stored in pgvector; None in Python objects
    embedding_model: Optional[str] = None

    # ── Passthrough metadata ─────────────────────────────────
    rating: Optional[float] = None
    date: Optional[datetime] = None
    url: Optional[str] = None

    @model_validator(mode="after")
    def set_chunk_count(self) -> "ProcessedDocument":
        self.chunk_count = len(self.chunks)
        return self

    model_config = {"use_enum_values": True}


# ──────────────────────────────────────────────────────────────
# 3. TaggedDocument — produced by analysis layer
# ──────────────────────────────────────────────────────────────

class MemoryCueProfile(BaseModel):
    """What the user remembers vs. has forgotten."""
    remembered_time: Optional[str] = None       # e.g. "last summer", "Christmas 2022"
    remembered_location: Optional[str] = None   # e.g. "Goa", "the beach"
    remembered_people: Optional[str] = None     # Anonymised: "[PERSON]" or role "my mom"
    remembered_object: Optional[str] = None     # e.g. "medicine bottle", "blue dress"
    remembered_emotion: Optional[str] = None    # e.g. "happy", "funny moment"
    forgotten: list[str] = Field(default_factory=list)   # e.g. ["exact date", "album name"]
    uncertainty_present: bool = False           # User expressed uncertainty ("I think it was...")
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class SearchBehaviorProfile(BaseModel):
    """How the user attempted to find the photo."""
    behaviors: list[SearchBehavior] = Field(default_factory=list)
    outcome: Outcome = Outcome.UNKNOWN
    evidence_quote: Optional[str] = None        # Verbatim quote from document
    workaround_used: bool = False
    workaround_tool: Optional[str] = None       # e.g. "Google Drive", "iCloud"
    perspective: Optional[str] = "first_person"           # "first_person" | "third_person"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class TaggedDocument(BaseModel):
    """
    Fully analysed document with all four analyzer outputs attached.
    Input to the synthesis/clustering layer.
    """
    processed_doc_id: str                       # FK → ProcessedDocument.raw_doc_id
    source: Source
    text_original: str
    rating: Optional[float] = None
    date: Optional[datetime] = None
    url: Optional[str] = None

    # ── Analyzer A: Retrieval Pattern ────────────────────────
    retrieval_types: list[RetrievalType] = Field(default_factory=list)
    retrieval_description: Optional[str] = None
    retrieval_confidence: float = Field(ge=0.0, le=1.0, default=0.0)

    # ── Analyzer B: Memory Cue ────────────────────────────────
    memory_cue: Optional[MemoryCueProfile] = None

    # ── Analyzer C: Failure Mode ──────────────────────────────
    failure_modes: list[FailureMode] = Field(default_factory=list)
    primary_failure_mode: Optional[FailureMode] = None
    failure_evidence_quote: Optional[str] = None
    failure_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    is_data_loss: bool = False                  # Route to separate analysis if True

    # ── Analyzer D: Search Behavior ───────────────────────────
    search_behavior: Optional[SearchBehaviorProfile] = None

    # ── QA Flags ─────────────────────────────────────────────
    needs_review: bool = False                  # Flag if any confidence < threshold
    low_confidence_dimensions: list[str] = Field(default_factory=list)

    # ── Vagueness signal ─────────────────────────────────────
    vagueness_high: bool = False                # True if user gives no specific memory cues

    model_config = {"use_enum_values": True}


# ──────────────────────────────────────────────────────────────
# 4. ClusterEvidence — produced by synthesis layer
# ──────────────────────────────────────────────────────────────

class ClusterEvidence(BaseModel):
    """A single verbatim quote linked to a cluster."""
    doc_id: str
    quote: str
    source: Source
    rating: Optional[float] = None
    date: Optional[datetime] = None
    url: Optional[str] = None
    upvotes: Optional[int] = None


class OpportunityCluster(BaseModel):
    """
    A discovered pain-point cluster with its label, score, and evidence.
    Final output of the synthesis layer; consumed by the output layer.
    """
    cluster_id: int
    run_id: str                                 # Versioned run identifier

    # ── Labeling ─────────────────────────────────────────────
    label: str                                  # 1-sentence cluster label
    summary: str                                # 2-sentence pain point summary
    primary_failure_mode: Optional[FailureMode] = None
    primary_retrieval_type: Optional[RetrievalType] = None

    # ── Composition ──────────────────────────────────────────
    doc_count: int
    source_breakdown: dict[str, int] = Field(default_factory=dict)   # source → count

    # ── Opportunity Scoring ───────────────────────────────────
    volume_score: float = Field(ge=0.0, le=100.0)
    severity_score: float = Field(ge=0.0, le=100.0)
    novelty_score: float = Field(ge=0.0, le=100.0)
    opportunity_score: float = Field(ge=0.0, le=100.0)

    # ── Evidence ─────────────────────────────────────────────
    top_evidence: list[ClusterEvidence] = Field(default_factory=list)

    # ── UMAP coordinates (for scatter plot) ──────────────────
    centroid_x: Optional[float] = None
    centroid_y: Optional[float] = None

    model_config = {"use_enum_values": True}
