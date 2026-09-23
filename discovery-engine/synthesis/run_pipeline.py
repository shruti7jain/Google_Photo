import os
import uuid
import numpy as np
from loguru import logger
from dotenv import load_dotenv
from collections import Counter

from synthesis.db import SynthesisDatabaseManager
from synthesis.clusterer import MathematicalClusterer
from synthesis.scorer import OpportunityScorer
from synthesis.labeler import ClusterLabeler
from models.schema import OpportunityCluster, ClusterEvidence

def main():
    load_dotenv()
    logger.info("Starting Fast Phase 4 (Synthesis & Clustering)")
    
    db = SynthesisDatabaseManager()
    clusterer = MathematicalClusterer()
    labeler = ClusterLabeler()
    
    # 1. Fetch data
    docs = db.fetch_embedded_documents()
    if not docs:
        logger.error("No embedded documents found!")
        return
        
    total_docs = len(docs)
    logger.info(f"Fetched {total_docs} embedded documents.")
    
    # 2. Cluster
    clusters_dict, umap_2d = clusterer.cluster_documents(docs)
    
    scorer = OpportunityScorer(total_corpus_size=total_docs)
    run_id = str(uuid.uuid4())
    
    final_clusters = []
    
    # 3. Analyze each cluster
    for cluster_id, c_docs in clusters_dict.items():
        logger.info(f"Processing Cluster {cluster_id} ({len(c_docs)} docs)...")
        
        # Get representatives
        top_docs = clusterer.get_top_representative_docs(c_docs, top_k=20)
        
        # Label via AI
        label_res = labeler.label_cluster(top_docs)
        
        # Score
        scores = scorer.score_cluster(c_docs)
        
        # Source breakdown
        sources = [d['source'] for d in c_docs]
        source_breakdown = dict(Counter(sources))
        
        # Centroid (2D for viz)
        coords_2d = np.array([d['2d_coords'] for d in c_docs])
        centroid_2d = np.mean(coords_2d, axis=0)
        
        # Build Evidence
        evidence = []
        for d in top_docs[:5]:  # Top 5 for evidence
            ev = ClusterEvidence(
                doc_id=d['raw_doc_id'],
                quote=d['text_original'],
                source=d['source'],
                rating=d.get('rating'),
                date=d.get('date'),
                url=d.get('url'),
                upvotes=d.get('upvotes')
            )
            evidence.append(ev)
            
        cluster_obj = OpportunityCluster(
            cluster_id=cluster_id,
            run_id=run_id,
            label=label_res.label,
            summary=label_res.summary,
            primary_failure_mode=label_res.primary_failure_mode,
            primary_retrieval_type=label_res.primary_retrieval_type,
            doc_count=len(c_docs),
            source_breakdown=source_breakdown,
            volume_score=scores['volume_score'],
            severity_score=scores['severity_score'],
            novelty_score=scores['novelty_score'],
            opportunity_score=scores['opportunity_score'],
            centroid_x=float(centroid_2d[0]),
            centroid_y=float(centroid_2d[1]),
            top_evidence=evidence
        )
        final_clusters.append(cluster_obj)
        
    # 4. Save
    db.save_clusters(final_clusters)
    logger.success(f"Saved {len(final_clusters)} fully labeled and scored clusters to DB!")

if __name__ == "__main__":
    main()
