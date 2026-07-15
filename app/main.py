from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialise shared resources here (db engine, CV models, etc.)
    yield
    # Shutdown: clean up resources here


def create_app() -> FastAPI:
    app = FastAPI(title="FaceFolio", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
