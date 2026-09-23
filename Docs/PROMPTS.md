# Prompts Reference & Catalog

> **Google Photos AI-Powered Photo Retrieval Discovery Engine**  
> Version: 2.0 (Unified & Multi-Dimensional Analyzer)

---

## 1. Unified 4-Dimensional Analyzer (`prompts/unified_analyzer.txt`)

- **Purpose:** Extracts all 4 customer research dimensions (Retrieval Pattern, Memory Cue, Failure Mode, Search Behavior) in a single LLM completion to optimize latency and rate-limit headroom.
- **Model:** `openai/gpt-oss-20b` (Groq inference)
- **Temperature:** 0.1 (near-deterministic)
- **Response Format:** `{"type": "json_object"}`

### Schema Extracted:
```json
{
  "retrieval_types": ["event_based", "person_based", "location_based", "object_based", "time_based", "emotion_based", "unknown"],
  "retrieval_description": "concise one-line summary",
  "retrieval_confidence": 0.95,
  "memory_cue": {
    "remembered_time": "time or null",
    "remembered_location": "location or null",
    "remembered_people": "person or null",
    "remembered_object": "object or null",
    "remembered_emotion": "emotion or null",
    "forgotten": ["items explicitly forgotten"],
    "uncertainty_present": false,
    "confidence": 0.95
  },
  "failure_modes": ["search_vocabulary_mismatch", "..."],
  "primary_failure_mode": "search_vocabulary_mismatch",
  "failure_evidence_quote": "exact quote",
  "failure_confidence": 0.95,
  "is_data_loss": false,
  "search_behavior": {
    "behaviors": ["keyword_guessing", "approximate_date_browsing"],
    "outcome": "failed",
    "evidence_quote": "exact quote or null",
    "workaround_used": false,
    "workaround_tool": null,
    "perspective": "first_person",
    "confidence": 0.95
  }
}
```

---

## 2. Cluster Labeler (`synthesis/labeler.py`)

- **Purpose:** Analyzes 20 representative verbatim feedback quotes from a mathematical cluster to synthesize a clean, actionable label and summary.
- **Model:** `openai/gpt-oss-120b` (Groq inference)
- **Temperature:** 0.2

### Schema Extracted:
```json
{
  "label": "A concise, 5-10 word title for this cluster",
  "summary": "A 2-sentence summary explaining what the users are trying to do, and why they are failing.",
  "primary_failure_mode": "one of the allowed failure modes",
  "primary_retrieval_type": "one of the allowed retrieval types"
}
```

---

## 3. Interactive Reviewer Chatbot (`dashboard/api.py`)

- **Purpose:** Answers ad-hoc user/PM inquiries in real time across the mathematical failure clusters and reviews.
- **Model:** `openai/gpt-oss-20b` (Groq inference)
- **Temperature:** 0.3
- **Output:** Clean, sanitized HTML blocks styled for the dashboard with verbatim evidence cards.
