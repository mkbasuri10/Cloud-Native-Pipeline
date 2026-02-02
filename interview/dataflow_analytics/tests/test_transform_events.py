from __future__ import annotations

import json
from pathlib import Path

from dataflow_analytics.config import Settings
from dataflow_analytics.jobs.transform_events import run_job
from dataflow_analytics.storage import S3Storage, start_moto, stop_moto


def _write_events(path: Path) -> None:
    rows = [
        {"event_id": "1", "user_id": "u1", "event_type": "page_view", "timestamp": "2026-01-30T10:00:00Z"},
        {"event_id": "2", "user_id": "u2", "event_type": "page_view", "timestamp": "2026-01-30T10:05:00Z"},
        {"event_id": "3", "user_id": "u1", "event_type": "signup", "timestamp": "2026-01-30T11:00:00Z"},
        {"event_id": "4", "user_id": "u3", "event_type": "purchase", "timestamp": "2026-01-31T12:00:00Z"},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")


def test_run_job_uploads_metrics(tmp_path: Path) -> None:
    start_moto()
    try:
        raw_path = tmp_path / "events.jsonl"
        _write_events(raw_path)
        cfg = Settings(s3_use_mock=True, s3_bucket="test-bucket", s3_prefix="metrics")
        storage = S3Storage(bucket=cfg.s3_bucket, prefix=cfg.s3_prefix, cfg=cfg)

        output_dir = tmp_path / "spark"
        run_job(raw_path, output_dir, storage)

        key = storage.key("metrics_by_day.jsonl")
        text = storage.download_text(key)
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        assert len(rows) == 3
        counts = {(row["event_date"], row["event_type"]): row["event_count"] for row in rows}
        assert counts[("2026-01-30", "page_view")] == 2
        assert counts[("2026-01-30", "signup")] == 1
        assert counts[("2026-01-31", "purchase")] == 1
    finally:
        stop_moto()
