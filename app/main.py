from contextlib import asynccontextmanager

from fastapi import FastAPI


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

    return app


app = create_app()
