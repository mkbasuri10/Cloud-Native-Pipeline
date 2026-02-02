# Data Pipeline Overview

Raw event logs land in the raw bucket, then the PySpark transformer aggregates daily metrics by event type.
Aggregates are stored as JSONL and served by the analytics API.
Use the transformer daily at 02:00 UTC to keep the dashboard current.
