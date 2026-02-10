from .permissions import router as permissions_router
from .resources import router as resources_router
from .sso_settings import router as sso_settings_router
from .sync_configs import router as sync_configs_router
from .users_roles_groups import router as users_roles_groups_router

ADMIN_MODULE_ROUTERS = (
    users_roles_groups_router,
    permissions_router,
    resources_router,
    sync_configs_router,
    sso_settings_router,
)

__all__ = ["ADMIN_MODULE_ROUTERS"]
