from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...auth import get_current_user
from ...db import get_db
from ...permissions import require_manage_menu_async, require_menu_action_async
from ...services.sso import (
    build_system_auth_setting_out,
    get_system_auth_setting_async,
    normalize_enabled_methods,
    normalize_login_method,
)

router = APIRouter(prefix="/sso/settings", tags=["admin_sso_settings"])

_METHOD_LABELS = {
    "local": "账号登录",
    "ldap": "LDAP",
    "cas": "CAS",
    "oidc": "OIDC",
    "oauth2": "OAuth2",
    "saml2": "SAML2",
}


@router.get("", response_model=schemas.SystemAuthSettingOut)
async def get_sso_settings(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.SystemAuthSettingOut:
    await require_menu_action_async(db, current_user, action="view", menu_id="admin")
    setting = await get_system_auth_setting_async(db)
    return build_system_auth_setting_out(setting)


@router.put("", response_model=schemas.SystemAuthSettingOut)
async def update_sso_settings(
    payload: schemas.SystemAuthSettingUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.SystemAuthSettingOut:
    await require_manage_menu_async(db, current_user)
    setting = await get_system_auth_setting_async(db)

    enabled_methods = normalize_enabled_methods(payload.enabled_methods)
    default_login_method = normalize_login_method(payload.default_login_method)
    if default_login_method not in enabled_methods:
        raise HTTPException(status_code=400, detail="默认登录方式必须在已启用的登录方式中")

    role_name = (payload.default_role or "user").strip() or "user"
    role_exists = (
        await db.execute(select(models.Role.id).where(models.Role.name == role_name))
    ).scalar_one_or_none()
    if role_exists is None:
        raise HTTPException(status_code=400, detail="默认角色不存在")

    external_methods = [item for item in enabled_methods if item != "local"]
    if external_methods:
        configured_protocols = set(
            (
                await db.execute(
                    select(models.AuthProviderConfig.protocol).where(
                        models.AuthProviderConfig.protocol.in_(external_methods)
                    )
                )
            ).scalars().all()
        )
        missing = [item for item in external_methods if item not in configured_protocols]
        if missing:
            missing_text = "、".join(_METHOD_LABELS.get(item, item.upper()) for item in missing)
            raise HTTPException(status_code=400, detail=f"请先在登录系统中保存 {missing_text} 配置")

    setting.enabled_methods = enabled_methods
    setting.default_login_method = default_login_method
    setting.auto_create_user = bool(payload.auto_create_user)
    setting.default_role = role_name

    await db.commit()
    await db.refresh(setting)
    return build_system_auth_setting_out(setting)
