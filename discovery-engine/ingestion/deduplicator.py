from typing import List, Dict
from simhash import Simhash
from models.schema import RawDocument
from loguru import logger

class Deduplicator:
    def __init__(self, distance_threshold: int = 3):
        self.distance_threshold = distance_threshold
        # Stores canonical documents by their ID
        self.canonical_docs: Dict[str, RawDocument] = {}
        # Pre-calculated simhashes for canonical docs
        self.canonical_simhashes: Dict[str, Simhash] = {}

    def _get_richness_score(self, doc: RawDocument) -> float:
        score = 0.0
        if doc.metadata.upvotes is not None:
            score += doc.metadata.upvotes * 0.1
        if doc.rating is not None:
            score += 1.0
        if doc.date is not None:
            score += 0.5
        return score

    def process_document(self, doc: RawDocument) -> RawDocument:
        """
        Process a document. If it's a near-duplicate, flag it.
        If it replaces an existing canonical doc (because it's richer), update the canonical.
        """
        doc_simhash = Simhash(doc.text)
        doc.simhash = str(doc_simhash.value)
        
        # Check against existing canonical docs
        for canon_id, canon_simhash in self.canonical_simhashes.items():
            if doc_simhash.distance(canon_simhash) < self.distance_threshold:
                canon_doc = self.canonical_docs[canon_id]
                
                doc_richness = self._get_richness_score(doc)
                canon_richness = self._get_richness_score(canon_doc)
                
                if doc_richness > canon_richness:
                    # New doc is better, it becomes canonical
                    doc.is_duplicate = False
                    canon_doc.is_duplicate = True
                    canon_doc.duplicate_of = doc.id
                    
                    self.canonical_docs[doc.id] = doc
                    self.canonical_simhashes[doc.id] = doc_simhash
                    del self.canonical_docs[canon_id]
                    del self.canonical_simhashes[canon_id]
                    
                    return doc
                else:
                    # New doc is duplicate
                    doc.is_duplicate = True
                    doc.duplicate_of = canon_id
                    return doc
        
        # Not a duplicate
        self.canonical_docs[doc.id] = doc
        self.canonical_simhashes[doc.id] = doc_simhash
        return doc
