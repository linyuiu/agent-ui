from fastapi import APIRouter

from .admin_modules.permissions import router as permissions_router
from .admin_modules.resources import router as resources_router
from .admin_modules.sync_configs import router as sync_configs_router
from .admin_modules.users_roles_groups import router as users_roles_groups_router

router = APIRouter(prefix="/admin", tags=["admin"])

router.include_router(users_roles_groups_router)
router.include_router(permissions_router)
router.include_router(resources_router)
router.include_router(sync_configs_router)
