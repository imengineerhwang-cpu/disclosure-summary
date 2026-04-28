from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"
DB_PATH = DATA_DIR / "disclosures.db"

load_dotenv(PROJECT_ROOT / ".env")


def get_dart_api_key() -> str:
    key = os.getenv("DART_API_KEY")
    if not key:
        raise RuntimeError(
            "DART_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요 (.env.example 참고)."
        )
    return key


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
