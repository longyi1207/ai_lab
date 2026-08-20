"""Process-level settings: data dir, DB DSN, Azure/OpenAI routing, alert env.

Loaded once from env + a project-root `.env` (standalone-repo convention —
this project was extracted from a larger monorepo where the equivalent rule
lives in that repo's own AZURE.md: credentials in repo-root `.env` only,
never a credential vault, for this project).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# research_dojo/src/research_dojo/config/settings.py -> project root is parents[3]
PACKAGE_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PACKAGE_ROOT
_ENV_PATH = REPO_ROOT / ".env"


def load_repo_env() -> None:
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOJO_", extra="ignore")

    data_dir: Path = Field(default=PACKAGE_ROOT / "outputs")
    database_url: str | None = Field(default=None, alias="DOJO_DATABASE_URL")

    alert_webhook_url: str = Field(default="")
    alert_min_severity: str = Field(default="warning")

    wandb_enabled: bool = Field(default=False, alias="DOJO_WANDB")

    stale_threshold_seconds: int = Field(default=600)
    heartbeat_interval_seconds: int = Field(default=60)
    max_dlq_attempts: int = Field(default=5)
    circuit_breaker_threshold: int = Field(default=5)
    circuit_breaker_cooldown_seconds: int = Field(default=60)

    def resolve_data_dir(self) -> Path:
        d = self.data_dir
        d.mkdir(parents=True, exist_ok=True)
        return d

    def resolve_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        db_path = self.resolve_data_dir() / "dojo.db"
        return f"sqlite:///{db_path}"

    def artifacts_root(self) -> Path:
        d = self.resolve_data_dir() / "artifacts"
        d.mkdir(parents=True, exist_ok=True)
        return d


@lru_cache
def get_settings() -> Settings:
    load_repo_env()
    return Settings()


def azure_openai_client_and_model():
    """Return (OpenAI-SDK client, model_name) per docs/AZURE.md routing rule:
    prefer Azure OpenAI, fall back to direct OpenAI, else raise.
    """
    from openai import OpenAI

    load_repo_env()
    prefer_azure = os.getenv("OPENAI_PREFER_AZURE", "true").lower() in ("1", "true", "yes")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_ep = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").rstrip("/")
    azure_deploy = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if prefer_azure and azure_key and azure_ep and azure_deploy:
        client = OpenAI(api_key=azure_key, base_url=f"{azure_ep}/openai/v1/")
        return client, azure_deploy
    if os.getenv("OPENAI_API_KEY"):
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        return client, os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    raise RuntimeError(
        "No usable chat credentials: set AZURE_OPENAI_{API_KEY,ENDPOINT,DEPLOYMENT} "
        f"or OPENAI_API_KEY in {_ENV_PATH}"
    )
