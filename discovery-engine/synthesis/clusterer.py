import numpy as np
import umap
import hdbscan
from typing import List, Dict, Any, Tuple
from loguru import logger
from sklearn.metrics.pairwise import cosine_similarity

class MathematicalClusterer:
    def __init__(self):
        pass

    def cluster_documents(self, docs: List[Dict[str, Any]]) -> Tuple[Dict[int, List[Dict[str, Any]]], np.ndarray]:
        logger.info(f"Running UMAP and HDBSCAN on {len(docs)} documents...")
        
        embeddings = np.array([doc['embedding'] for doc in docs])
        
        # Reduce to 10D for HDBSCAN
        reducer = umap.UMAP(n_components=10, metric='cosine', n_neighbors=15, min_dist=0.1, random_state=42)
        umap_embeddings = reducer.fit_transform(embeddings)
        
        # Reduce to 2D for Visualization/Centroids
        reducer_2d = umap.UMAP(n_components=2, metric='cosine', n_neighbors=15, min_dist=0.1, random_state=42)
        umap_2d = reducer_2d.fit_transform(embeddings)
        
        clusterer = hdbscan.HDBSCAN(min_cluster_size=20, min_samples=5, metric='euclidean')
        cluster_labels = clusterer.fit_predict(umap_embeddings)
        
        clusters = {}
        for i, label in enumerate(cluster_labels):
            if label == -1: # Noise
                continue
            if label not in clusters:
                clusters[label] = []
            
            doc_copy = docs[i].copy()
            doc_copy['2d_coords'] = umap_2d[i]
            clusters[label].append(doc_copy)
            
        logger.info(f"Found {len(clusters)} clusters (excluding noise).")
        return clusters, umap_2d

    def get_top_representative_docs(self, cluster_docs: List[Dict[str, Any]], top_k: int = 20) -> List[Dict[str, Any]]:
        if not cluster_docs:
            return []
            
        embeddings = np.array([d['embedding'] for d in cluster_docs])
        centroid = np.mean(embeddings, axis=0).reshape(1, -1)
        
        similarities = cosine_similarity(embeddings, centroid).flatten()
        
        # Sort indices by similarity descending
        top_indices = similarities.argsort()[::-1][:top_k]
        
        return [cluster_docs[i] for i in top_indices]
