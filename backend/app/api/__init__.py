from fastapi import FastAPI

from . import admin, agent_groups, agents, auth, chat_proxy, dashboard, demo, models


def register_routes(app: FastAPI) -> None:
    app.include_router(auth.router)
    app.include_router(chat_proxy.router)
    app.include_router(admin.router)
    app.include_router(dashboard.router)
    app.include_router(agents.router)
    app.include_router(models.router)
    app.include_router(demo.router)
    app.include_router(agent_groups.router)
