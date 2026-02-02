from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from dataflow_analytics.api.app import create_app
from dataflow_analytics.config import Settings
from dataflow_analytics.storage import S3Storage, start_moto, stop_moto


def test_api_summary_and_search(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ops.md").write_text(
        "Ingestion latency should stay under 15 minutes. Check the Spark logs if it grows.",
        encoding="utf-8",
    )
    (docs_dir / "support.md").write_text(
        "If purchase events drop, re-run the aggregation job.",
        encoding="utf-8",
    )

    cfg = Settings(
        s3_use_mock=True,
        s3_bucket="api-bucket",
        s3_prefix="metrics",
        docs_dir=docs_dir,
    )

    start_moto()
    try:
        storage = S3Storage(bucket=cfg.s3_bucket, prefix=cfg.s3_prefix, cfg=cfg)
        rows = [
            {"event_date": "2026-01-30", "event_type": "page_view", "event_count": 5, "unique_users": 3},
            {"event_date": "2026-01-30", "event_type": "purchase", "event_count": 2, "unique_users": 2},
        ]
        payload = "\n".join(json.dumps(row) for row in rows)
        storage.upload_text(payload, storage.key("metrics_by_day.jsonl"))

        app = create_app(cfg)
        with TestClient(app) as client:
            summary = client.get("/analytics/summary").json()
            assert summary["total_events"] == 7
            assert summary["event_types"]["page_view"] == 5

            results = client.get("/docs/search", params={"q": "latency"}).json()
            assert results["results"]
    finally:
        stop_moto()
