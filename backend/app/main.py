from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.logging_config import configure_logging
from app.middleware import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialise shared resources here (db engine, CV models, etc.)
    configure_logging()
    yield
    # Shutdown: clean up resources here


def create_app() -> FastAPI:
    app = FastAPI(title="FaceFolio", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
