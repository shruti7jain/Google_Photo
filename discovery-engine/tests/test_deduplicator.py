import pytest
from datetime import datetime

from ingestion.deduplicator import Deduplicator
from models.schema import RawDocument, Source, DocumentMetadata

@pytest.fixture
def base_doc():
    return RawDocument(
        source=Source.PLAY_STORE,
        text="This is a test review about finding photos.",
        rating=3.0,
        date=datetime(2023, 1, 1),
        metadata=DocumentMetadata(upvotes=10)
    )

def test_deduplicator_first_doc(base_doc):
    dedup = Deduplicator()
    processed = dedup.process_document(base_doc)
    assert not processed.is_duplicate
    assert processed.simhash is not None

def test_deduplicator_exact_duplicate(base_doc):
    dedup = Deduplicator()
    dedup.process_document(base_doc)
    
    dup_doc = RawDocument(
        source=Source.PLAY_STORE,
        text="This is a test review about finding photos.",
        rating=2.0,
        date=datetime(2023, 1, 2),
        metadata=DocumentMetadata(upvotes=5)
    )
    processed_dup = dedup.process_document(dup_doc)
    
    # Original has higher score (rating 3 + date + upvotes=10 = 1+0.5+1 = 2.5) vs dup (1+0.5+0.5=2)
    assert processed_dup.is_duplicate
    assert processed_dup.duplicate_of == base_doc.id

def test_deduplicator_richer_duplicate_replaces_original(base_doc):
    dedup = Deduplicator()
    dedup.process_document(base_doc)
    
    richer_doc = RawDocument(
        source=Source.PLAY_STORE,
        text="This is a test review about finding photos.",
        rating=5.0, # Higher rating
        date=datetime(2023, 1, 2),
        metadata=DocumentMetadata(upvotes=50) # Way more upvotes (5.0) -> Score: 1 + 0.5 + 5 = 6.5
    )
    processed = dedup.process_document(richer_doc)
    
    # The new one is richer, so it should NOT be flagged as duplicate itself
    # but the original should be updated to be a duplicate of the new one.
    assert not processed.is_duplicate
    
    # The original document in the canonical list was replaced
    assert base_doc.is_duplicate
    assert base_doc.duplicate_of == richer_doc.id
    assert dedup.canonical_docs[richer_doc.id] == richer_doc

def test_deduplicator_different_docs_not_duplicates():
    dedup = Deduplicator()
    doc1 = RawDocument(
        source=Source.PLAY_STORE,
        text="This is a test review about finding photos.",
        rating=3.0,
        metadata=DocumentMetadata()
    )
    doc2 = RawDocument(
        source=Source.PLAY_STORE,
        text="I love this app, it is so great and amazing and I use it every day for my cat pictures.",
        rating=5.0,
        metadata=DocumentMetadata()
    )
    
    p1 = dedup.process_document(doc1)
    p2 = dedup.process_document(doc2)
    
    assert not p1.is_duplicate
    assert not p2.is_duplicate
