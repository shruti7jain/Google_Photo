from typing import List
import numpy as np

class BaseEmbedder:
    def embed(self, text: str) -> List[float]:
        raise NotImplementedError

class MiniLMEmbedder(BaseEmbedder):
    """
    Local embedding model using sentence-transformers.
    Uses all-MiniLM-L6-v2 which outputs 384-dimensional vectors.
    """
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384

    def embed(self, text: str) -> List[float]:
        # Returns a normalized dense vector
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]
