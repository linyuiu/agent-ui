from fastapi import FastAPI

from . import admin, agents, auth, dashboard, demo, models


def register_routes(app: FastAPI) -> None:
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(dashboard.router)
    app.include_router(agents.router)
    app.include_router(models.router)
    app.include_router(demo.router)
