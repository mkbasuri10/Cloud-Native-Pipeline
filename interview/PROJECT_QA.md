# DataFlow Analytics — Project Q&A

This is a concise, comprehensive Q&A that explains the architecture, data flow, and how to run and test the project locally.

## Overview

**Q: What problem does this project solve?**  
A: It builds a cloud‑native data pipeline that transforms customer interaction logs into analytics metrics, stores them in S3‑compatible object storage, and exposes analytics plus a RAG‑style document search via a FastAPI service.

**Q: What are the main capabilities?**  
A: PySpark batch transforms, S3 storage integration (mocked locally with moto), FastAPI analytics endpoints, and a retrieval‑enhanced document search over operational docs.

## Data Flow and Architecture

**Q: What is the end‑to‑end data flow?**  
A: Raw JSONL events → PySpark aggregation (daily metrics) → JSONL upload to S3 → FastAPI reads metrics for analytics → Document Store indexes markdown docs for search → API serves analytics + doc search.

**Q: Where are raw events stored?**  
A: Locally at `dataflow_analytics/data/raw/events.jsonl` for development. The path is configurable via `DFA_RAW_EVENTS_PATH`.

**Q: What does the Spark job produce?**  
A: A daily aggregate table grouped by `event_date` and `event_type` with `event_count` and approximate `unique_users`.

**Q: How is S3 used without a real AWS account?**  
A: The `moto` library mocks S3 in‑memory. When `DFA_S3_USE_MOCK=1`, all S3 operations are local.

## Components

**Q: What are the core components?**  
A:
- **PySpark job** (`dataflow_analytics/jobs/transform_events.py`) for aggregations.
- **S3 storage wrapper** (`dataflow_analytics/storage.py`) for object uploads/downloads.
- **Analytics service** (`dataflow_analytics/analytics.py`) for summary metrics.
- **Document store** (`dataflow_analytics/rag.py`) for TF‑IDF search.
- **FastAPI app** (`dataflow_analytics/api/app.py`) for serving metrics and search results.

**Q: How does the document search work?**  
A: Markdown files are indexed with TF‑IDF. Queries are scored with cosine similarity and return top‑K matches plus snippets.

**Q: What endpoints are available?**  
A:
- `GET /health`
- `GET /analytics/metrics`
- `GET /analytics/summary`
- `GET /docs`
- `GET /docs/search?q=...&k=...`

## Running Locally

**Q: How do I run the pipeline end‑to‑end?**  
A:
1) Create/activate venv and install deps.  
2) Run the Spark transform (uploads to mocked S3).  
3) Start the FastAPI server and call endpoints.

**Q: What are the exact commands?**  
A:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[local,test]"

export DFA_S3_USE_MOCK=1
python -m dataflow_analytics.jobs.transform_events \
  --input dataflow_analytics/data/raw/events.jsonl

python -m dataflow_analytics.api.app
```

## Testing

**Q: How do I run tests?**  
A: `pytest`

**Q: What do tests cover?**  
A:
- Spark job correctness and S3 uploads (mocked)
- API endpoints for analytics + document search

## Configuration

**Q: What configuration is available?**  
A: All settings are in `dataflow_analytics/config.py` and can be overridden via `DFA_` environment variables (e.g., `DFA_S3_BUCKET`, `DFA_S3_PREFIX`, `DFA_S3_USE_MOCK`).

**Q: How do I use a real S3 bucket?**  
A: Set `DFA_S3_USE_MOCK=0`, configure `DFA_S3_BUCKET`, and provide AWS credentials in your environment. Optionally set `DFA_S3_ENDPOINT_URL` for S3‑compatible services.

## Troubleshooting

**Q: Spark fails with “getSubject is supported only if a security manager is allowed.”**  
A: On Java 21+, export:
```bash
export JAVA_TOOL_OPTIONS="-Djava.security.manager=allow"
```
Or use Java 17 and set `JAVA_HOME`.

**Q: Pylance can’t resolve imports.**  
A: Ensure your editor is using `.venv/bin/python` and dependencies are installed.

## Extending the Project

**Q: How do I add a new event field or metric?**  
A: Update the schema in `transform_events.py`, re-run the Spark job, and extend summary logic in `analytics.py`.

**Q: How do I add new documents for RAG search?**  
A: Drop new `.md` files into `dataflow_analytics/data/docs` and restart the API.

**Q: How do I add a new API endpoint?**  
A: Add a new FastAPI route in `dataflow_analytics/api/app.py` and update tests in `dataflow_analytics/tests`.

## Requirements Checklist

**Q: Does the project meet the original requirements?**  
A: Yes. It includes:
- PySpark transformation job for raw event data
- S3 storage integration with local mocking
- FastAPI endpoints for analytics
- RAG‑style document search over operational docs
- Fully local and testable workflow (no cloud required)
