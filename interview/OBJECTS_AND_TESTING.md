# DataFlow Analytics: Objects and Testing Guide

This document describes the main runtime objects in the DataFlow Analytics codebase and the steps to run the system and tests locally.

## Core objects and responsibilities

### Configuration
- `Settings` (`dataflow_analytics/config.py`)
  - Central config object using `pydantic-settings`.
  - Reads environment variables prefixed with `DFA_`.
  - Key fields:
    - `s3_bucket`, `s3_prefix`, `s3_region`, `s3_endpoint_url`, `s3_use_mock`
    - `raw_events_path`, `docs_dir`, `tmp_dir`

### Storage layer
- `S3Storage` (`dataflow_analytics/storage.py`)
  - Thin wrapper around boto3 S3 client with helper methods for uploads/downloads.
  - Handles mocked S3 via moto when `s3_use_mock=True`.
  - Key methods:
    - `ensure_bucket()` create bucket if missing
    - `key(name)` apply prefix
    - `upload_file(path, key)` upload local file
    - `upload_text(text, key)` upload raw string
    - `download_text(key)` read object as text
    - `upload_jsonl(rows, key)` write JSONL payload

- `start_moto()` / `stop_moto()` (`dataflow_analytics/storage.py`)
  - Global helpers to start/stop in-memory S3 emulator for local development/tests.

### Spark transformation job
- `build_spark()` (`dataflow_analytics/jobs/transform_events.py`)
  - Creates a local Spark session with UTC timezone.

- `transform_events()` (`dataflow_analytics/jobs/transform_events.py`)
  - Reads raw JSONL, extracts `event_date`, aggregates by date and event_type.
  - Outputs metrics: `event_count`, `unique_users` (approx distinct).

- `run_job()` (`dataflow_analytics/jobs/transform_events.py`)
  - Runs the transform, writes output JSON files, uploads merged JSONL to S3.

### Analytics domain
- `AnalyticsService` (`dataflow_analytics/analytics.py`)
  - Loads metrics from S3 (`metrics_by_day.jsonl`).
  - Computes summary rollups:
    - total events
    - event counts by type
    - date range
    - sum of daily unique users

### RAG document search
- `DocumentStore` (`dataflow_analytics/rag.py`)
  - Loads markdown docs from `docs_dir`.
  - Builds a TF-IDF index in memory.
  - `search(query, top_k)` returns ranked matches with snippets.

- `DocumentResult` (`dataflow_analytics/rag.py`)
  - Result schema: `doc_id`, `title`, `score`, `snippet`.

### API layer
- `create_app()` (`dataflow_analytics/api/app.py`)
  - FastAPI app factory.
  - Instantiates `AnalyticsService` + `DocumentStore` on startup.
  - Endpoints:
    - `GET /health`
    - `GET /analytics/metrics`
    - `GET /analytics/summary`
    - `GET /docs`
    - `GET /docs/search?q=...&k=...`

## Local environment setup

### 1) Create and activate venv
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -e ".[local,test]"
```

## Run the pipeline end-to-end (local)

### 1) Run Spark transform (uploads to mocked S3)
```bash
export DFA_S3_USE_MOCK=1
python -m dataflow_analytics.jobs.transform_events \
  --input dataflow_analytics/data/raw/events.jsonl
```

### 2) Start API
```bash
export DFA_S3_USE_MOCK=1
python -m dataflow_analytics.api.app
```

### 3) Call API endpoints
```bash
curl http://localhost:8000/health
curl http://localhost:8000/analytics/summary
curl "http://localhost:8000/docs/search?q=ingestion"
```

## Testing steps

### Run all tests
```bash
pytest
```

### What the tests cover
- `dataflow_analytics/tests/test_transform_events.py`
  - Creates sample JSONL events.
  - Runs the Spark transform.
  - Asserts aggregated counts and S3 upload in moto.

- `dataflow_analytics/tests/test_api.py`
  - Seeds mocked S3 metrics.
  - Spins up the FastAPI app with a temporary docs directory.
  - Validates analytics summary and doc search response.

### Common issues and fixes
- `pytest: command not found`
  - Ensure the venv is active and dependencies installed.

- Spark startup errors
  - Ensure Java is installed and `JAVA_HOME` is set.
  - Try re-running with a fresh venv.

- Empty `/analytics/summary`
  - Run the Spark transform first to populate `metrics_by_day.jsonl`.
  - Ensure `DFA_S3_USE_MOCK=1` when running both transform and API.
