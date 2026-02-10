from fastapi import FastAPI

from . import admin, agent_groups, agents, auth, auth_sso, chat_proxy, dashboard, demo, models

API_ROUTERS = (
    auth.router,
    auth_sso.router,
    chat_proxy.router,
    admin.router,
    dashboard.router,
    agents.router,
    models.router,
    demo.router,
    agent_groups.router,
)


def register_routes(app: FastAPI) -> None:
    for router in API_ROUTERS:
        app.include_router(router)
