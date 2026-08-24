"""Central configuration, including the FROZEN CLOCK.

Rule 3: time is frozen. The dataset snapshot from the workbook README is the ONLY
"now" in this system. `datetime.now()` / `date.today()` / `time.time()` are banned
repo-wide (a test greps for them). Always import `SNAPSHOT_AT` from here.
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED = ROOT / "data" / "extracted"
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "parcelpilot.sqlite"

# --- THE FROZEN CLOCK ---------------------------------------------------------
# README sheet: "Dataset snapshot = 2026-08-16 11:00 Asia/Kolkata".
# This constant is the sole source of "now". Verified against the workbook by
# tests/test_snapshot.py so it can never silently drift from the data.
SNAPSHOT_TZ = ZoneInfo("Asia/Kolkata")
SNAPSHOT_AT = datetime(2026, 8, 16, 11, 0, 0, tzinfo=SNAPSHOT_TZ)

# Currency for the whole dataset (README sheet). All money is whole INR.
CURRENCY = "INR"


def now() -> datetime:
    """The only sanctioned 'current time': the frozen snapshot.

    Business logic must call this instead of the wall clock.
    """
    return SNAPSHOT_AT


class Settings(BaseSettings):
    """Provider / runtime settings loaded from .env.

    Generation is provider-agnostic (Gemini and/or Groq) behind src/llm/client.py.
    Embeddings are ALWAYS local — no embeddings API — so there is no key for them.
    """

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    llm_provider: str = Field(default="gemini")
    llm_fallback_provider: str = Field(default="")

    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-3.7-flash")

    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="openai/gpt-oss-120b")

    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5")

    # Hand-written agent loop cap (Rule 1: few, fat tool calls).
    max_agent_iterations: int = Field(default=8)


@lru_cache
def get_settings() -> Settings:
    return Settings()
