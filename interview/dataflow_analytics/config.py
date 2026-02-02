from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DFA_", env_file=".env", env_file_encoding="utf-8")

    # S3 configuration
    s3_bucket: str = "dfa-analytics"
    s3_prefix: str = "aggregates"
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    s3_use_mock: bool = True

    # Local paths
    base_dir: Path = Path(__file__).resolve().parents[1]
    data_dir: Path = base_dir / "dataflow_analytics" / "data"
    raw_events_path: Path = data_dir / "raw" / "events.jsonl"
    docs_dir: Path = data_dir / "docs"
    tmp_dir: Path = base_dir / ".tmp"


settings = Settings()
