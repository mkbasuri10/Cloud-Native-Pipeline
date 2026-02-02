from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

from dataflow_analytics.analytics import AnalyticsService, MetricsSummary
from dataflow_analytics.config import Settings, settings as default_settings
from dataflow_analytics.rag import DocumentStore, DocumentResult
from dataflow_analytics.storage import start_moto, stop_moto


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status.")


class AnalyticsMetricsResponse(BaseModel):
    metrics: list[dict[str, Any]] = Field(
        ..., description="Raw aggregated metrics loaded from metrics_by_day.jsonl."
    )


class AnalyticsSummaryResponse(BaseModel):
    total_events: int = Field(..., description="Sum of event_count across all days.")
    event_types: dict[str, int] = Field(
        ..., description="Aggregate event_count grouped by event_type."
    )
    date_range: dict[str, str] | None = Field(
        None, description="ISO date range covering available metrics."
    )
    daily_unique_users_sum: int = Field(
        ..., description="Sum of approximate unique users per day."
    )


class DocumentSearchResponse(BaseModel):
    query: str = Field(..., description="Search query string.")
    results: list[DocumentResult] = Field(
        ..., description="Top matching documents with relevance scores."
    )


class DocumentsListResponse(BaseModel):
    documents: list[str] = Field(..., description="Available document IDs.")


def create_app(cfg: Settings | None = None) -> FastAPI:
    cfg = cfg or default_settings
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if cfg.s3_use_mock:
            start_moto()
        app.state.analytics = AnalyticsService(cfg)
        app.state.docs = DocumentStore(cfg.docs_dir)
        yield
        if cfg.s3_use_mock:
            stop_moto()

    app = FastAPI(
        title="DataFlow Analytics API",
        version="0.1.0",
        description=(
            "API for aggregated analytics metrics and RAG-style operational document search. "
            "Uses S3-compatible storage (mocked locally) and a TF-IDF document index."
        ),
        contact={"name": "DataFlow Analytics"},
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "Service health and readiness."},
            {"name": "analytics", "description": "Aggregated metrics endpoints."},
            {"name": "docs", "description": "Operational document search endpoints."},
        ],
    )

    def get_analytics() -> AnalyticsService:
        return app.state.analytics

    def get_docs() -> DocumentStore:
        return app.state.docs

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["health"],
        summary="Health check",
        description="Simple health check endpoint to verify the service is running.",
    )
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/analytics/metrics",
        response_model=AnalyticsMetricsResponse,
        tags=["analytics"],
        summary="Raw metrics",
        description="Returns the raw aggregated metrics loaded from S3.",
    )
    def analytics_metrics(service: AnalyticsService = Depends(get_analytics)) -> AnalyticsMetricsResponse:
        return AnalyticsMetricsResponse(metrics=service.load_metrics())

    @app.get(
        "/analytics/summary",
        response_model=AnalyticsSummaryResponse,
        tags=["analytics"],
        summary="Summary metrics",
        description="Returns summarized metrics aggregated across all dates.",
    )
    def analytics_summary(service: AnalyticsService = Depends(get_analytics)) -> AnalyticsSummaryResponse:
        summary: MetricsSummary = service.summary()
        return AnalyticsSummaryResponse(
            total_events=summary.total_events,
            event_types=summary.event_types,
            date_range=summary.dates,
            daily_unique_users_sum=summary.daily_unique_users_sum,
        )

    @app.get(
        "/docs/search",
        response_model=DocumentSearchResponse,
        tags=["docs"],
        summary="Search documents",
        description="Search operational documentation using a TF-IDF index.",
    )
    def docs_search(
        q: str = Query(..., min_length=2),
        k: int = Query(3, ge=1, le=10),
        store: DocumentStore = Depends(get_docs),
    ) -> DocumentSearchResponse:
        results = store.search(q, top_k=k)
        return DocumentSearchResponse(query=q, results=results)

    @app.get(
        "/docs",
        response_model=DocumentsListResponse,
        tags=["docs"],
        summary="List documents",
        description="Lists all available operational document IDs.",
    )
    def docs_list(store: DocumentStore = Depends(get_docs)) -> DocumentsListResponse:
        return DocumentsListResponse(documents=[doc_id for doc_id, _ in store._documents])

    @app.exception_handler(Exception)
    def handle_errors(_, exc: Exception):
        return JSONResponse(status_code=500, content={"error": str(exc)})

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("dataflow_analytics.api.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
