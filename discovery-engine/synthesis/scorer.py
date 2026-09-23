from typing import List, Dict, Any

class OpportunityScorer:
    def __init__(self, total_corpus_size: int):
        self.total_corpus_size = total_corpus_size
        
    def score_cluster(self, cluster_docs: List[Dict[str, Any]]) -> Dict[str, float]:
        if not cluster_docs:
            return {"volume_score": 0.0, "severity_score": 0.0, "novelty_score": 0.0, "opportunity_score": 0.0}
            
        # Volume: percentage of total docs
        volume_score = (len(cluster_docs) / self.total_corpus_size) * 100
        
        # Severity: percentage of docs with rating <= 2
        severe_count = 0
        total_rated = 0
        for doc in cluster_docs:
            rating = doc.get('rating')
            if rating is not None:
                total_rated += 1
                if float(rating) <= 2.0:
                    severe_count += 1
                    
        severity_score = (severe_count / total_rated * 100) if total_rated > 0 else 50.0
        
        # Ignoring novelty for now (50/50 split)
        opportunity_score = (volume_score * 0.5) + (severity_score * 0.5)
        
        return {
            "volume_score": min(volume_score, 100.0),
            "severity_score": min(severity_score, 100.0),
            "novelty_score": 0.0,
            "opportunity_score": min(opportunity_score, 100.0)
        }
