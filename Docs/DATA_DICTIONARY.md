# Data Dictionary: PostgreSQL Database Schema

> **Discovery Engine Database Catalog**  
> Engine: PostgreSQL 15+ / 16  
> ORM / Interface: SQLAlchemy & Pydantic v2

---

## 1. `raw_documents` (Phase 1)
Stores raw, uncleaned feedback records scraped directly from external sources.

| Column | Type | Nullable | Description |
|---|---|:---:|---|
| `id` | `TEXT` (PK) | No | Auto-generated UUID-v4 |
| `source` | `TEXT` | No | Source platform (`play_store`, `app_store`, `reddit`, `community`) |
| `text` | `TEXT` | No | Raw verbatim feedback text |
| `rating` | `FLOAT` | Yes | 1.0 to 5.0 store rating (null for forum posts) |
| `date` | `TIMESTAMPTZ` | Yes | Publication timestamp |
| `url` | `TEXT` | Yes | Source URL link |
| `metadata` | `JSONB` | Yes | Platform-specific metadata (upvotes, replies, version) |
| `simhash` | `TEXT` | Yes | 64-bit SimHash fingerprint string |
| `is_duplicate`| `BOOLEAN` | No | Flag indicating near-duplicate record |
| `duplicate_of`| `TEXT` | Yes | FK referencing original document ID |
| `ingested_at` | `TIMESTAMPTZ` | No | Database ingestion timestamp |

---

## 2. `processed_documents` (Phase 2)
Stores normalized, noise-filtered, and embedded documents.

| Column | Type | Nullable | Description |
|---|---|:---:|---|
| `raw_doc_id` | `TEXT` (PK) | No | Foreign Key referencing `raw_documents.id` |
| `source` | `TEXT` | No | Source platform identifier |
| `text_clean` | `TEXT` | No | Normalized text (URLs, excessive newlines stripped) |
| `text_original`| `TEXT` | No | Original verbatim text preserved for evidence display |
| `language` | `TEXT` | Yes | Detected ISO language code (e.g. `en`) |
| `language_confidence` | `FLOAT` | Yes | Confidence score (0.0 to 1.0) |
| `processing_status` | `TEXT` | No | `pending`, `processed`, `failed` |
| `is_relevant` | `BOOLEAN` | Yes | Boolean classification flag |
| `relevance_confidence` | `FLOAT` | Yes | Confidence score |
| `chunks` | `TEXT[]` | Yes | Paragraph chunks for documents > 512 tokens |
| `chunk_count`| `INTEGER` | No | Number of chunks generated |
| `embedding` | `VECTOR(384)` / `BYTEA` | Yes | 384-dimensional dense semantic vector (`all-MiniLM-L6-v2`) |
| `embedding_model` | `TEXT` | Yes | Name of embedding model used |
| `rating` | `FLOAT` | Yes | Store rating |
| `date` | `TIMESTAMPTZ` | Yes | Timestamp |
| `url` | `TEXT` | Yes | Reference URL |
| `processed_at` | `TIMESTAMPTZ` | No | Processing timestamp |

---

## 3. `tagged_documents` (Phase 3)
Stores 4-dimensional AI-extracted metadata for each document.

| Column | Type | Nullable | Description |
|---|---|:---:|---|
| `processed_doc_id` | `TEXT` (PK) | No | Foreign Key referencing `processed_documents.raw_doc_id` |
| `source` | `TEXT` | No | Source platform identifier |
| `text_original` | `TEXT` | No | Verbatim feedback text |
| `rating` | `FLOAT` | Yes | Store star rating |
| `date` | `TIMESTAMPTZ` | Yes | Publication date |
| `url` | `TEXT` | Yes | Source URL |
| `retrieval_types` | `TEXT[]` | No | Array of classified retrieval types |
| `retrieval_description` | `TEXT` | Yes | One-line summary of what user tried to find |
| `retrieval_confidence` | `NUMERIC` | No | Confidence score (0.0 to 1.0) |
| `memory_cue` | `JSONB` | Yes | Serialized `MemoryCueProfile` object |
| `failure_modes` | `TEXT[]` | No | Array of identified failure modes |
| `primary_failure_mode` | `TEXT` | Yes | Dominant failure mode taxonomy |
| `failure_evidence_quote` | `TEXT` | Yes | Verbatim snippet proving failure |
| `failure_confidence` | `NUMERIC` | No | Failure confidence score |
| `is_data_loss` | `BOOLEAN` | No | Flag if user reports permanent photo loss |
| `search_behavior` | `JSONB` | Yes | Serialized `SearchBehaviorProfile` object |
| `needs_review` | `BOOLEAN` | No | QA flag if confidence < 0.6 |
| `low_confidence_dimensions` | `TEXT[]` | Yes | List of dimensions with low confidence |
| `vagueness_high` | `BOOLEAN` | No | Flag if user gives no specific memory cues |
| `tagged_at` | `TIMESTAMPTZ` | No | Timestamp of tagging run |

---

## 4. `clusters` (Phase 4)
Mathematical clusters discovered through UMAP + HDBSCAN.

| Column | Type | Nullable | Description |
|---|---|:---:|---|
| `cluster_id` | `INTEGER` (PK) | No | Cluster identifier (-1 = noise) |
| `run_id` | `TEXT` | No | Unique clustering execution ID |
| `label` | `TEXT` | No | AI-synthesized concise cluster title |
| `summary` | `TEXT` | No | 2-sentence summary of the core breakdown |
| `primary_failure_mode` | `TEXT` | Yes | Dominant failure mode across cluster |
| `primary_retrieval_type` | `TEXT` | Yes | Dominant retrieval type across cluster |
| `doc_count` | `INTEGER` | No | Number of documents assigned to cluster |
| `source_breakdown` | `JSONB` | Yes | Counts per source platform |
| `volume_score` | `FLOAT` | No | Normalized volume score (0 to 100) |
| `severity_score` | `FLOAT` | No | Percentage of ratings ≤ 2.0 |
| `novelty_score` | `FLOAT` | No | Novelty score against known features |
| `opportunity_score` | `FLOAT` | No | Composite weighted score: `(Vol*0.4)+(Sev*0.4)+(Nov*0.2)` |
| `centroid_x` | `FLOAT` | Yes | 2D UMAP coordinate X for visualization |
| `centroid_y` | `FLOAT` | Yes | 2D UMAP coordinate Y for visualization |
| `created_at` | `TIMESTAMPTZ` | No | Generation timestamp |

---

## 5. `cluster_evidence` (Phase 4)
Representative verbatim quotes linked to each opportunity cluster.

| Column | Type | Nullable | Description |
|---|---|:---:|---|
| `id` | `INTEGER` (PK) | No | Serial sequence identifier |
| `cluster_id` | `INTEGER` | No | Foreign Key referencing `clusters.cluster_id` |
| `doc_id` | `TEXT` | No | Foreign Key referencing `raw_documents.id` |
| `quote` | `TEXT` | No | Verbatim excerpt |
| `source` | `TEXT` | No | Source platform identifier |
| `rating` | `FLOAT` | Yes | Store rating |
| `date` | `TIMESTAMPTZ` | Yes | Review date |
| `url` | `TEXT` | Yes | Source link |
| `upvotes` | `INTEGER` | Yes | Platform upvote count |
