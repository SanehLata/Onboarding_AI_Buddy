# config.py
# @Author: Saneh Lata
# Central configuration — paths, model names, constants, logging, observability.
# All modules import from here. Never hardcode paths elsewhere.

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR        = Path(__file__).resolve().parent
DATA_DIR        = BASE_DIR / "data"
MOCK_DOCS_DIR   = DATA_DIR / "mock_docs"
MOCK_DB_DIR     = DATA_DIR / "mock_db"
VECTORSTORE_DIR = DATA_DIR / "vectorstore"
DB_PATH         = MOCK_DB_DIR / "onboarding.db"
TEAMS_JSON      = MOCK_DB_DIR / "teams.json"
SYSTEMS_JSON    = MOCK_DB_DIR / "systems.json"
DL_GROUPS_JSON  = MOCK_DB_DIR / "dl_groups.json"

# ── LLM ───────────────────────────────────────────────────────────────────────

GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
LLM_MODEL       = "llama-3.3-70b-versatile"
LLM_TEMPERATURE = 0
LLM_MAX_TOKENS  = 1024

# ── Embeddings ────────────────────────────────────────────────────────────────

EMBEDDING_MODEL    = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME    = "onboarding_knowledge_base"
RETRIEVER_TOP_K    = 4

# ── Chunking ──────────────────────────────────────────────────────────────────

CHUNK_SIZE    = 500
CHUNK_OVERLAP = 100

# ── Agent behaviour ───────────────────────────────────────────────────────────

MAX_RETRIES            = 3   # tool call retry attempts
RETRY_DELAY_SECONDS    = 2   # wait between retries
PROACTIVE_NUDGE_AFTER  = 3   # suggest next topic after N questions answered
HITL_QUESTIONS_PER_DOC = 3   # ask to mark doc complete after N questions about it
HITL_SNOOZE_AFTER      = 3   # if dev says No, ask again after N more questions

# ── LangSmith observability ───────────────────────────────────────────────────
# Tracing is automatic when LANGCHAIN_TRACING_V2=true.
# LangChain and LangGraph instrument all LLM calls, tool calls, and node
# transitions without any additional code changes.
#
# Setup:
#   1. Sign up at https://smith.langchain.com (free tier is sufficient)
#   2. Create an API key in Settings → API Keys
#   3. Add to your .env file:
#        LANGCHAIN_TRACING_V2=true
#        LANGCHAIN_API_KEY=your_key_here
#        LANGCHAIN_PROJECT=onboarding-buddy
#        LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
#
# To disable tracing (e.g. in production or to save quota):
#   Set LANGCHAIN_TRACING_V2=false in your .env

os.environ.setdefault(
    "LANGCHAIN_TRACING_V2",
    os.getenv("LANGCHAIN_TRACING_V2", "false")
)
os.environ.setdefault(
    "LANGCHAIN_API_KEY",
    os.getenv("LANGCHAIN_API_KEY", "")
)
os.environ.setdefault(
    "LANGCHAIN_PROJECT",
    os.getenv("LANGCHAIN_PROJECT", "onboarding-buddy")
)
os.environ.setdefault(
    "LANGCHAIN_ENDPOINT",
    os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
)

# ── Local logging ─────────────────────────────────────────────────────────────
# Writes to both terminal and logs/onboarding_buddy.log.
# Use: from config import log
# Then: log.info("...") / log.warning("...") / log.error("...")
#
# Log levels:
#   DEBUG   — very verbose (LLM prompts, full state diffs)
#   INFO    — normal operation (node transitions, route decisions, tool outcomes)
#   WARNING — unexpected but recoverable (missing fields, fallbacks triggered)
#   ERROR   — failures that affect the user (tool errors, DB failures)

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

_formatter = logging.Formatter(
    fmt   = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)

_file_handler    = logging.FileHandler(LOG_DIR / "onboarding_buddy.log", encoding="utf-8")
_console_handler = logging.StreamHandler()

_file_handler.setFormatter(_formatter)
_console_handler.setFormatter(_formatter)

# Root logger for the project — all submodule loggers inherit from this
logging.getLogger("onboarding_buddy").setLevel(logging.INFO)
logging.getLogger("onboarding_buddy").addHandler(_file_handler)
logging.getLogger("onboarding_buddy").addHandler(_console_handler)
logging.getLogger("onboarding_buddy").propagate = False

# Silence noisy third-party loggers that aren't useful day-to-day
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

# Single logger instance imported by all modules
log = logging.getLogger("onboarding_buddy")