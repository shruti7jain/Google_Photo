# Operational Runbook: AI Discovery Engine

> **Step-by-step operating and troubleshooting guide for engineers & PMs.**

---

## 1. Quick Start & Prerequisites

### Prerequisites:
- Python 3.11+ (Python 3.13 supported)
- PostgreSQL 15+ running locally or in Docker
- Groq API Key ([console.groq.com](https://console.groq.com))

### Environment Configuration:
Verify `.env` has:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/discovery_engine
GROQ_API_KEY=gsk_...
```

---

## 2. Launching the PM Interactive Dashboard

Run the FastAPI dashboard with auto-reload:
```powershell
cd "c:\Users\shrut\OneDrive\Documents\Google Photo\discovery-engine"
.\.venv\Scripts\uvicorn.exe dashboard.api:app --reload --port 8000
```
Open **`http://localhost:8000`** in your browser.

---

## 3. Running Master Pipeline Commands

The master runner [`pipeline_runner.py`](file:///c:/Users/shrut/OneDrive/Documents/Google%20Photo/discovery-engine/pipeline_runner.py) allows running the entire pipeline or individual phases on-demand:

### Check Pipeline Health & Record Counts:
```powershell
.\.venv\Scripts\python.exe pipeline_runner.py --status
```

### Run a Specific Phase:
- **Phase 1 (Data Ingestion):**
  ```powershell
  .\.venv\Scripts\python.exe pipeline_runner.py --phase 1
  ```
- **Phase 2 (Preprocessing & Embedding):**
  ```powershell
  .\.venv\Scripts\python.exe pipeline_runner.py --phase 2
  ```
- **Phase 3 (AI Analysis Layer — LLM Tagging):**
  ```powershell
  .\.venv\Scripts\python.exe pipeline_runner.py --phase 3 --limit 100
  ```
- **Phase 4 (Synthesis & Clustering):**
  ```powershell
  .\.venv\Scripts\python.exe pipeline_runner.py --phase 4
  ```
- **Phase 5 (Generate Top 10 Insight Reports):**
  ```powershell
  .\.venv\Scripts\python.exe pipeline_runner.py --phase 5
  ```

---

## 4. Running Verification Tests

Run the full pytest suite to verify all schema validators and preprocessing utilities:
```powershell
.\.venv\Scripts\pytest.exe -v
```
All 40 unit and integration tests must pass with 100% success.

---

## 5. Troubleshooting & FAQ

### Issue: Groq 429 Rate Limit (Tokens per Minute exceeded)
- **Cause:** Groq free-tier on-demand has an 8,000 TPM limit.
- **Resolution:** [`analysis/prompt_runner.py`](file:///c:/Users/shrut/OneDrive/Documents/Google%20Photo/discovery-engine/analysis/prompt_runner.py) automatically backs off and retries up to 3 times with exponential backoff. For bulk processing, keep `--batch-size 10` and use `--limit <N>`.

### Issue: Deprecated Groq Models (Error 400 `model_decommissioned`)
- **Active Chat Model:** `openai/gpt-oss-20b` (fast, efficient, generous token limits).
- **Active High-Capacity Model:** `openai/gpt-oss-120b` (used for cluster synthesis).
- Configured in [`config.yaml`](file:///c:/Users/shrut/OneDrive/Documents/Google%20Photo/discovery-engine/config.yaml) and [`dashboard/api.py`](file:///c:/Users/shrut/OneDrive/Documents/Google%20Photo/discovery-engine/dashboard/api.py).
