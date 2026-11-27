"""Worker app factory with the /health and /ready endpoints every worker must expose."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from pydantic import BaseModel


class ModelState:
    """Tracks whether the worker's model is loaded. Models load once at start-up, never per request."""

    def __init__(self) -> None:
        self.loaded = False
        self.model_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    model_id: str | None = None


ModelLoader = Callable[[ModelState], Awaitable[None]]


def create_worker_app(name: str, load_model: ModelLoader) -> FastAPI:
    state = ModelState()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await load_model(state)
        yield

    app = FastAPI(title=f"semraa-{name}-worker", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.model = state

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="alive")

    @app.get("/ready", response_model=HealthResponse)
    async def ready(response: Response) -> HealthResponse:
        if not state.loaded:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return HealthResponse(status="loading")
        return HealthResponse(status="ready", model_id=state.model_id)

    return app
