# Discovery Engine — Google Photos Photo Retrieval

AI-powered pipeline to analyze user feedback at scale and surface high-signal retrieval pain points for the Google Photos Core Experience team.

## Project Structure

```
discovery-engine/
├── ingestion/          # Source connectors (Play Store, App Store, Reddit via Apify, Community via Apify)
├── preprocessing/      # Language detection, noise filtering, relevance classification, chunking, embedding
├── analysis/           # LLM-based analyzers (Groq): Retrieval Pattern, Memory Cue, Failure Mode, Search Behavior
├── synthesis/          # UMAP + HDBSCAN clustering, opportunity scoring, evidence linking
├── output/             # Streamlit dashboard, insight report generator
├── models/             # Shared Pydantic schemas (common data contract)
├── prompts/            # Versioned LLM prompt templates
├── data/
│   ├── raw/            # Ingested documents (not committed to Git)
│   └── processed/      # Embedded + tagged documents (not committed to Git)
├── notebooks/          # Exploratory analysis notebooks
├── tests/              # Unit + integration tests
├── config.yaml         # Source configs, model choices, thresholds
├── .env.example        # API key template (copy to .env and fill in)
└── requirements.txt    # Python dependencies
```

## Quickstart

### 1. Clone and set up environment

```bash
git clone <repo-url>
cd discovery-engine
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and fill in your keys
```

### 3. Validate setup

```bash
python -m pytest tests/test_schema.py -v
python scripts/validate_env.py
```

### 4. Run ingestion (Phase 1)

```bash
python -m ingestion.run_all
```

## API Keys Required

| Key | Used For | Where to get |
|---|---|---|
| `GROQ_API_KEY` | LLM inference (relevance, tagging, labeling) | [console.groq.com](https://console.groq.com) |
| `APIFY_API_TOKEN` | Reddit + Community scraping | [console.apify.com](https://console.apify.com) |
| `DATABASE_URL` | PostgreSQL connection string | Local or cloud Postgres |

## Pipeline Phases

| Phase | Command | Description |
|---|---|---|
| 1 — Ingest | `python -m ingestion.run_all` | Scrape all sources |
| 2 — Preprocess | `python -m preprocessing.run` | Filter, chunk, embed |
| 3 — Analyze | `python -m analysis.run` | Tag all docs via Groq |
| 4 — Synthesize | `python -m synthesis.run` | Cluster + score opportunities |
| 5 — Output | `streamlit run output/dashboard.py` | Launch PM dashboard |

## Configuration

All thresholds, model names, and source targets are in [`config.yaml`](config.yaml). Do not hardcode values in source files.
