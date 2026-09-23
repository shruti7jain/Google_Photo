"""
scripts/validate_env.py
────────────────────────────────────────────────────────────────
Validates that all required environment variables are set and
all API credentials can reach their respective services.

Run after copying .env.example to .env:

    python scripts/validate_env.py

Exit code 0 = all checks passed.
Exit code 1 = one or more checks failed.
"""

import os
import sys

import httpx
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

REQUIRED_VARS = {
    "GROQ_API_KEY":     "Groq LLM inference",
    "APIFY_API_TOKEN":  "Apify Reddit + Community scraping",
    "DATABASE_URL":     "PostgreSQL connection",
}

OPTIONAL_VARS = {
    "SERP_API_KEY":  "SerpAPI (Play Store fallback)",
    "OPENAI_API_KEY": "OpenAI embeddings upgrade",
}

errors: list[str] = []


def check_env_vars() -> None:
    logger.info("── Checking required environment variables ──")
    for var, purpose in REQUIRED_VARS.items():
        value = os.getenv(var)
        if not value:
            logger.error(f"  ✗ {var} is missing  ({purpose})")
            errors.append(var)
        else:
            logger.success(f"  ✓ {var} is set")

    logger.info("── Checking optional environment variables ──")
    for var, purpose in OPTIONAL_VARS.items():
        value = os.getenv(var)
        if not value:
            logger.warning(f"  ⚠ {var} is not set  ({purpose}) — optional")
        else:
            logger.success(f"  ✓ {var} is set")


def check_groq() -> None:
    logger.info("── Testing Groq API connection ──")
    api_key = os.getenv("GROQ_API_KEY", "")
    try:
        # Use the models list endpoint — lightweight, no token consumption
        resp = httpx.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            models = [m["id"] for m in resp.json().get("data", [])]
            has_llama = any("llama" in m for m in models)
            logger.success(f"  ✓ Groq API reachable — {len(models)} models available")
            if has_llama:
                logger.success("  ✓ llama models confirmed available")
            else:
                logger.warning("  ⚠ llama models not found — check model names in config.yaml")
        elif resp.status_code == 401:
            logger.error("  ✗ Groq API key is invalid (401 Unauthorized)")
            errors.append("GROQ_API_KEY (invalid)")
        else:
            logger.warning(f"  ⚠ Groq returned unexpected status {resp.status_code}")
    except httpx.RequestError as e:
        logger.error(f"  ✗ Could not reach Groq API: {e}")
        errors.append("GROQ_API_KEY (network)")


def check_apify() -> None:
    logger.info("── Testing Apify API connection ──")
    token = os.getenv("APIFY_API_TOKEN", "")
    try:
        resp = httpx.get(
            "https://api.apify.com/v2/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            user = resp.json().get("data", {}).get("username", "unknown")
            logger.success(f"  ✓ Apify API reachable — logged in as '{user}'")
        elif resp.status_code == 401:
            logger.error("  ✗ Apify API token is invalid (401 Unauthorized)")
            errors.append("APIFY_API_TOKEN (invalid)")
        else:
            logger.warning(f"  ⚠ Apify returned unexpected status {resp.status_code}")
    except httpx.RequestError as e:
        logger.error(f"  ✗ Could not reach Apify API: {e}")
        errors.append("APIFY_API_TOKEN (network)")


def check_database() -> None:
    logger.info("── Testing PostgreSQL connection ──")
    db_url = os.getenv("DATABASE_URL", "")
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.success(f"  ✓ PostgreSQL reachable — {version[:40]}...")
    except Exception as e:
        logger.error(f"  ✗ PostgreSQL connection failed: {e}")
        errors.append("DATABASE_URL (connection failed)")


def main() -> None:
    logger.info("=" * 55)
    logger.info("  discovery-engine — Environment Validation")
    logger.info("=" * 55)

    check_env_vars()
    if "GROQ_API_KEY" not in errors:
        check_groq()
    if "APIFY_API_TOKEN" not in errors:
        check_apify()
    if "DATABASE_URL" not in errors:
        check_database()

    logger.info("=" * 55)
    if errors:
        logger.error(f"❌ Validation FAILED — {len(errors)} issue(s): {errors}")
        logger.info("Fix the above issues in your .env file and re-run.")
        sys.exit(1)
    else:
        logger.success("✅ All checks passed — environment is ready.")
        logger.info("Next step: python scripts/setup_db.py")
        sys.exit(0)


if __name__ == "__main__":
    main()
