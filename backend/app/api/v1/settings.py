"""Platform settings endpoints.

Canonical LDAP/LDAPS routes: GET/PUT /settings/ldap, POST /settings/ldap/test-*.
Legacy api/v1/ldap.py was removed (unmounted duplicate).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_admin, require_permission
from app.models.platform import CoreUser
from app.models.solace_intel import SolaceAIProviderRegistry
from app.schemas.settings import (
    AiProviderOut,
    AiProviderUpdateIn,
    DatabaseStatusOut,
    LdapSettingsIn,
    LdapSettingsOut,
    LdapUserLookupIn,
    MfaSettingsIn,
    MfaSettingsOut,
    RedactionRuleIn,
    RedactionRuleOut,
    SecuritySettingsOut,
    SystemSettingsIn,
    SystemSettingsOut,
)
from app.services import (
    audit_service,
    compliance_service,
    ldap_service,
    ldap_sync_service,
    platform_settings_service,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/system", response_model=SystemSettingsOut)
def get_system(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("settings.read")),
):
    return platform_settings_service.get_system_settings(db)


@router.put("/system", response_model=SystemSettingsOut)
def put_system(
    body: SystemSettingsIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("settings.update")),
):
    platform_settings_service.update_system_settings(db, body.model_dump(exclude_unset=True))
    audit_service.log_config_change(db, admin.id, "system_settings", "System settings updated")
    db.commit()
    return platform_settings_service.get_system_settings(db)


@router.get("/database", response_model=DatabaseStatusOut)
def get_database_status(
    _user: CoreUser = Depends(require_permission("settings.read")),
):
    return platform_settings_service.get_database_status()


@router.post("/database/test")
def test_database(
    _user: CoreUser = Depends(require_permission("settings.read")),
):
    status = platform_settings_service.get_database_status()
    return {"success": status.get("connected", False), "message": status.get("message")}


@router.get("/security", response_model=SecuritySettingsOut)
def get_security(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("settings.read")),
):
    s = platform_settings_service.get_system_settings(db)
    return SecuritySettingsOut(
        session_timeout_minutes=s["session_timeout_minutes"],
        login_max_attempts=s["login_max_attempts"],
        login_lockout_minutes=s["login_lockout_minutes"],
    )


@router.get("/ldap", response_model=LdapSettingsOut)
def get_ldap(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("ldap.read")),
):
    return ldap_service.directory_settings_to_dict(ldap_service.get_directory_settings(db))


@router.put("/ldap")
def put_ldap(
    body: LdapSettingsIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("ldap.update")),
):
    if body.directory_type.upper() == "LDAP" and not body.use_ssl:
        if not body.plain_ldap_warning_acknowledged:
            return {
                "success": False,
                "warning": "Plain LDAP requires administrator acknowledgement.",
            }
    ldap_service.save_directory_settings(
        db, body.model_dump(), body.bind_password, changed_by=admin.id
    )
    db.commit()
    return {"success": True}


@router.post("/ldap/test-connection")
def ldap_test_connection(
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("ldap.test")),
):
    return ldap_service.test_connection(db, actor_id=admin.id)


@router.post("/ldap/test-user-lookup")
def ldap_test_user(
    body: LdapUserLookupIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("ldap.test")),
):
    return ldap_service.test_user_lookup(db, body.username, actor_id=admin.id)


class GroupRoleMappingIn(BaseModel):
    directory_group_dn: str
    role_id: str


class GroupRoleMappingsIn(BaseModel):
    mappings: list[GroupRoleMappingIn]


class GroupRolePreviewIn(BaseModel):
    groups: list[str]


@router.get("/ldap/group-mappings")
def get_ldap_group_mappings(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("ldap.read")),
):
    return ldap_service.list_group_role_mappings(db)


@router.put("/ldap/group-mappings")
def put_ldap_group_mappings(
    body: GroupRoleMappingsIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("ldap.update")),
):
    data = [m.model_dump() for m in body.mappings]
    result = ldap_service.save_group_role_mappings(db, data, actor_id=admin.id)
    db.commit()
    return result


@router.post("/ldap/preview-roles")
def preview_ldap_roles(
    body: GroupRolePreviewIn,
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("ldap.read")),
):
    return {"roles": ldap_service.preview_roles_for_groups(db, body.groups)}


@router.post("/ldap/sync/preview")
def ldap_sync_preview(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("ldap.sync")),
):
    return ldap_sync_service.preview_sync(db)


@router.post("/ldap/sync/apply")
def ldap_sync_apply(
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("ldap.sync")),
):
    result = ldap_sync_service.apply_sync(db, admin.id)
    db.commit()
    return result


@router.post("/ldap/sync/clear")
def ldap_sync_clear(
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("ldap.sync")),
):
    org, _row = ldap_sync_service._resolve_sync_organization(db)
    removed = ldap_sync_service.clear_imported_directory_users(db, org.id)
    audit_service.log_admin_action(
        db,
        admin.id,
        "ldap.sync_clear",
        target_type="directory",
        detail={"removed": removed, "organization_id": str(org.id)},
    )
    db.commit()
    return {"success": True, "removed": removed}


@router.post("/ldap/sync/clear-and-apply")
def ldap_sync_clear_and_apply(
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("ldap.sync")),
):
    org, _row = ldap_sync_service._resolve_sync_organization(db)
    cleared = ldap_sync_service.clear_imported_directory_users(db, org.id)
    result = ldap_sync_service.apply_sync(db, admin.id)
    result.setdefault("counts", {})["cleared"] = cleared
    audit_service.log_admin_action(
        db,
        admin.id,
        "ldap.sync_clear_and_apply",
        target_type="directory",
        detail=result.get("counts"),
    )
    db.commit()
    return result


class SmtpTestIn(BaseModel):
    to_email: EmailStr


@router.post("/mfa/test-smtp")
def test_smtp(
    body: SmtpTestIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("smtp.test")),
):
    result = platform_settings_service.test_smtp_email(db, body.to_email, actor_id=admin.id)
    db.commit()
    return result


@router.get("/mfa", response_model=MfaSettingsOut)
def get_mfa(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("mfa.read")),
):
    return platform_settings_service.get_mfa_settings(db)


@router.put("/mfa", response_model=MfaSettingsOut)
def put_mfa(
    body: MfaSettingsIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("mfa.update")),
):
    platform_settings_service.update_mfa_settings(
        db, body.model_dump(exclude_unset=True), updated_by=admin.id
    )
    audit_service.log_config_change(db, admin.id, "mfa_settings", "MFA/SMTP settings updated")
    db.commit()
    return platform_settings_service.get_mfa_settings(db)


@router.get("/ai-providers", response_model=list[AiProviderOut])
def get_ai_providers(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("ai_providers.read")),
):
    rows = db.scalars(
        select(SolaceAIProviderRegistry).order_by(SolaceAIProviderRegistry.display_name)
    ).all()
    return [
        AiProviderOut(
            provider_code=r.provider_code,
            display_name=r.display_name,
            provider_type=r.provider_type,
            is_enabled=r.is_enabled,
            is_external=r.is_external,
        )
        for r in rows
    ]


@router.patch("/ai-providers/{provider_code}")
def patch_ai_provider(
    provider_code: str,
    body: AiProviderUpdateIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("ai_providers.update")),
):
    row = db.scalar(
        select(SolaceAIProviderRegistry).where(
            SolaceAIProviderRegistry.provider_code == provider_code
        )
    )
    if not row:
        return {"success": False, "message": "Provider not found"}
    row.is_enabled = body.is_enabled
    audit_service.log_config_change(
        db, admin.id, f"ai_provider:{provider_code}", f"enabled={body.is_enabled}"
    )
    db.commit()
    return {"success": True}


@router.get("/redaction", response_model=list[RedactionRuleOut])
def get_redaction(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("redaction.read")),
):
    return compliance_service.list_redaction_rules(db)


@router.post("/redaction", response_model=RedactionRuleOut)
def post_redaction(
    body: RedactionRuleIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("settings.update")),
):
    row = compliance_service.create_redaction_rule(db, body.model_dump())
    audit_service.log_config_change(
        db, admin.id, "redaction_library", f"Added rule {body.pattern_name}"
    )
    db.commit()
    return row
