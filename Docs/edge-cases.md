# Edge Cases: AI-Powered Photo Retrieval Discovery Engine

> **Scope:** All corner scenarios, failure modes, and unexpected inputs that could degrade pipeline quality, produce misleading insights, or cause system failures.
> Organized by pipeline layer, then by severity: 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low

---

## Layer 1 — Data Ingestion

### 1.1 Google Play Store Connector

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| P1 | Scraper returns HTML error page instead of JSON | 🔴 | `google-play-scraper` silently returns partial results on rate-limit | Validate response schema; check `count == expected`; retry with backoff |
| P2 | Duplicate reviews across multiple scrape runs | 🟠 | Same review fetched in "newest" and "most relevant" sort passes | Hash `(source, author_id, date, text[:50])` as idempotency key before insert |
| P3 | Review text is only a star rating with no text | 🟡 | e.g., ★★★★★ with empty body — useless for NLP | Filter out docs where `len(text.strip()) < 20` in noise filter |
| P4 | App version mismatch (very old reviews) | 🟡 | Reviews from 2018 may describe a fundamentally different product | Add `min_date` filter in config (e.g., ignore reviews before 2022) |
| P5 | Non-English reviews slipping through | 🟡 | Some EN-tagged reviews contain mixed Hindi/Spanish | Enforce `langdetect` check even on Play Store EN results |
| P6 | Play Store geo-blocks scraper IP | 🟠 | Scraper returns empty results without an explicit error | Assert `len(results) > 0`; alert and fallback to SerpAPI |

---

### 1.2 Apple App Store Connector

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| A1 | `app-store-scraper` returns 0 results for a storefront | 🟠 | Apple silently drops the feed for low-volume storefronts | Fallback to iTunes RSS feed; log and skip gracefully |
| A2 | Duplicate reviews across US and IN storefronts | 🟡 | Same user may review on multiple storefronts | Dedup on `(text_hash, date, rating)` cross-storefront |
| A3 | App Store feed returns HTML instead of JSON | 🔴 | Apple can return maintenance pages mid-scrape | Validate `Content-Type: application/json`; fail fast with alert |

---

### 1.3 Reddit Connector (Apify)

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| R1 | Apify actor run fails silently (status: SUCCEEDED but empty dataset) | 🔴 | Actor completes but returns 0 items due to Reddit API changes | Assert dataset item count > 0 after every actor run |
| R2 | Apify account compute unit exhaustion mid-run | 🔴 | Run aborts at 60% completion | Checkpoint partial results; resume from last saved item |
| R3 | Reddit post is a link post with no text body | 🟠 | `selftext` is empty; only title is available | Use title + top comments; flag as `low_text_density` |
| R4 | Comment thread is deleted by moderator between crawl and parse | 🟡 | Apify returns `[deleted]` or `[removed]` as text | Discard docs where `text in ("[deleted]", "[removed]", "")` |
| R5 | Highly upvoted off-topic post dominates corpus | 🟠 | A viral rant about Google storage pricing floods the dataset | Relevance classifier must handle this; also enforce subreddit allowlist |
| R6 | Sarcastic or meme posts | 🟡 | "Oh wow Google Photos found my photo, only took 3 years 😂" — LLM may mis-tag as positive | Add sarcasm-awareness note to prompts; flag low-confidence tags for review |
| R7 | Nested comment threads include off-topic replies | 🟡 | Only the parent post is about photo retrieval; replies drift | Ingest only depth-1 comments (direct replies to OP); cap depth |

---

### 1.4 Google Photos Community Connector (Apify)

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| C1 | Google support page restructures URL schema | 🔴 | Apify crawler follows old URLs and gets 404s | Use `startUrls` with the community search endpoint; monitor crawl success rate |
| C2 | Crawler hits a CAPTCHA or bot-detection wall | 🔴 | Apify returns empty or partial results | Use Apify's built-in stealth mode; add delays between requests |
| C3 | Thread contains a "solved" tag but no resolution details | 🟡 | Thread shows pain point exists but gives no behavioral signal | Ingest anyway; tag `outcome=resolved_unknown` |
| C4 | Staff/bot responses dominate thread | 🟠 | Google staff templates bloat corpus with non-user language | Filter out posts where `author_type == "google_staff"` or known bot usernames |
| C5 | Same issue cross-posted across Reddit and Community | 🟡 | Inflates the signal for one specific issue | Cross-source deduplication on text similarity (MinHash) |

---

### 1.5 General Ingestion

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| G1 | Schema validation fails for a batch of documents | 🔴 | Missing required fields crash the insert | Wrap each insert in try/except; log and quarantine invalid docs to `failed_documents` table |
| G2 | Text field contains only a URL or image embed | 🟡 | User posts a screenshot with no text context | Discard if `len(text) < 20` after stripping URLs |
| G3 | Date field is missing or epoch zero (1970-01-01) | 🟡 | Corrupt date from scraper | Set `date = null`; exclude from time-based analysis; do not discard |
| G4 | Extremely long document (> 5,000 tokens) | 🟠 | Long Reddit threads or community mega-threads | Hard-cap at 5,000 tokens during chunking; log truncation |
| G5 | All sources return below minimum target volume | 🔴 | Corpus too small for meaningful clustering | Expand search queries; add subreddits; lower `min_date` cutoff |

---

## Layer 2 — Preprocessing & Embedding

### 2.1 Language Detection

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| L1 | `langdetect` incorrectly classifies short English text as another language | 🟠 | "Can't find photo" → misidentified as Dutch | Use `langdetect` with confidence threshold ≥ 0.9; if uncertain, keep the doc |
| L2 | Code-switched text (Hinglish, Spanglish) | 🟡 | "Yaar mera photo nahi mil raha Google Photos pe" — mixed Hindi/English | Flag as `language=mixed`; exclude from v1 but archive for future multilingual scope |
| L3 | Emoji-only or symbol-heavy text passes language detection | 🟡 | "📷❌🔍😭" passes as "unknown" language | Add character ratio check: discard if `alpha_ratio < 0.5` |

---

### 2.2 Relevance Classification

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| RC1 | Feature request misclassified as retrieval problem | 🟠 | "Google Photos should have better search" — is this a retrieval pain or a feature vote? | Refine prompt: "Does the user describe a *specific instance* of failing to find a photo?" |
| RC2 | Positive testimonial misclassified as pain point | 🟠 | "I searched and found my old photo easily!" — Groq may flag as retrieval-related | Add instruction: "Exclude success stories; only include failure or struggle reports" |
| RC3 | Groq rate limit hit during relevance classification | 🔴 | `429 Too Many Requests` mid-batch stops pipeline | Implement token-bucket rate limiter; cache results; resume from checkpoint |
| RC4 | Groq returns non-JSON despite system prompt | 🟠 | LLM outputs prose instead of `{"relevant": true}` | Wrap in regex fallback parser; if parse fails, default to `uncertain` and manual review |
| RC5 | Relevance rate drops below 20% | 🔴 | Corpus contains too many off-topic reviews | Trigger alert; PM reviews sample; broaden search queries and re-ingest |
| RC6 | All reviews from one source classified as irrelevant | 🟠 | e.g., App Store reviews skew toward billing/storage, not retrieval | Log per-source relevance rate; alert if any source < 10% relevant |

---

### 2.3 Chunking

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| CH1 | Chunking splits a sentence mid-thought | 🟡 | "I searched for my vacation photo but..." → split at token boundary | Use sentence-aware splitter (`nltk.sent_tokenize`); never split mid-sentence |
| CH2 | Single chunk exceeds LLM context window | 🟠 | Very verbose review > 1,024 tokens | Hard-cap at 512 tokens; truncate with `[TRUNCATED]` marker; log |
| CH3 | Parent document reference lost after chunking | 🔴 | Chunk can't be traced back to source URL or rating | Always propagate `doc_id`, `source`, `url`, `rating`, `date` to every chunk |

---

### 2.4 Embedding

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| E1 | All-MiniLM model produces near-identical embeddings for semantically different short texts | 🟡 | Short reviews cluster incorrectly due to model limitations | Upgrade to `text-embedding-3-small` for docs with < 30 tokens |
| E2 | Embedding model returns NaN or zero vector | 🔴 | Silent failure causes downstream clustering to break | Validate: `assert not np.isnan(emb).any() and np.linalg.norm(emb) > 0` |
| E3 | Embedding store (pgvector) runs out of disk space | 🔴 | Insert fails silently or crashes | Set up disk usage alert at 80% capacity; pre-calculate storage needed |

---

## Layer 3 — AI Analysis (Groq / LLM Tagging)

### 3.1 Groq API

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| GA1 | Groq free tier daily limit exhausted | 🔴 | 14,400 req/day limit hit mid-batch processing | Schedule batch jobs across days; checkpoint progress; use `llama-3.1-8b-instant` as fallback |
| GA2 | Groq returns HTTP 503 (service unavailable) | 🔴 | Groq infrastructure outage | Retry with exponential backoff (1s, 2s, 4s, max 3 attempts); log failures |
| GA3 | JSON output schema not respected by LLM | 🔴 | LLM returns extra fields, missing fields, or wrong types | Pydantic validation on every output; partial fallback: use valid fields, flag missing ones |
| GA4 | LLM "hallucinates" a quote that doesn't appear in the input text | 🟠 | `evidence_quote` field contains invented text | Post-validate: check quoted string is a substring of original document |
| GA5 | Context window overflow for long documents | 🟡 | Prompt + document > 8K tokens (llama-3.3-70b limit) | Pre-truncate document in PromptRunner if `len(prompt + doc) > 7500 tokens` |

---

### 3.2 Retrieval Pattern Extractor

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| RP1 | Multiple retrieval types apply equally | 🟡 | "Photo of my sister at our Goa trip" → event + person + location all valid | Allow `retrieval_type` to be an array; require at least one; no forced single label |
| RP2 | Retrieval type is `unknown` for > 30% of corpus | 🟠 | Model can't categorize; taxonomy may be too narrow | Analyze `unknown` docs manually; add new types to taxonomy |
| RP3 | User describes wanting to retrieve a video, not a photo | 🟡 | "I can't find the video of my kid's first steps" — project scope is photos | Tag `media_type=video`; include in analysis but flag separately |

---

### 3.3 Memory Cue Classifier

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| MC1 | User remembers nothing specific — vague complaint | 🟠 | "I can never find my photos" — no extractable memory cues | Set all remembered/forgotten fields to `null`; tag `vagueness=high`; still useful as volume signal |
| MC2 | User remembers contradictory details | 🟡 | "I think it was summer 2021... or maybe 2022?" | Capture both with `uncertainty=true` flag; do not discard |
| MC3 | Memory cue is a person's name (PII concern) | 🟠 | "photo with John Smith" — stores real names | Anonymize names before storage: replace with `[PERSON]` using NER; never store raw PII |

---

### 3.4 Failure Mode Tagger

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| FM1 | Multiple failure modes co-occur | 🟡 | "I knew it was from last Christmas (temporal) and I typed 'Christmas dinner' but nothing came up (vocabulary)" | Allow `failure_modes` array; flag `primary_mode` explicitly |
| FM2 | Failure mode is "Google Photos deleted my photo" — not a retrieval issue | 🟠 | Different problem (data loss) contaminating retrieval clusters | Add `failure_mode=data_loss`; exclude from retrieval opportunity scoring; route to separate analysis |
| FM3 | User blames themselves ("I'm bad at organizing") — no product failure | 🟢 | Low signal for product improvement | Tag `locus_of_control=user`; deprioritize in scoring but retain as behavioral data |

---

### 3.5 Search Behavior Analyzer

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| SB1 | User describes behavior of another person ("my mom can't find...") | 🟡 | Third-person account may introduce inaccuracies | Tag `perspective=third_person`; treat as weaker evidence |
| SB2 | User mentions using a workaround (Google Drive, iCloud, etc.) | 🟡 | Signals frustration but also competitive churn risk | Tag `workaround_used=true` + tool name; valuable signal for PM |
| SB3 | Behavior is ambiguous — could be browsing or searching | 🟡 | "I went through my photos" — scrolling or using search? | If ambiguous, tag `behaviors=["unknown_browsing"]` and `confidence < 0.6` |

---

## Layer 4 — Synthesis & Clustering

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| CL1 | HDBSCAN produces only 1–2 mega-clusters | 🔴 | All docs collapse into "search is broken" — too generic | Increase `min_cluster_size`; apply sub-clustering (recursive HDBSCAN) on large clusters |
| CL2 | HDBSCAN assigns > 40% of docs to noise (`label = -1`) | 🔴 | Too much data excluded from insights | Lower `min_cluster_size`; try UMAP with different `n_neighbors`; consider k-means fallback |
| CL3 | Two clusters are semantically identical (near-duplicate clusters) | 🟠 | "Can't find old photos" and "Old photos missing from search" clustered separately | Post-merge clusters with centroid cosine similarity > 0.92 |
| CL4 | Cluster labeled by LLM with a vague or misleading name | 🟠 | LLM outputs "Users want better search" for a specific pain point | Run labeling prompt twice; pick highest-specificity output; flag for PM review |
| CL5 | One data source dominates all clusters | 🟠 | 80% of each cluster's docs are from Play Store | Weight cluster evidence to ensure source diversity; surface source breakdown per cluster |
| CL6 | Cluster score ties between two opportunity areas | 🟢 | Ambiguous prioritization for PM | Add a tiebreaker: prefer cluster with higher source diversity |
| CL7 | UMAP runs out of RAM on 1,500 embeddings | 🟢 | Unlikely at this scale but possible on low-memory machines | Set `low_memory=True` in UMAP; process in batches if needed |
| CL8 | Opportunity Novelty score is miscalibrated | 🟠 | A feature Google Photos already has scores high on "novelty" | Maintain a curated, up-to-date `known_features.json`; validate before each scoring run |

---

## Layer 5 — Output & Delivery

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| O1 | Insight report references a quote that violates PII rules | 🔴 | A verbatim quote contains a full name, email, or phone number | Run NER on all evidence quotes before report generation; mask PII with `[REDACTED]` |
| O2 | Streamlit dashboard crashes on empty cluster table | 🔴 | If clustering produces 0 valid clusters, dashboard throws unhandled exception | Add `if clusters.empty: show_empty_state_message()` guard on all pages |
| O3 | PM misinterprets opportunity score as absolute truth | 🟠 | Score is a heuristic, not a ground truth metric | Add a prominent disclaimer on dashboard: "Scores are relative signals, not absolute metrics" |
| O4 | Evidence Explorer returns results for a query with no matches | 🟢 | Semantic search returns 0 results | Show "No results found — try a broader query" with suggested example queries |
| O5 | Auto-generated report has repetitive or low-quality writing | 🟡 | LLM generates boilerplate for clusters with thin evidence | Set `min_evidence_count = 3` per cluster before generating a report; skip if below |
| O6 | PDF export fails due to missing LaTeX/pandoc dependency | 🟡 | PDF generation crashes silently | Fallback to Markdown export; log warning; add pandoc to setup checklist |

---

## Cross-Cutting / System-Level Edge Cases

| # | Edge Case | Severity | Description | Mitigation |
|---|---|---|---|---|
| SYS1 | Pipeline partially completes and leaves DB in inconsistent state | 🔴 | Crash mid-tagging leaves half the docs tagged | Use idempotent writes (`INSERT ... ON CONFLICT DO UPDATE`); track `processing_status` per doc |
| SYS2 | Re-running pipeline overwrites previously validated clusters | 🔴 | PM-approved clusters from last run get wiped | Version cluster runs with `run_id` and `run_date`; never overwrite, always append |
| SYS3 | Groq model version deprecated between runs | 🟠 | `llama-3.3-70b-versatile` replaced by a newer model name | Pin model version in `config.yaml`; alert when Groq deprecation notice is detected |
| SYS4 | `.env` file accidentally committed to Git | 🔴 | API keys exposed publicly | Add `.env` to `.gitignore` immediately; use `pre-commit` hook to block secrets |
| SYS5 | Clock skew causes date-based deduplication to fail | 🟡 | Timestamps from different sources in different timezones | Normalize all dates to UTC at ingestion time |
| SYS6 | Config file (`config.yaml`) has conflicting parameters | 🟡 | `min_cluster_size > total_relevant_docs` causes HDBSCAN to return empty | Add a `validate_config()` step at pipeline startup that checks parameter consistency |
| SYS7 | Pipeline runs on a weekend with Apify actor maintenance | 🟢 | Scheduled run silently skips ingestion | Set up alerting on zero-record ingestion runs |
| SYS8 | Corpus skewed by a viral Reddit thread or PR event | 🟠 | One thread with 1,000 comments dominates a cluster | Cap max contribution per source thread: `max_docs_per_thread = 20` |

---

## Edge Cases Specific to PM Interpretation

| # | Edge Case | Description | Guidance |
|---|---|---|---|
| PI1 | Correlation ≠ causation in cluster patterns | High volume of temporal ambiguity complaints may reflect *when* users search, not a product gap | Always pair with quantitative data (search abandonment rate) before drawing causal conclusions |
| PI2 | Recency bias in reviews | Recent reviews may spike after a product update (good or bad), distorting trend signals | Filter last 30 days separately from 6-month window; compare distributions |
| PI3 | Selection bias in who writes reviews | Users who write reviews skew frustrated or delighted — silent majority is underrepresented | Explicitly note in every report: "This corpus represents vocal users, not all users" |
| PI4 | Cluster overlap with known research | A discovered pain point may already be in an existing PM's PRD | Cross-reference top clusters against internal product roadmap before presenting as "new" discovery |

---

## Edge Case Severity Summary

| Severity | Count | Action Required |
|---|---|---|
| 🔴 Critical | 18 | Must be handled before production run; pipeline may break or produce wrong insights |
| 🟠 High | 19 | Should be handled in v1; degrades insight quality if ignored |
| 🟡 Medium | 16 | Handle in v1 or v2; manageable workarounds exist |
| 🟢 Low | 5 | Nice-to-have; log and revisit in Phase 6 |
