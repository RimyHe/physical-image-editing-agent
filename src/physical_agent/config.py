from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    planner_model: str
    verifier_model: str
    image_edit_model: str
    timeout_seconds: int = 120
    max_retries: int = 1


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    base_url = os.getenv("OPENAI_COMPAT_BASE_URL", "").rstrip("/")
    api_key = os.getenv("OPENAI_COMPAT_API_KEY", "")
    missing = [
        name
        for name, value in {
            "OPENAI_COMPAT_BASE_URL": base_url,
            "OPENAI_COMPAT_API_KEY": api_key,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return Settings(
        base_url=base_url,
        api_key=api_key,
        planner_model=_env_or_default("PLANNER_MODEL", "gpt-5.4-mini"),
        verifier_model=_env_or_default("VERIFIER_MODEL", "gpt-5.4-mini"),
        image_edit_model=_env_or_default("IMAGE_EDIT_MODEL", "gpt-image-2"),
        timeout_seconds=int(os.getenv("API_TIMEOUT_SECONDS", "120")),
        max_retries=int(os.getenv("MAX_AGENT_RETRIES", "1")),
    )


def _env_or_default(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default
