from fastapi import APIRouter

from .admin_modules import ADMIN_MODULE_ROUTERS

router = APIRouter(prefix="/admin", tags=["admin"])

for module_router in ADMIN_MODULE_ROUTERS:
    router.include_router(module_router)
