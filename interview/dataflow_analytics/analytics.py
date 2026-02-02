from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from .config import Settings, settings as default_settings
from .storage import S3Storage


@dataclass
class MetricsSummary:
    total_events: int
    event_types: dict[str, int]
    dates: dict[str, str] | None
    daily_unique_users_sum: int


class AnalyticsService:
    def __init__(self, cfg: Settings | None = None):
        self.cfg = cfg or default_settings
        self.storage = S3Storage(self.cfg.s3_bucket, self.cfg.s3_prefix, self.cfg)
        self.metrics_key = self.storage.key("metrics_by_day.jsonl")

    def load_metrics(self) -> list[dict[str, Any]]:
        try:
            text = self.storage.download_text(self.metrics_key)
        except Exception:
            return []
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows

    def summary(self) -> MetricsSummary:
        rows = self.load_metrics()
        total_events = 0
        daily_unique_users_sum = 0
        event_types: dict[str, int] = {}
        dates: list[date] = []
        for row in rows:
            count = int(row.get("event_count", 0))
            unique_users = int(row.get("unique_users", 0))
            total_events += count
            daily_unique_users_sum += unique_users
            event_type = row.get("event_type") or "unknown"
            event_types[event_type] = event_types.get(event_type, 0) + count
            event_date = row.get("event_date")
            if event_date:
                try:
                    dates.append(date.fromisoformat(event_date))
                except ValueError:
                    pass
        date_range = None
        if dates:
            date_range = {
                "start": min(dates).isoformat(),
                "end": max(dates).isoformat(),
            }
        return MetricsSummary(
            total_events=total_events,
            event_types=event_types,
            dates=date_range,
            daily_unique_users_sum=daily_unique_users_sum,
        )
