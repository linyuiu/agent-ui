from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..api import register_routes
from ..config import settings
from ..migrations import ensure_schema


def create_app() -> FastAPI:
    app = FastAPI(title="Agent-UI")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS or ["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup() -> None:
        ensure_schema()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    register_routes(app)
    return app
