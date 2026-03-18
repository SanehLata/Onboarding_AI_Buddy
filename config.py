# config.py
# @Author: Saneh Lata
# Central configuration — paths, model names, constants.
# All modules import from here. Never hardcode paths elsewhere.

import os
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

MAX_RETRIES           = 3          # tool call retry attempts
RETRY_DELAY_SECONDS   = 2          # wait between retries
PROACTIVE_NUDGE_AFTER = 3          # suggest next topic after N questions answered
HITL_QUESTIONS_PER_DOC = 3         # ask to mark doc complete after N questions about it
HITL_SNOOZE_AFTER      = 3         # if dev says No, ask again after N more questions about same doc