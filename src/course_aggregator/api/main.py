"""Точка входу FastAPI із підтримкою Correlation ID та RFC 9457 помилок."""

import structlog
from course_aggregator.logging_conf import setup_logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from course_aggregator.api.routes import router
from course_aggregator.api.schemas import ProblemDetail
from course_aggregator.domain.exceptions import (
    EntityNotFoundError,
    ProgressRegressionError,
)
from course_aggregator.storage.database import Base, engine

setup_logging()
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Створення таблиць при запуску застосунку."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Course Aggregator API",
    description="REST API агрегатора онлайн-курсів за темами",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Прокидання Correlation ID та структуроване JSON-логування запиту."""
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)

    logger.info("request_started", method=request.method, client=request.client.host if request.client else "unknown")
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info("request_completed", status_code=response.status_code)
    return response


@app.exception_handler(ProgressRegressionError)
async def progress_regression_handler(
    request: Request, exc: ProgressRegressionError
) -> JSONResponse:
    """Обробка регресу прогресу (Критерій 2 ТЗ: статус 422)."""
    status_code = getattr(
        status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    problem = ProblemDetail(
        type="https://example.com/probs/progress-regression",
        title="Unprocessable Content - Progress Regression",
        status=status_code,
        detail=str(exc),
        instance=str(request.url),
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


@app.exception_handler(EntityNotFoundError)
async def not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
    """Обробка відсутності сутності (404 Not Found)."""
    problem = ProblemDetail(
        type="https://example.com/probs/not-found",
        title="Resource Not Found",
        status=status.HTTP_404_NOT_FOUND,
        detail=str(exc),
        instance=str(request.url),
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


@app.get("/healthz", tags=["Системні"])
async def health_check() -> dict[str, str]:
    """Перевірка доступності сервісу (Health Check)."""
    return {"status": "ok"}

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Глобальний перехоплювач помилок 500 без витоку системного стек-трейсу."""
    logger.error("internal_server_error", error=str(exc))
    problem = ProblemDetail(
        type="https://example.com/probs/internal-error",
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Виникла внутрішня помилка сервера. Спробуйте пізніше.",
        instance=str(request.url),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


app.include_router(router)