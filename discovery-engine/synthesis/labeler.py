import os
import json
from typing import List, Dict, Any
from pydantic import BaseModel
from loguru import logger
from groq import Groq
from models.schema import FailureMode, RetrievalType

class ClusterLabelOutput(BaseModel):
    label: str
    summary: str
    primary_failure_mode: FailureMode
    primary_retrieval_type: RetrievalType

class ClusterLabeler:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        self.client = Groq(api_key=api_key)
        # Using a larger model that has a fresh daily token quota
        self.model = "openai/gpt-oss-120b"
        
        self.system_prompt = """You are an expert Google Photos Product Manager. 
You are given 20 verbatim user feedback quotes that a mathematical clustering algorithm has grouped together because they represent the SAME underlying product pain point.

Your task is to analyze these 20 quotes and output a JSON object describing the core issue.
The JSON must perfectly match this structure:
{
  "label": "A concise, 5-10 word title for this cluster (e.g., 'Inability to search by exact date')",
  "summary": "A 2-sentence summary explaining what the users are trying to do, and why they are failing.",
  "primary_failure_mode": "<one of the allowed failure modes>",
  "primary_retrieval_type": "<one of the allowed retrieval types>"
}

Allowed failure modes: search_vocabulary_mismatch, temporal_ambiguity, location_imprecision, no_album_structure, visual_only_memory, search_ux_breakdown, wrong_confidence_signal, data_loss, unknown
Allowed retrieval types: event_based, person_based, location_based, object_based, time_based, emotion_based, unknown
"""

    def label_cluster(self, representative_docs: List[Dict[str, Any]]) -> ClusterLabelOutput:
        quotes = [d['text_original'] for d in representative_docs]
        user_prompt = "Here are the 20 quotes for this cluster:\n\n"
        for i, q in enumerate(quotes):
            user_prompt += f"{i+1}. {q}\n"
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            content = response.choices[0].message.content
            parsed = json.loads(content)
            return ClusterLabelOutput(**parsed)
        except Exception as e:
            logger.error(f"Failed to label cluster: {e}")
            return ClusterLabelOutput(
                label="Unlabeled Cluster",
                summary="Failed to generate summary.",
                primary_failure_mode=FailureMode.UNKNOWN,
                primary_retrieval_type=RetrievalType.UNKNOWN
            )
