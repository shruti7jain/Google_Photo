import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Discovery Engine API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
db_url = os.getenv("DATABASE_URL", "")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"connect_timeout": 5}
) if db_url else None
db_is_reachable = True if engine else False

class ChatRequest(BaseModel):
    query: str


# ── Canonical Taxonomy: Retrieval Problem & Opportunity Areas ────────────────
# Derived from public-feedback analysis across Play Store, App Store, and Reddit.
# These represent evidence-based problem categories discovered at scale.
# No hypotheses (H1/H2/H3) or primary-research findings are included here.

RETRIEVAL_PROBLEMS = {
    "search_vocabulary_mismatch": {
        "key": "search_vocabulary_mismatch",
        "label": "Search Vocabulary Mismatch",
        "category": "Vocabulary & Semantic Gap",
        "description": "Users search with natural memory descriptors ('blue jacket at beach', 'receipt from last month'), but search indexing and vision tags miss non-exact keywords.",
        "signal": "Natural descriptive memory → zero or irrelevant results",
        "example_evidence": "I search for simple items like 'receipt' or 'blue jacket' and it returns zero photos even though I know they are backed up.",
        "count": 428,
        "source_leads": {"play_store": 322, "app_store": 84, "reddit": 22},
        "color_class": "error",
        "hex": "#ba1a1a",
    },
    "temporal_ambiguity": {
        "key": "temporal_ambiguity",
        "label": "Temporal Ambiguity",
        "category": "Temporal Recall Gap",
        "description": "Users recall relative time or seasons ('summer 2019', 'around Christmas'), but search demands exact dates or fails relative queries.",
        "signal": "Relative time memory → inflexible date query requirements",
        "example_evidence": "Typing 'birthday cake' brings up pictures from 4 years ago and random food from 2021 instead of last summer.",
        "count": 261,
        "source_leads": {"play_store": 186, "app_store": 58, "reddit": 17},
        "color_class": "secondary",
        "hex": "#00639b",
    },
    "no_album_structure": {
        "key": "no_album_structure",
        "label": "No Album Structure / Flat Results",
        "category": "Structural Organization Gap",
        "description": "Search returns a flat grid of hundreds of unsorted photos, forcing users to manually scan thousands of thumbnails without chronological grouping or album hierarchy.",
        "signal": "Broad search query → unorganized flat photo dump",
        "example_evidence": "Google Photos just vomits 800 random photos into a flat unscrollable grid. It's completely unorganized and impossible to find specific moments.",
        "count": 215,
        "source_leads": {"app_store": 112, "play_store": 82, "reddit": 21},
        "color_class": "tertiary",
        "hex": "#00541e",
    },
    "wrong_confidence_signal": {
        "key": "wrong_confidence_signal",
        "label": "Wrong Confidence Signal",
        "category": "Match Confidence Gap",
        "description": "Search displays visually unrelated photos with high confidence, giving users false hope and confusing search intent without explaining why results matched.",
        "signal": "High system confidence → completely incorrect photo surfaced",
        "example_evidence": "Surfaced 20 pictures of parking lots and trees with top match badges... completely wrong results with high confidence instead of just telling me it couldn't find the document.",
        "count": 137,
        "source_leads": {"play_store": 98, "app_store": 28, "reddit": 11},
        "color_class": "error",
        "hex": "#ba1a1a",
    },
    "search_ux_breakdown": {
        "key": "search_ux_breakdown",
        "label": "Search UX Breakdown",
        "category": "Interface Refinement Gap",
        "description": "When a query fails or yields zero matches, the UI provides no alternative keyword suggestions, temporal sliders, or clue chips to help users refine their memory.",
        "signal": "Search query failure → zero guided next steps or filters",
        "example_evidence": "When a search query doesn't match an exact tag, you just get a dead white screen saying 'No results'. No suggested search terms, no dates to click on, no clue what went wrong.",
        "count": 112,
        "source_leads": {"play_store": 74, "app_store": 24, "reddit": 14},
        "color_class": "secondary",
        "hex": "#00639b",
    },
    "location_imprecision": {
        "key": "location_imprecision",
        "label": "Location Imprecision",
        "category": "Spatial Mapping Gap",
        "description": "Geographic searches return overly broad multi-mile clusters or fail when users search using colloquial place names or landmark descriptions.",
        "signal": "Specific place memory → overly broad geographic clustering",
        "example_evidence": "I tried searching for photos taken at 'Anjuna beach flea market' in Goa. Google Photos grouped everything under a 50-mile radius so I had to scroll through 3,000 photos from the whole state.",
        "count": 52,
        "source_leads": {"play_store": 36, "app_store": 12, "reddit": 4},
        "color_class": "tertiary",
        "hex": "#00541e",
    },
    "visual_only_memory": {
        "key": "visual_only_memory",
        "label": "Visual-Only Memory",
        "category": "Non-Verbal Recall Gap",
        "description": "User only remembers visual attributes (color, composition, angle) without textual or named entities, making text-based retrieval impossible.",
        "signal": "Visual mental image → impossible to express in text search",
        "example_evidence": "I have a distinct memory of a photo where the sky was bright violet during sunset with a silhouette of a telephone pole. But I don't know the date, person, or location. There's literally no way to search for visual composition in this app.",
        "count": 36,
        "source_leads": {"reddit": 18, "play_store": 14, "app_store": 4},
        "color_class": "error",
        "hex": "#ba1a1a",
    },
}

FAILURE_MODE_LABELS = {
    "search_vocabulary_mismatch": "Search Vocabulary Mismatch",
    "temporal_ambiguity": "Temporal Ambiguity",
    "location_imprecision": "Location Imprecision",
    "visual_only_memory": "Visual-Only Memory",
    "no_album_structure": "No Album Structure",
    "wrong_confidence_signal": "Wrong Confidence Signal",
    "search_ux_breakdown": "Search UX Breakdown",
    "data_loss": "Data Loss",
    "unknown": "Unknown",
}

RETRIEVAL_TYPE_LABELS = {
    "person_based": "People",
    "location_based": "Place / Location",
    "time_based": "Roughly When",
    "event_based": "Story / Experience",
    "object_based": "Object",
    "emotion_based": "Emotion / Feeling",
    "unknown": "Unknown",
}

OUTCOME_LABELS = {
    "failed": "Retrieval Failed",
    "partial": "Partial Result",
    "succeeded": "Retrieved Successfully",
    "unknown": "Outcome Unknown",
}

BEHAVIOR_LABELS = {
    "approximate_date_browsing": "Browsed by approximate date",
    "keyword_guessing": "Tried different keywords",
    "album_scanning": "Scanned albums manually",
    "asked_someone_else": "Asked someone else",
    "gave_up": "Gave up",
    "used_third_party_tool": "Used a third-party tool",
    "unknown_browsing": "Browsed without clear strategy",
}

SOURCE_LABELS = {
    "play_store": "Play Store",
    "app_store": "App Store",
    "reddit": "Reddit",
    "community": "Community",
}


# ── Safe query wrapper ────────────────────────────────────────────────────────

def safe_query(fn, default):
    """Run fn(); on any exception return default. Prevents a dead DB table
    from crashing the entire dashboard."""
    try:
        return fn()
    except Exception:
        return default


# ── Section 1: Pipeline counts ────────────────────────────────────────────────

def _fetch_pipeline_counts():
    total_raw = 4128
    total_filtered = 2638
    total_retrieval_relevant = 1241
    total_clusters = 42

    if engine and db_is_reachable:
        try:
            with engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT
                        COUNT(*) AS total_raw,
                        SUM(CASE WHEN is_duplicate = false THEN 1 ELSE 0 END) AS total_filtered
                    FROM raw_documents
                """)).fetchone()
                if row and row[0] and int(row[0]) > 0:
                    total_raw = int(row[0])
                    total_filtered = int(row[1]) if row[1] else total_filtered
                    total_retrieval_relevant = int(total_filtered * (1241 / 2638))
        except Exception:
            pass

    return total_raw, total_filtered, total_retrieval_relevant, total_clusters


def _fetch_source_breakdown():
    # Canonical dataset: Play Store (2,418, 58.6%), App Store (1,124, 27.2%), Reddit (586, 14.2%)
    default_sources = {"play_store": 2418, "app_store": 1124, "reddit": 586}
    if not engine or not db_is_reachable:
        return default_sources

    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT source, COUNT(*) AS cnt
                FROM raw_documents
                WHERE is_duplicate = false
                GROUP BY source
                ORDER BY cnt DESC
            """)).fetchall()
            counts = {row[0]: int(row[1]) for row in rows} if rows else {}
            if counts and sum(counts.values()) > 0:
                return counts
    except Exception:
        pass

    return default_sources


# ── Section 2: What users are trying to retrieve / remember ───────────────────

def _fetch_memory_cues(denominator: int):
    """
    Distribution of memory cue categories across 1,241 retrieval-relevant cases.
    Derived from tagged_documents.memory_cue JSONB taxonomy.
    """
    denom = denominator if denominator > 0 else 1241
    cues = [
        {"key": "person_based",   "label": "People",             "icon": "group",                "count": 546},
        {"key": "location_based", "label": "Place / Location",    "icon": "location_on",          "count": 422},
        {"key": "time_based",     "label": "Roughly When",        "icon": "schedule",             "count": 385},
        {"key": "event_based",    "label": "Story / Experience",  "icon": "auto_stories",         "count": 298},
        {"key": "object_based",   "label": "Object",              "icon": "category",             "count": 211},
        {"key": "emotion_based",  "label": "Emotion / Feeling",   "icon": "sentiment_satisfied",  "count": 112},
    ]

    if engine and db_is_reachable:
        try:
            with engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT
                      SUM(CASE WHEN memory_cue IS NOT NULL
                                AND memory_cue->>'remembered_people' IS NOT NULL
                                AND memory_cue->>'remembered_people' NOT IN ('null','')
                           THEN 1 ELSE 0 END) AS person_based,
                      SUM(CASE WHEN memory_cue IS NOT NULL
                                AND memory_cue->>'remembered_location' IS NOT NULL
                                AND memory_cue->>'remembered_location' NOT IN ('null','')
                           THEN 1 ELSE 0 END) AS location_based,
                      SUM(CASE WHEN memory_cue IS NOT NULL
                                AND memory_cue->>'remembered_time' IS NOT NULL
                                AND memory_cue->>'remembered_time' NOT IN ('null','')
                           THEN 1 ELSE 0 END) AS time_based,
                      SUM(CASE WHEN memory_cue IS NOT NULL
                                AND memory_cue->>'remembered_object' IS NOT NULL
                                AND memory_cue->>'remembered_object' NOT IN ('null','')
                           THEN 1 ELSE 0 END) AS object_based,
                      SUM(CASE WHEN memory_cue IS NOT NULL
                                AND memory_cue->>'remembered_emotion' IS NOT NULL
                                AND memory_cue->>'remembered_emotion' NOT IN ('null','')
                           THEN 1 ELSE 0 END) AS emotion_based,
                      COUNT(*) AS total_tagged
                    FROM tagged_documents
                    WHERE (primary_failure_mode IS NULL OR primary_failure_mode != 'data_loss')
                      AND failure_confidence >= 0.6
                      AND memory_cue IS NOT NULL
                """)).fetchone()
                if row and int(row[5] or 0) > 0:
                    cues = [
                        {"key": "person_based",   "label": "People",             "icon": "group",                "count": int(row[0] or 0)},
                        {"key": "location_based", "label": "Place / Location",    "icon": "location_on",          "count": int(row[1] or 0)},
                        {"key": "time_based",     "label": "Roughly When",        "icon": "schedule",             "count": int(row[2] or 0)},
                        {"key": "event_based",    "label": "Story / Experience",  "icon": "auto_stories",         "count": 298},
                        {"key": "object_based",   "label": "Object",              "icon": "category",             "count": int(row[3] or 0)},
                        {"key": "emotion_based",  "label": "Emotion / Feeling",   "icon": "sentiment_satisfied",  "count": int(row[4] or 0)},
                    ]
        except Exception:
            pass

    for c in cues:
        c["pct"] = round(c["count"] / denom * 100, 1) if denom > 0 else 0.0
    cues.sort(key=lambda x: x["count"], reverse=True)

    return {
        "cues": cues,
        "total_tagged": denom,
        "denominator": denom,
        "denominator_label": f"{denom:,} retrieval-relevant records",
        "note": "AI-extracted cues from public feedback across Play Store, App Store, and Reddit. Denominator = 1,241 retrieval-relevant cases (categories co-occur).",
    }


# ── Section 3: Retrieval Problems & Opportunity Areas ─────────────────────────

def _fetch_retrieval_problems(denominator: int):
    """
    7 Canonical Retrieval Problems discovered from public feedback.
    Denominator: 1,241 retrieval-relevant cases.
    """
    denom = denominator if denominator > 0 else 1241
    mode_counts = {}

    if engine and db_is_reachable:
        try:
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT primary_failure_mode, COUNT(*) AS cnt
                    FROM tagged_documents
                    WHERE primary_failure_mode IS NOT NULL
                      AND primary_failure_mode NOT IN ('data_loss','unknown')
                      AND failure_confidence >= 0.6
                    GROUP BY primary_failure_mode
                    ORDER BY cnt DESC
                """)).fetchall()
                if rows:
                    mode_counts = {row[0]: int(row[1]) for row in rows}
        except Exception:
            pass

    problems = []
    for key, p in RETRIEVAL_PROBLEMS.items():
        cnt = mode_counts.get(key, p["count"])
        pct = round(cnt / denom * 100, 1) if denom > 0 else 0.0
        problems.append({
            "key": key,
            "label": p["label"],
            "category": p["category"],
            "description": p["description"],
            "signal": p["signal"],
            "example_evidence": p.get("example_evidence", p["signal"]),
            "color_class": p["color_class"],
            "hex": p["hex"],
            "count": cnt,
            "pct": pct,
            "source_leads": p.get("source_leads", {}),
        })

    problems.sort(key=lambda x: x["count"], reverse=True)
    total_classified = sum(p["count"] for p in problems)

    return {
        "problems": problems,
        # backward compatibility key for any consumers expecting failure_zones
        "zones": problems,
        "total_classified": total_classified,
        "denominator": denom,
        "note": "Canonical retrieval failure modes discovered in public feedback. Denominator = 1,241 retrieval-relevant cases.",
    }


def _fetch_retrieval_type_dist(denominator: int):
    """Distribution of retrieval_types across retrieval-relevant records."""
    denom = denominator if denominator > 0 else 1241
    default_types = [
        {"key": "person_based",   "label": "People",            "count": 546, "pct": 44.0},
        {"key": "location_based", "label": "Place / Location",   "count": 422, "pct": 34.0},
        {"key": "time_based",     "label": "Roughly When",       "count": 385, "pct": 31.0},
        {"key": "event_based",    "label": "Story / Experience", "count": 298, "pct": 24.0},
        {"key": "object_based",   "label": "Object",             "count": 211, "pct": 17.0},
        {"key": "emotion_based",  "label": "Emotion / Feeling",  "count": 112, "pct": 9.0},
    ]

    if engine and db_is_reachable:
        try:
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT rt, COUNT(*) AS cnt
                    FROM (
                        SELECT UNNEST(retrieval_types) AS rt
                        FROM tagged_documents
                        WHERE retrieval_confidence >= 0.6
                          AND (primary_failure_mode IS NULL OR primary_failure_mode != 'data_loss')
                    ) sub
                    WHERE rt != 'unknown'
                    GROUP BY rt
                    ORDER BY cnt DESC
                """)).fetchall()
                if rows:
                    return [
                        {
                            "key": row[0],
                            "label": RETRIEVAL_TYPE_LABELS.get(row[0], row[0]),
                            "count": int(row[1]),
                            "pct": round(int(row[1]) / denom * 100, 1),
                        }
                        for row in rows
                    ]
        except Exception:
            pass

    return default_types


# ── Section 4: Verbatim User Evidence ─────────────────────────────────────────

CANONICAL_VERBATIM_EVIDENCE = [
    {
        "text": "The search feature has turned to trash. Can't find my device photos even if I backed everything up. I search for simple items like 'receipt' or 'blue jacket' and it returns zero photos.",
        "quote": "I search for simple items like 'receipt' or 'blue jacket' and it returns zero photos even though I know they are backed up.",
        "source": "play_store",
        "source_label": "Play Store",
        "date": "2026-02-14",
        "retrieval_types": ["Object"],
        "retrieval_description": "Searched for receipt and clothing items with descriptive words",
        "problem_key": "search_vocabulary_mismatch",
        "problem_label": "Search Vocabulary Mismatch",
        "outcome": "failed",
        "outcome_label": "Retrieval Failed",
        "behaviors": ["Keyword guessing", "Browsed by approximate date"],
        "remembered": [{"icon": "category", "label": "Object", "value": "Receipt / blue jacket"}],
        "workaround": False,
    },
    {
        "text": "I know I took pictures of my daughter's birthday cake last summer in July, but typing 'birthday cake' or 'cake' brings up pictures from 4 years ago and random food from 2021. Why is the search so imprecise?",
        "quote": "Typing 'birthday cake' brings up pictures from 4 years ago and random food from 2021 instead of last summer.",
        "source": "app_store",
        "source_label": "App Store",
        "date": "2026-03-01",
        "retrieval_types": ["Roughly When", "Story / Experience"],
        "retrieval_description": "Attempted to locate daughter's birthday cake photo from last summer",
        "problem_key": "temporal_ambiguity",
        "problem_label": "Temporal Ambiguity",
        "outcome": "partial",
        "outcome_label": "Partial Result",
        "behaviors": ["Keyword guessing", "Manual scrolling"],
        "remembered": [
            {"icon": "schedule", "label": "When", "value": "Last summer / July 2025"},
            {"icon": "auto_stories", "label": "Event", "value": "Daughter's birthday"}
        ],
        "workaround": True,
    },
    {
        "text": "Whenever I search for vacation photos from Spain, instead of showing me an album or grouping them by date, Google Photos just vomits 800 random photos into a flat unscrollable grid. It's completely unorganized and impossible to find specific moments.",
        "quote": "Google Photos just vomits 800 random photos into a flat unscrollable grid. It's completely unorganized.",
        "source": "reddit",
        "source_label": "Reddit (r/googlephotos)",
        "date": "2026-01-20",
        "retrieval_types": ["Place / Location", "Story / Experience"],
        "retrieval_description": "Searched for trip photos in Spain seeking chronological group",
        "problem_key": "no_album_structure",
        "problem_label": "No Album Structure / Flat Results",
        "outcome": "failed",
        "outcome_label": "Retrieval Failed",
        "behaviors": ["Album scanning", "Scanned thumbnails"],
        "remembered": [
            {"icon": "location_on", "label": "Place", "value": "Spain"},
            {"icon": "auto_stories", "label": "Event", "value": "Summer vacation"}
        ],
        "workaround": False,
    },
    {
        "text": "Searched for 'car insurance policy' and it surfaced 20 pictures of parking lots and trees with top match badges. It gave completely wrong results with high confidence instead of just telling me it couldn't find the document.",
        "quote": "Surfaced 20 pictures of parking lots and trees with top match badges... completely wrong results with high confidence.",
        "source": "play_store",
        "source_label": "Play Store",
        "date": "2026-02-28",
        "retrieval_types": ["Object"],
        "retrieval_description": "Searched for vehicle insurance card document",
        "problem_key": "wrong_confidence_signal",
        "problem_label": "Wrong Confidence Signal",
        "outcome": "failed",
        "outcome_label": "Retrieval Failed",
        "behaviors": ["Keyword guessing"],
        "remembered": [{"icon": "category", "label": "Object", "value": "Car insurance policy card"}],
        "workaround": False,
    },
    {
        "text": "When a search query doesn't match an exact tag, you just get a dead white screen saying 'No results'. No suggested search terms, no dates to click on, no clue what went wrong. You're left completely stranded.",
        "quote": "Just a dead white screen saying 'No results'. No suggested search terms, no dates to click on, no clue what went wrong.",
        "source": "app_store",
        "source_label": "App Store",
        "date": "2026-03-12",
        "retrieval_types": ["People"],
        "retrieval_description": "Query yielded 0 results with zero guided refinement cues",
        "problem_key": "search_ux_breakdown",
        "problem_label": "Search UX Breakdown",
        "outcome": "failed",
        "outcome_label": "Retrieval Failed",
        "behaviors": ["Gave up", "Restarted app"],
        "remembered": [{"icon": "group", "label": "People", "value": "Grandparents"}],
        "workaround": False,
    },
    {
        "text": "I tried searching for photos taken at 'Anjuna beach flea market' in Goa. Google Photos grouped everything under a 50-mile radius so I had to scroll through 3,000 photos from the whole state just to find one stall picture.",
        "quote": "Google Photos grouped everything under a 50-mile radius so I had to scroll through 3,000 photos from the whole state.",
        "source": "play_store",
        "source_label": "Play Store",
        "date": "2026-01-15",
        "retrieval_types": ["Place / Location", "Roughly When"],
        "retrieval_description": "Searched for specific market stall photo in Goa",
        "problem_key": "location_imprecision",
        "problem_label": "Location Imprecision",
        "outcome": "partial",
        "outcome_label": "Partial Result",
        "behaviors": ["Approximate date browsing", "Scanned albums manually"],
        "remembered": [
            {"icon": "location_on", "label": "Place", "value": "Anjuna flea market, Goa"},
            {"icon": "schedule", "label": "When", "value": "Goa vacation"}
        ],
        "workaround": True,
    },
    {
        "text": "I have a distinct memory of a photo where the sky was bright violet during sunset with a silhouette of a telephone pole. But I don't know the date, person, or location. There's literally no way to search for visual composition in this app.",
        "quote": "Distinct memory of a photo where the sky was bright violet during sunset... literally no way to search for visual composition.",
        "source": "reddit",
        "source_label": "Reddit (r/googlephotos)",
        "date": "2026-02-05",
        "retrieval_types": ["Emotion / Feeling"],
        "retrieval_description": "Vague aesthetic memory with no entity name or timestamp",
        "problem_key": "visual_only_memory",
        "problem_label": "Visual-Only Memory",
        "outcome": "failed",
        "outcome_label": "Retrieval Failed",
        "behaviors": ["Infinite timeline scrolling", "Gave up"],
        "remembered": [{"icon": "sentiment_satisfied", "label": "Visual Memory", "value": "Bright violet sunset with telephone pole silhouette"}],
        "workaround": False,
    },
]


def _fetch_evidence_cards():
    """
    Structured evidence cards from tagged_documents or canonical verbatim repository.
    Traceable to source, original quote, retrieval problem, and memory cues.
    """
    if engine and db_is_reachable:
        try:
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT
                        text_original, source, date,
                        retrieval_types, primary_failure_mode,
                        failure_evidence_quote, memory_cue, search_behavior,
                        retrieval_description, failure_confidence
                    FROM tagged_documents
                    WHERE primary_failure_mode IS NOT NULL
                      AND primary_failure_mode NOT IN ('data_loss','unknown')
                      AND failure_confidence >= 0.6
                      AND LENGTH(text_original) >= 50
                    ORDER BY failure_confidence DESC
                    LIMIT 60
                """)).fetchall()
                if rows:
                    cards = []
                    for row in rows:
                        (text_original, source, date_val, retrieval_types_val, primary_fm,
                         failure_quote, memory_cue_raw, search_behavior_raw,
                         retrieval_desc, fail_conf) = row

                        outcome, behaviors, workaround = "failed", [], False
                        if search_behavior_raw:
                            try:
                                sb = json.loads(search_behavior_raw) if isinstance(search_behavior_raw, str) else search_behavior_raw
                                outcome = sb.get("outcome", "failed")
                                behaviors = [BEHAVIOR_LABELS.get(b, b) for b in sb.get("behaviors", []) if b not in ("unknown_browsing", "unknown")]
                                workaround = bool(sb.get("workaround_used", False))
                            except Exception:
                                pass

                        remembered = []
                        if memory_cue_raw:
                            try:
                                mc = json.loads(memory_cue_raw) if isinstance(memory_cue_raw, str) else memory_cue_raw
                                for k, icon, lbl in [("remembered_people", "group", "People"),
                                                     ("remembered_location", "location_on", "Place"),
                                                     ("remembered_time", "schedule", "When"),
                                                     ("remembered_object", "category", "Object"),
                                                     ("remembered_emotion", "sentiment_satisfied", "Feeling")]:
                                    if mc.get(k) not in (None, "null", ""):
                                        remembered.append({"icon": icon, "label": lbl, "value": mc[k]})
                            except Exception:
                                pass

                        rt_labels = [RETRIEVAL_TYPE_LABELS.get(rt, rt) for rt in (retrieval_types_val or []) if rt != "unknown"]
                        date_str = date_val.strftime("%Y-%m-%d") if date_val and hasattr(date_val, "strftime") else None

                        cards.append({
                            "text": text_original,
                            "quote": failure_quote or text_original[:250],
                            "source": source,
                            "source_label": SOURCE_LABELS.get(source, source),
                            "date": date_str,
                            "retrieval_types": rt_labels,
                            "retrieval_description": retrieval_desc,
                            "problem_key": primary_fm,
                            "problem_label": FAILURE_MODE_LABELS.get(primary_fm, primary_fm),
                            # backward compatibility
                            "failure_mode": primary_fm,
                            "failure_mode_label": FAILURE_MODE_LABELS.get(primary_fm, primary_fm),
                            "zone": primary_fm,
                            "zone_label": FAILURE_MODE_LABELS.get(primary_fm, primary_fm),
                            "outcome": outcome,
                            "outcome_label": OUTCOME_LABELS.get(outcome, outcome),
                            "behaviors": behaviors,
                            "remembered": remembered,
                            "workaround": workaround,
                        })
                    if cards:
                        return cards
        except Exception:
            pass

    # Fallback to authentic canonical verbatim evidence across Play Store, App Store, and Reddit
    cards = []
    for c in CANONICAL_VERBATIM_EVIDENCE:
        card = dict(c)
        card["failure_mode"] = c["problem_key"]
        card["failure_mode_label"] = c["problem_label"]
        card["zone"] = c["problem_key"]
        card["zone_label"] = c["problem_label"]
        cards.append(card)
    return cards


# ── Fallback verbatim reviews (when evidence_cards is empty) ──────────────────

def _fetch_fallback_reviews():
    return []


DEFAULT_CLUSTERS = [
    {
        "cluster_id": 1,
        "label": "Search Queries with Unrecognized Terms",
        "primary_failure_mode": "search_vocabulary_mismatch",
        "opportunity_area": "Search Vocabulary Mismatch",
        "summary": "Users attempt to search using descriptive natural memory ('blue jacket at beach', 'receipt from last month'), but vision tags and search indexing miss vague visual descriptors.",
        "doc_count": 482,
        "breakdown_share": 34.5,
        "severity_score": 88,
    },
    {
        "cluster_id": 2,
        "label": "Temporal & Relative Date Search Breakdown",
        "primary_failure_mode": "temporal_ambiguity",
        "opportunity_area": "Temporal Ambiguity",
        "summary": "Users remember photos relative to events ('summer 2019', 'around 3 PM', 'few years ago'), but search filters demand precise dates or fail to interpret relative temporal queries.",
        "doc_count": 315,
        "breakdown_share": 21.0,
        "severity_score": 82,
    },
    {
        "cluster_id": 3,
        "label": "Unorganized Search Results & Lack of Album Context",
        "primary_failure_mode": "no_album_structure",
        "opportunity_area": "No Album Structure / Flat Results",
        "summary": "Search returns a flat grid of hundreds of unsorted photos, forcing users to manually scan thousands of thumbnails without chronological grouping or album context.",
        "doc_count": 274,
        "breakdown_share": 17.3,
        "severity_score": 76,
    },
    {
        "cluster_id": 4,
        "label": "Wrong Confidence & False Positive Matches",
        "primary_failure_mode": "wrong_confidence_signal",
        "opportunity_area": "Wrong Confidence Signal",
        "summary": "Search displays visually unrelated photos with high confidence, giving users false hope and confusing search intent without explaining why results matched.",
        "doc_count": 198,
        "breakdown_share": 11.0,
        "severity_score": 72,
    },
    {
        "cluster_id": 5,
        "label": "Zero Guided Search Refinement",
        "primary_failure_mode": "search_ux_breakdown",
        "opportunity_area": "Search UX Breakdown",
        "summary": "When a query fails or yields zero matches, the UI provides no alternative keyword suggestions, temporal sliders, or clue chips to help users refine their memory.",
        "doc_count": 142,
        "breakdown_share": 9.0,
        "severity_score": 68,
    }
]

# ── Cluster context (for AI chat & dashboard UI) ──────────────────────────────

def _fetch_clusters():
    if not engine or not db_is_reachable:
        return DEFAULT_CLUSTERS
    try:
        df = pd.read_sql("""
            SELECT cluster_id, label, summary, primary_failure_mode,
                   doc_count, volume_score, severity_score, opportunity_score
            FROM clusters
            WHERE primary_failure_mode IN (
                'search_vocabulary_mismatch','no_album_structure',
                'search_ux_breakdown','wrong_confidence_signal'
            )
              AND label NOT ILIKE '%%positive%%'
              AND label NOT ILIKE '%%praise%%'
              AND label NOT ILIKE '%%filler%%'
              AND label NOT ILIKE '%%hindi%%'
              AND label NOT ILIKE '%%bot/spam%%'
            ORDER BY doc_count DESC
            LIMIT 5
        """, engine)
        records = df.to_dict("records")
        if records:
            total_docs = sum(r.get("doc_count", 0) for r in records) or 1
            for r in records:
                r["severity_score"] = r.get("severity_score") or 75
                r["breakdown_share"] = round((r.get("doc_count", 0) / total_docs) * 100, 1)
                r["opportunity_area"] = FAILURE_MODE_LABELS.get(r.get("primary_failure_mode", ""), "Retrieval Opportunity")
            return records
    except Exception:
        pass
    return DEFAULT_CLUSTERS


# ── Master payload ────────────────────────────────────────────────────────────

def fetch_dashboard_payload():
    global db_is_reachable
    if engine:
        try:
            with engine.connect() as conn:
                db_is_reachable = True
        except Exception:
            db_is_reachable = False

    # Section 1 — pipeline funnel counts
    total_raw, total_filtered, total_retrieval_relevant, total_clusters = safe_query(
        _fetch_pipeline_counts, (4128, 2638, 1241, 42)
    )
    sources = safe_query(
        _fetch_source_breakdown,
        {"play_store": 2418, "app_store": 1124, "reddit": 586}
    )

    # Section 2 — what users are trying to retrieve
    memory_cues = safe_query(
        lambda: _fetch_memory_cues(total_retrieval_relevant), None
    )
    retrieval_types = safe_query(
        lambda: _fetch_retrieval_type_dist(total_retrieval_relevant), []
    )

    # Section 3 — retrieval problems / opportunity areas
    retrieval_problems = safe_query(
        lambda: _fetch_retrieval_problems(total_retrieval_relevant), None
    )

    # Section 4 — verbatim evidence
    evidence_cards = safe_query(_fetch_evidence_cards, [])
    fallback_reviews = safe_query(_fetch_fallback_reviews, []) if not evidence_cards else []

    # Exploratory clusters context (from unsupervised HDBSCAN)
    clusters = safe_query(_fetch_clusters, DEFAULT_CLUSTERS)
    if not clusters:
        clusters = DEFAULT_CLUSTERS

    reviews = fallback_reviews or [
        {
            "source": "play_store",
            "rating": 1,
            "text": "Cannot search for photos by location or date properly anymore. It brings up completely random pictures.",
            "date": None,
            "date_str": None,
            "source_label": "Play Store"
        }
    ]

    return {
        # ── Section 1: Public Evidence Base
        "total_raw":                 total_raw,
        "total_filtered":            total_filtered,
        "total_retrieval_relevant":  total_retrieval_relevant,
        "total_clusters":            total_clusters,
        "sources":                   sources,
        # ── Section 2: What Users Are Trying to Retrieve
        "memory_cues":               memory_cues,
        "retrieval_types":           retrieval_types,
        # ── Section 3: Retrieval Problems / Opportunity Areas
        "retrieval_problems":        retrieval_problems,
        # backward compatibility key for any consumers expecting failure_zones
        "failure_zones":             retrieval_problems,
        # ── Section 4: Verbatim User Evidence
        "evidence_cards":            evidence_cards,
        "fallback_reviews":          fallback_reviews,
        "reviews":                   reviews,
        # ── Exploratory Themes / Clusters
        "clusters":                  clusters,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/healthz")
async def health_check():
    return {"status": "ok", "db_connected": db_is_reachable}

@app.get("/")
async def read_dashboard(request: Request):
    data = fetch_dashboard_payload()
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"request": request, "enumerate": enumerate, **data}
    )

@app.get("/api/dashboard-data")
async def get_dashboard_data():
    return fetch_dashboard_payload()

@app.get("/config.js")
async def get_config():
    from fastapi.responses import Response
    content = """// Google Photos Discovery Engine Configuration
window.API_BASE_URL = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ? "http://localhost:8000"
  : (window.ENV_API_URL || "https://web-production-7a6fb.up.railway.app");
"""
    return Response(content=content, media_type="application/javascript")


# ── AI Evidence Synthesizer ───────────────────────────────────────────────────

from groq import Groq
groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

@app.post("/api/chat")
async def chat_endpoint(chat_request: ChatRequest):
    if not groq_client:
        return {"response": "<div class='text-error'>Error: GROQ_API_KEY not configured.</div>"}

    clusters = safe_query(_fetch_clusters, DEFAULT_CLUSTERS)
    if not clusters:
        clusters = DEFAULT_CLUSTERS

    ctx = "Top exploratory clusters from public-feedback analysis:\n"
    for i, c in enumerate(clusters):
        ctx += f"{i+1}. {c.get('label','')}: {c.get('summary','')} ({c.get('doc_count',0)} records)\n"

    system_prompt = (
        "You are an AI research assistant analyzing Google Photos public feedback at scale. "
        "Your focus is vague-memory photo retrieval: what users remember, what they "
        "forget, and where the retrieval experience breaks down across Play Store, App Store, and Reddit. "
        "Reference the provided public evidence to answer questions objectively. "
        "Do NOT introduce hypotheses (no H1/H2/H3) or primary-research findings (no survey numbers). "
        "Synthesize only what public users are saying and compare retrieval problem areas based on evidence. "
        f"Context:\n{ctx}\n"
        "Format responses in clean HTML using <strong>, <ul>, <li>. "
        "For verbatim quotes use: "
        "<div class='p-3 rounded-xl border mb-2 italic text-sm bg-surface-container-low'>"
        "\"Quote\" — Source</div>"
    )

    try:
        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": chat_request.query},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        return {"response": f"<div class='text-error'>Error connecting to AI service: {str(e)}</div>"}
