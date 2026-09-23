# Implementation Plan: AI-Powered Photo Retrieval Discovery Engine

> **Based on:** [`context.md`](context.md) · [`architecture.md`](architecture.md)
> **Goal:** Build a discovery engine that surfaces high-signal retrieval pain points from real user feedback, enabling a PM to identify a meaningful improvement opportunity for Google Photos.

---

## Plan Summary

| Phase | Name | Duration | Output |
|---|---|---|---|
| 0 | Foundation & Setup | Week 1 | Dev environment, repo, schemas |
| 1 | Data Ingestion | Week 2–3 | Raw document store with 4,000–5,000 records |
| 2 | Preprocessing & Embedding | Week 3–4 | Clean, embedded, relevance-filtered corpus |
| 3 | AI Analysis Layer | Week 4–6 | Tagged documents (pattern, memory, failure, behavior) |
| 4 | Synthesis & Clustering | Week 6–7 | Ranked opportunity clusters with evidence |
| 5 | Output & Delivery | Week 7–8 | PM Dashboard + Insight Reports |
| 6 | Iteration & Hardening | Week 9–10 | Refined model, edge case handling, future roadmap |

**Total Timeline: ~10 weeks (solo/small team)**

---

## Phase 0 — Foundation & Setup

### Duration
Week 1 (Days 1–5)

### Goals
- Establish the project scaffold, tooling, and data contracts
- Agree on the scope, sources, and PM-facing deliverables upfront

### Tasks

#### 0.1 Repository & Project Structure
```
discovery-engine/
├── ingestion/          # Source connectors
├── preprocessing/      # Filtering, chunking, embedding
├── analysis/           # LLM-based analyzers
├── synthesis/          # Clustering, scoring
├── output/             # Dashboard, reports
├── data/
│   ├── raw/            # Ingested documents (not committed)
│   └── processed/      # Embedded + tagged documents
├── prompts/            # All LLM prompt templates (versioned)
├── notebooks/          # Exploratory analysis
├── tests/              # Unit + integration tests
├── config.yaml         # Source configs, model choices, thresholds
└── README.md
```

#### 0.2 Environment Setup
- [ ] Create virtual environment (Python 3.11+)
- [ ] Install core dependencies: `groq`, `apify-client`, `google-play-scraper`, `app-store-scraper`, `sentence-transformers`, `umap-learn`, `hdbscan`, `pandas`, `psycopg2`, `pinecone-client`
- [ ] Set up PostgreSQL (structured store) + local file store (raw JSON dumps)
- [ ] Configure `.env` for API keys: **Groq API key**, Apify API token, SerpAPI (Play Store fallback), Apple Search API

#### 0.3 Common Data Schema
Define and validate the canonical document schema used throughout the pipeline:

```json
{
  "id": "uuid-v4",
  "source": "play_store | app_store | reddit | community",
  "text": "raw user text",
  "rating": null,
  "date": "2024-03-15T00:00:00Z",
  "url": "https://...",
  "metadata": {
    "upvotes": 0,
    "reply_count": 0,
    "is_thread_starter": true,
    "app_version": null
  }
}
```

#### 0.4 Stakeholder Alignment
- [ ] Confirm PM-facing output format (dashboard vs. report vs. both)
- [ ] Define "success" for Phase 1 (minimum corpus size per source)
- [ ] Agree on language scope (English-only for v1)

### Deliverables
- Initialized Git repo with folder structure
- Working `.env` and `config.yaml`
- Schema definition with Pydantic validation model
- PostgreSQL tables created and migrated

### Success Criteria
- `python -m pytest tests/test_schema.py` passes
- All API credentials verified with test calls

---

## Phase 1 — Data Ingestion

### Duration
Week 2–3 (Days 6–15)

### Goals
- Build reliable, rate-limit-aware connectors for all four data sources
- Normalize all raw data into the common schema
- Deduplicate and store in the raw document store

### Tasks

#### 1.1 Google Play Store Connector
- Use `google-play-scraper` Python library
- Pull reviews for `com.google.android.apps.photos`
- Sort by newest + most relevant
- Target: **1,500–2,000 reviews**

```python
# ingestion/play_store.py
from google_play_scraper import reviews, Sort

result, continuation_token = reviews(
    'com.google.android.apps.photos',
    lang='en', country='us',
    sort=Sort.NEWEST,
    count=2000
)
```

#### 1.2 Apple App Store Connector
- Use `app-store-scraper` Python library
- App ID: `962194608` (Google Photos)
- Pull reviews from US + IN storefronts
- Target: **1,000–1,500 reviews**

#### 1.3 Reddit Connector (Apify)
- Use the **Apify Reddit Scraper** actor (`trudax/reddit-scraper`)
- Subreddits: `r/googlephotos`, `r/AndroidQuestions`, `r/iphone`
- Search queries: `"google photos search"`, `"can't find photo"`, `"lost photos"`, `"find old photo"`
- Pull posts + top-level comments
- Target: **800–1,000 posts/comments**

```python
# ingestion/reddit.py
from apify_client import ApifyClient

client = ApifyClient(token=APIFY_API_TOKEN)
run = client.actor("trudax/reddit-scraper").call(run_input={
    "searches": ["google photos can't find photo", "lost google photos"],
    "maxItems": 1000,
    "type": "posts"
})
```

#### 1.4 Google Photos Community Connector (Apify)
- Use the **Apify Website Content Crawler** actor to scrape `support.google.com/photos/community`
- Filter threads containing keywords: "search", "find photos", "missing photos", "can't find"
- Target: **500–700 threads**

```python
# ingestion/community.py
from apify_client import ApifyClient

client = ApifyClient(token=APIFY_API_TOKEN)
run = client.actor("apify/website-content-crawler").call(run_input={
    "startUrls": [{"url": "https://support.google.com/photos/community"}],
    "maxCrawlPages": 300,
    "pageFilter": "search|find photos|missing photos"
})
```

#### 1.5 Deduplication
- Generate SimHash fingerprint for each document's text
- Flag duplicates with Hamming distance < 3 as near-duplicates
- Keep the version with highest metadata richness (upvotes, rating, date)

#### 1.6 Storage
- Insert validated documents into PostgreSQL `raw_documents` table
- Archive original JSON responses to S3/GCS

### Deliverables
- 4 working `SourceConnector` classes (2 direct libraries + 2 via Apify)
- `Deduplicator` utility with unit tests
- `raw_documents` table populated with 4,000–5,000 records
- Ingestion run logged with per-source breakdown stats

### Success Criteria
| Metric | Target |
|---|---|
| Total documents ingested | 4,000–5,000 |
| Play Store coverage | 1,500–2,000 |
| App Store coverage | 1,000–1,500 |
| Reddit coverage (via Apify) | 800–1,000 |
| Community coverage (via Apify) | 500–700 |
| Deduplication rate | < 15% duplicates remaining |
| Schema validation pass rate | 100% |

---

## Phase 2 — Preprocessing & Embedding

### Duration
Week 3–4 (Days 11–20)

### Goals
- Filter out noise and off-topic content
- Generate vector embeddings for semantic operations downstream
- Produce a clean, relevance-filtered corpus

### Tasks

#### 2.1 Language Detection & Filtering
- Use `langdetect` or `fastText` language ID model
- v1 scope: retain only `en` documents
- Log volume of filtered-out non-English docs for future roadmap

#### 2.2 Noise Filtering
Rule-based filters first, then classifier:

```
Discard if:
  - len(text) < 20 characters
  - text is only emojis or punctuation
  - text matches spam patterns (promo codes, links only)
  - rating == 5 with no mention of search/find/retrieve (for reviews)
```

#### 2.3 Relevance Classifier
- Build a binary LLM-based classifier:
  - **Prompt:** *"Does this text describe a problem or experience related to finding, searching for, or retrieving a photo in Google Photos? Answer yes or no."*
  - Use **Groq** (`llama-3.1-8b-instant`) for fast, cost-efficient classification at this volume
  - Cache results to avoid re-classification
- Target: retain ~35–40% of corpus (**≥ 1,500 relevant documents**)

#### 2.4 Text Normalization
- Lowercase, strip HTML tags, fix encoding artifacts (`â€™` → `'`)
- Preserve original text separately for display in evidence explorer

#### 2.5 Chunking
- Split long Reddit threads / community posts into paragraph-level chunks
- Max chunk size: 512 tokens
- Maintain parent document reference in each chunk

#### 2.6 Embedding Generation
- Model: `sentence-transformers/all-MiniLM-L6-v2` (local, free) for v1; upgrade to `text-embedding-3-small` (OpenAI) if needed
- Batch process in groups of 64
- Store embeddings in **pgvector** (PostgreSQL extension) alongside document ID

### Deliverables
- `preprocessor.py` with all filter and chunking logic
- `embedder.py` with batched embedding generation
- `processed_documents` table with `is_relevant` flag and chunk references
- Vector store populated with **≥ 1,500 embeddings**
- Cost tracking log (API spend)

### Success Criteria
| Metric | Target |
|---|---|
| Relevant documents after filtering | ≥ 1,500 |
| Embedding generation success rate | ≥ 99% |
| Avg. processing time per document | < 300ms |
| False negative rate (relevant docs discarded) | < 5% (spot-checked manually) |

---

## Phase 3 — AI Analysis Layer

### Duration
Week 4–6 (Days 16–35)

### Goals
- Tag every relevant document with structured labels across 4 dimensions
- All outputs must be structured JSON with confidence scores
- Prompts must be versioned and reproducible

### Tasks

#### 3.1 Prompt Engineering Framework
- Store all prompts in `prompts/` as `.txt` files with version headers
- Use a `PromptRunner` class that:
  - Loads prompt template
  - Injects document text
  - Calls LLM with `response_format={"type": "json_object"}`
  - Validates output against a Pydantic model
  - Retries on malformed responses (max 3 attempts)

#### 3.2 Analyzer A — Retrieval Pattern Extractor
**What type of memory/photo is the user trying to retrieve?**

```
Output Schema:
{
  "retrieval_type": ["event_based", "person_based", "location_based",
                     "object_based", "time_based", "emotion_based", "unknown"],
  "description": "one-line explanation",
  "confidence": 0.0–1.0
}
```

**Few-shot examples to include in prompt:**
- "photo of my mom's birthday last year" → `event_based`, `person_based`, `time_based`
- "picture of the medicine I took" → `object_based`

#### 3.3 Analyzer B — Memory Cue Classifier
**What does the user remember vs. forget?**

```
Output Schema:
{
  "remembered": {
    "time": "last summer",
    "location": "Goa",
    "people": null,
    "object": null,
    "emotion": "happy"
  },
  "forgotten": ["exact date", "album name", "person's name"],
  "confidence": 0.0–1.0
}
```

#### 3.4 Analyzer C — Failure Mode Tagger
**Where does the retrieval experience break down?**

```
Taxonomy:
- search_vocabulary_mismatch
- temporal_ambiguity
- location_imprecision
- no_album_structure
- visual_only_memory
- search_ux_breakdown
- wrong_confidence_signal
- unknown

Output Schema:
{
  "failure_modes": ["temporal_ambiguity", "search_vocabulary_mismatch"],
  "primary_mode": "temporal_ambiguity",
  "evidence_quote": "I remembered it was around Christmas but couldn't find it",
  "confidence": 0.0–1.0
}
```

#### 3.5 Analyzer D — Search Behavior Analyzer
**How does the user attempt to find the photo?**

```
Output Schema:
{
  "behaviors": ["approximate_date_browsing", "keyword_guessing",
                "album_scanning", "asked_someone_else",
                "gave_up", "used_third_party_tool"],
  "outcome": "failed | partial | succeeded",
  "quote": "I tried scrolling through two months of photos",
  "confidence": 0.0–1.0
}
```

#### 3.6 Batch Processing Pipeline
- Process all **~1,500 relevant documents** through all 4 analyzers
- Use **Groq** (`llama-3.3-70b-versatile`) for all structured JSON tagging — fast inference, generous free tier
- Parallelise with `asyncio` + Groq rate limiting (RPM-aware)
- Store tagged outputs in `tagged_documents` table
- Track token usage per analyzer run

```python
# analysis/prompt_runner.py
from groq import Groq

client = Groq(api_key=GROQ_API_KEY)
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"},
    temperature=0.1
)
```

#### 3.7 Quality Assurance
- Spot-check 100 randomly sampled tagged documents manually
- Compute inter-rater agreement (human vs. LLM) on sample
- Iterate prompt if accuracy < 80% on any dimension

### Deliverables
- 4 versioned analyzer prompt files
- `PromptRunner` class with validation and retry logic
- `tagged_documents` table fully populated
- QA report with accuracy estimates per analyzer

### Success Criteria
| Analyzer | Target Accuracy (spot-check) |
|---|---|
| Retrieval Pattern | ≥ 85% |
| Memory Cue | ≥ 80% |
| Failure Mode | ≥ 82% |
| Search Behavior | ≥ 80% |
| Overall tagging completion | ≥ 98% of relevant docs |

---

## Phase 4 — Synthesis & Clustering

### Duration
Week 6–7 (Days 36–42)

### Goals
- Group semantically related pain points into coherent clusters
- Score each cluster as a product opportunity
- Link every cluster to verbatim user evidence

### Tasks

#### 4.1 Dimensionality Reduction
- Apply UMAP to all document embeddings (reduce to 10D for clustering, 2D for visualization)
- Parameters: `n_neighbors=15`, `min_dist=0.1`, `metric='cosine'`

#### 4.2 Clustering
- Apply HDBSCAN on 10D UMAP representation
- Parameters: `min_cluster_size=30`, `min_samples=10`
- Output: cluster label per document (`-1` = noise/outlier)
- Expected: 15–40 meaningful clusters

#### 4.3 Cluster Labeling
For each cluster, select top 20 representative documents (highest cosine similarity to centroid) and run:

```
Prompt: "Here are 20 user reviews/posts all describing the same retrieval problem.
Write a concise 1-sentence cluster label and a 2-sentence summary of
the core pain point. Return JSON: {label, summary, primary_failure_mode,
primary_retrieval_type}"
```

#### 4.4 Opportunity Scoring

For each cluster, compute:

| Score Component | Calculation | Weight |
|---|---|---|
| Volume Score | (cluster size / total docs) × 100 | 40% |
| Severity Score | % of docs in cluster with rating ≤ 2 (or negative sentiment) | 40% |
| Novelty Score | 1 − (overlap with existing Google Photos features) | 20% |

**Final Formula:**
```
Opportunity Score = (Volume × 0.4) + (Severity × 0.4) + (Novelty × 0.2)
```

Novelty is assessed by querying a knowledge base of current Google Photos features (manually curated list) and checking if the cluster's failure mode is already addressed.

#### 4.5 Evidence Linking
For each cluster:
- Select top 5 most representative verbatim quotes
- Prioritize quotes that contain: clear pain description + specific memory details + outcome
- Store as `cluster_evidence` table: `{cluster_id, doc_id, quote, source, rating, date}`

#### 4.6 Cross-Cluster Comparison
- Generate a comparison matrix: cluster × failure_mode heatmap
- Identify co-occurring failure modes (e.g., temporal_ambiguity + search_vocabulary_mismatch)

### Deliverables
- `clusters` table with labels, summaries, scores, and top-N evidence
- 2D UMAP scatter plot (interactive, color-coded by cluster)
- Opportunity ranking table (top 10 clusters by score)
- Cross-cluster failure mode heatmap

### Success Criteria
| Metric | Target |
|---|---|
| Number of meaningful clusters | 15–40 |
| Noise/outlier rate | < 20% |
| Manual coherence check (top 5 clusters) | Reviewers agree ≥ 80% |
| Top cluster has clear, actionable label | Yes |

---

## Phase 5 — Output & Delivery

### Duration
Week 7–8 (Days 43–56)

### Goals
- Deliver PM-consumable artifacts: dashboard, insight reports, evidence explorer
- All outputs must be self-explanatory without engineering context

### Tasks

#### 5.1 PM Insight Dashboard (Streamlit)

**Page 1: Opportunity Leaderboard**
- Ranked table: Cluster Label | Score | Volume | Severity | Top Quote
- Click row → drills into Cluster Detail page
- Filters: Source, Date Range, Failure Mode, Rating

**Page 2: Cluster Detail**
- Cluster label + summary
- Failure mode breakdown (pie chart)
- Memory cue profile: what users remember vs. forget (stacked bar)
- Top 5 verbatim quotes with source, rating, date
- Similar clusters (cosine similarity)

**Page 3: Evidence Explorer**
- Semantic search across all tagged documents
- Filters: retrieval_type, failure_mode, behavior, source, rating
- Returns: relevant docs with tags + original text

**Page 4: Discovery Map**
- Interactive 2D UMAP scatter plot
- Hover: cluster label + top quote
- Color: by failure mode or by source

#### 5.2 Structured Insight Reports (Markdown/PDF)
Auto-generate one report per top-10 cluster:

```markdown
# Insight Report: [Cluster Label]

## Opportunity Score: [X/100]

## The Problem in One Line
[cluster summary]

## Who Is Affected
[volume stats, source breakdown]

## What Users Remember
[memory cue profile]

## Where It Breaks Down
[primary + secondary failure modes]

## What Users Try (and Fail)
[search behaviors + outcomes]

## Evidence (Top 5 Quotes)
1. ⭐⭐ (Play Store, Jan 2024): "..."
2. Reddit (r/googlephotos, 847 upvotes): "..."
...

## Opportunity Statement
"[X]% of analyzed users struggle with [failure mode] when trying to retrieve
[retrieval type] photos. Current Google Photos search does not address [gap].
An improvement here could directly impact retrieval success rate."
```

#### 5.3 PM Briefing Deck Outline
Produce a skeleton deck outline (not slides) that the PM can use to present findings:
- Slide 1: Methodology overview
- Slide 2: Scale (corpus size, sources)
- Slide 3: Top 5 opportunity clusters (ranked)
- Slide 4: Deep dive — #1 opportunity
- Slide 5: Cross-cutting patterns
- Slide 6: Recommended next step

### Deliverables
- Running Streamlit dashboard (local or deployed)
- 10 auto-generated insight reports (Markdown + PDF)
- PM briefing deck outline
- README with instructions to run the dashboard

### Success Criteria
- Dashboard loads in < 3 seconds for all pages
- PM can navigate from leaderboard to evidence in ≤ 2 clicks
- Insight reports reviewed and approved by PM as "decision-ready"

---

## Phase 6 — Iteration & Hardening

### Duration
Week 9–10 (Days 57–70)

### Goals
- Incorporate PM feedback on insight quality
- Harden the pipeline for reliability and reusability
- Document the system for future contributors

### Tasks

#### 6.1 PM Feedback Loop
- PM reviews top 10 cluster reports and rates: Useful / Partially Useful / Not Useful
- For "Not Useful" clusters: diagnose — bad labeling, bad clustering, or genuinely low signal?
- Adjust prompt, clustering parameters, or scoring weights accordingly

#### 6.2 Prompt Refinement
- Update prompts for any analyzer with spot-check accuracy < 85%
- Re-run affected documents through updated analyzers
- Re-cluster if > 20% of documents were re-tagged

#### 6.3 Pipeline Automation
- Wrap ingestion → preprocessing → analysis → synthesis into an Airflow/Prefect DAG
- Add alerting on: ingestion failure, embedding cost spike, cluster count anomaly
- Schedule weekly incremental ingestion (new reviews only)

#### 6.4 Testing & Reliability
- [ ] Unit tests for all schema validators and parsers
- [ ] Integration test: run mini end-to-end pipeline on 100 sample docs
- [ ] Regression test: re-run top-10 cluster labels against golden set

#### 6.5 Documentation
- [ ] `README.md` — system overview and quickstart
- [ ] `PROMPTS.md` — all prompt templates with version history and rationale
- [ ] `DATA_DICTIONARY.md` — all table schemas and field definitions
- [ ] `RUNBOOK.md` — how to re-run ingestion, re-embed, re-cluster

### Deliverables
- Refined prompts (v2) with updated accuracy estimates
- Automated Airflow/Prefect DAG for weekly incremental runs
- Full test suite passing
- Complete documentation set

### Success Criteria
- End-to-end pipeline reproducible by a new engineer in < 1 day
- PM rates ≥ 80% of insight reports as "Useful" or "Partially Useful"
- Weekly incremental run completes in < 2 hours

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| API rate limits blocking ingestion | Medium | High | Exponential backoff + multi-key rotation |
| LLM tagging cost overrun | **Low** | Medium | Groq free tier handles full corpus; fallback to `llama-3.1-8b-instant` if rate-limited |
| Low relevance rate (< 10% relevant docs) | Low | High | Broaden relevance classifier; add more search queries for Reddit |
| Clusters too generic (e.g., "users want better search") | Medium | High | Increase min_cluster_size; use sub-clustering on large generic clusters |
| Play Store / App Store scraping blocked | Medium | High | Fallback to SerpAPI or manual export |
| PM finds output not actionable | Low | High | Early preview at Phase 4 milestone for course correction |

---

## Cost Estimate (v1)

| Item | Tool | Estimate |
|---|---|---|
| Ingestion — Reddit (Apify) | Apify Reddit Scraper | ~$2–5 (compute units) |
| Ingestion — Community (Apify) | Apify Website Content Crawler | ~$1–3 (compute units) |
| Play Store + App Store scraping | `google-play-scraper` + `app-store-scraper` | **Free** (libraries) |
| Relevance classification (4K–5K docs) | Groq `llama-3.1-8b-instant` | **~$0** (free tier) |
| Embedding (1,500 docs) | `all-MiniLM-L6-v2` (local) | **Free** |
| LLM tagging (1,500 × 4 analyzers) | Groq `llama-3.3-70b-versatile` | **~$0–2** (free tier covers this) |
| Cluster labeling (15–20 clusters) | Groq `llama-3.3-70b-versatile` | **~$0** |
| Insight report generation (10 reports) | Groq `llama-3.3-70b-versatile` | **~$0** |
| **Total** | | **~$3–10** (mostly Apify actors) |

> **Groq free tier** (as of 2024): 14,400 req/day on `llama-3.3-70b-versatile` and 7,000 req/day on `llama-3.1-8b-instant` — more than sufficient for a corpus of 1,500 documents.

---

## Milestones & Review Gates

| Milestone | End of | Review |
|---|---|---|
| M0: Infra + Schema ready | Week 1 | Internal |
| M1: 4K–5K docs ingested | Week 3 | PM preview: source breakdown stats |
| M2: ≥ 1,500 clean, embedded docs ready | Week 4 | Internal |
| M3: All 1,500 docs tagged via Groq | Week 6 | PM preview: sample tagged docs for feedback |
| M4: Clusters + scores ready | Week 7 | **PM Gate: approve top-10 cluster list** |
| M5: Dashboard + reports delivered | Week 8 | **PM Gate: sign off on output quality** |
| M6: Pipeline hardened + documented | Week 10 | Engineering review |
