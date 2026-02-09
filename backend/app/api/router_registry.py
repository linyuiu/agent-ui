from fastapi import FastAPI

from . import admin, agent_groups, agents, auth, chat_proxy, dashboard, demo, models

API_ROUTERS = (
    auth.router,
    chat_proxy.router,
    admin.router,
    dashboard.router,
    agents.router,
    models.router,
    demo.router,
    agent_groups.router,
)


def include_api_routers(app: FastAPI) -> None:
    for router in API_ROUTERS:
        app.include_router(router)
