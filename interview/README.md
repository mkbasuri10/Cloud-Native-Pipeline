# DataFlow Analytics

Local-first data pipeline that transforms raw event logs with PySpark, stores aggregated metrics in an S3-compatible store (mocked with moto by default), and serves analytics plus a lightweight RAG-style document search via FastAPI.

## What this project does (end-to-end)

1. **Ingest raw events**: JSONL event logs are read from a local file.
2. **Transform and aggregate**: PySpark groups events by day and event type and calculates counts + approximate unique users.
3. **Store aggregates in S3**: The aggregated output is uploaded to S3 (mocked locally using moto).
4. **Serve analytics + docs search**: FastAPI exposes endpoints to fetch metrics and to search operational docs (RAG-style retrieval).

## Architecture overview

```mermaid
flowchart LR
    A[Raw Events JSONL] --> B[PySpark Transform Job]
    B --> C[Aggregates: metrics_by_day.jsonl]
    C --> D[S3 Storage (moto mock locally)]
    D --> E[Analytics Service]
    F[Operational Docs (Markdown)] --> G[Document Store / TF-IDF Index]
    E --> H[FastAPI API]
    G --> H
    H --> I[Clients: dashboards / BI / users]
```

### Data flow
- Raw JSONL events are transformed by the Spark job into daily aggregates.
- Aggregates are uploaded to S3-compatible storage (mocked locally).
- The API reads aggregates via the analytics service.
- Operational docs are indexed locally for retrieval (RAG-style search).
- Clients use the API to fetch metrics and query docs.

### Key features by component

**1) PySpark Transform**
- Batch aggregation by `event_date` + `event_type`.
- Calculates `event_count` and approximate `unique_users`.
- Output is a single JSONL object for easy loading.

**2) S3 Storage (mocked locally)**
- Uses boto3 with moto for local-only execution.
- No cloud credentials required.
- Stores aggregate file under `s3://{bucket}/{prefix}/metrics_by_day.jsonl`.

**3) Analytics Service**
- Loads JSONL from S3.
- Computes summary totals and date range.
- Keeps API response format stable and simple.

**4) Document Store (RAG-style)**
- Local Markdown docs are indexed with TF‑IDF.
- Returns top‑K matches with relevance score and snippet.

**5) FastAPI**
- Combines analytics + document retrieval.
- Provides health check and structured JSON responses.

## Components and responsibilities

### 1) Configuration (`dataflow_analytics/config.py`)
- Central settings object using `pydantic-settings`.
- Environment variables prefixed with `DFA_` override defaults.
- Key fields:
  - `DFA_S3_USE_MOCK` (default: `1` / true)
  - `DFA_S3_BUCKET`, `DFA_S3_PREFIX`, `DFA_S3_REGION`
  - `DFA_RAW_EVENTS_PATH`, `DFA_DOCS_DIR`, `DFA_TMP_DIR`

### 2) Storage layer (`dataflow_analytics/storage.py`)
- Wraps boto3 S3 client with convenient helpers.
- When `DFA_S3_USE_MOCK=1`, moto provides an in-memory S3 for local dev/tests.
- Responsibilities:
  - Ensure bucket exists
  - Upload/download text or files
  - Manage object key prefixes

### 3) Spark transformation job (`dataflow_analytics/jobs/transform_events.py`)
- Reads JSONL events.
- Adds `event_date` from the timestamp.
- Aggregates by `event_date` + `event_type`.
- Outputs JSON lines and uploads `metrics_by_day.jsonl` to S3.

### 4) Analytics service (`dataflow_analytics/analytics.py`)
- Loads `metrics_by_day.jsonl` from S3.
- Computes summary totals:
  - total events
  - event counts by type
  - date range
  - sum of daily unique users

### 5) RAG document search (`dataflow_analytics/rag.py`)
- Loads local Markdown docs.
- Builds a TF‑IDF index in memory.
- Ranks results by cosine similarity and returns snippets.

### 6) API layer (`dataflow_analytics/api/app.py`)
- FastAPI endpoints:
  - `GET /health`
  - `GET /analytics/metrics`
  - `GET /analytics/summary`
  - `GET /docs`
  - `GET /docs/search?q=...&k=...`
- Initializes storage + doc index on startup.

## Quick start (local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[local,test]"
```

Run the Spark transform and upload metrics to mocked S3:

```bash
export DFA_S3_USE_MOCK=1
python -m dataflow_analytics.jobs.transform_events \
  --input dataflow_analytics/data/raw/events.jsonl
```

Start the API:

```bash
export DFA_S3_USE_MOCK=1
python -m dataflow_analytics.api.app
```

Example requests:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/analytics/summary
curl "http://localhost:8000/docs/search?q=ingestion"
```

## Tests

```bash
pytest
```

## Notes

- The S3 layer uses `boto3` and is mocked with `moto` when `DFA_S3_USE_MOCK=1` (default).
- Spark runs in local mode (`local[*]`) so no external cluster is required.
- Aggregated metrics are stored as `metrics_by_day.jsonl` in the mocked S3 bucket/prefix.

## Troubleshooting

### Spark + Java 21 security manager error
If you see:
```
getSubject is supported only if a security manager is allowed
```
Set:
```bash
export JAVA_TOOL_OPTIONS="-Djava.security.manager=allow"
```
Then re-run the Spark job. Alternatively, use Java 17 and set `JAVA_HOME`.
