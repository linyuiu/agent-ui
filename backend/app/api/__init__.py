from fastapi import FastAPI

from .router_registry import include_api_routers


def register_routes(app: FastAPI) -> None:
    include_api_routers(app)
