from __future__ import annotations

from pydantic import BaseModel, Field


class SystemSettingsOut(BaseModel):
    app_display_name: str
    environment_label: str
    session_timeout_minutes: int
    login_max_attempts: int
    login_lockout_minutes: int


class SystemSettingsIn(BaseModel):
    app_display_name: str | None = None
    environment_label: str | None = None
    session_timeout_minutes: int | None = None
    login_max_attempts: int | None = None
    login_lockout_minutes: int | None = None


class DatabaseStatusOut(BaseModel):
    configured: bool
    connected: bool
    server_hint: str | None = None
    database_name: str | None = None
    message: str | None = None


class SecuritySettingsOut(BaseModel):
    session_timeout_minutes: int
    login_max_attempts: int
    login_lockout_minutes: int


class MfaSettingsOut(BaseModel):
    enable_mfa: bool
    require_mfa_for_admins: bool
    otp_expiry_minutes: int
    otp_retry_limit: int
    resend_cooldown_seconds: int
    smtp_host: str | None
    smtp_port: int
    smtp_use_tls: bool
    smtp_username: str | None
    from_email: str | None
    has_smtp_password: bool
    smtp_password_masked: str | None = None


class MfaSettingsIn(BaseModel):
    enable_mfa: bool | None = None
    require_mfa_for_admins: bool | None = None
    otp_expiry_minutes: int | None = None
    otp_retry_limit: int | None = None
    resend_cooldown_seconds: int | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_use_tls: bool | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    from_email: str | None = None


class LdapSettingsOut(BaseModel):
    configured: bool
    directory_enabled: bool = False
    directory_type: str = "LDAPS"
    host: str | None = None
    port: int = 636
    use_ssl: bool = True
    use_starttls: bool = False
    bind_dn: str | None = None
    bind_username: str | None = None
    has_bind_password: bool = False
    bind_password_masked: str | None = None
    base_dn: str | None = None
    user_search_filter: str = "(sAMAccountName={username})"
    group_search_filter: str | None = None
    email_attribute: str = "mail"
    display_name_attribute: str = "displayName"
    department_attribute: str = "department"
    role_group_mapping: dict | list | None = None
    certificate_validation_enabled: bool = True
    allowed_certificate_thumbprints: str | None = None
    ca_chain_reference: str | None = None
    connection_timeout_seconds: int = 10
    plain_ldap_warning_acknowledged: bool = False
    overwrite_local_on_sync: bool = False
    production_warning: str | None = None


class LdapSettingsIn(BaseModel):
    directory_enabled: bool = False
    directory_type: str = "LDAPS"
    host: str | None = None
    port: int = 636
    use_ssl: bool = True
    use_starttls: bool = False
    bind_dn: str | None = None
    bind_username: str | None = None
    bind_password: str | None = None
    base_dn: str | None = None
    user_search_filter: str = "(sAMAccountName={username})"
    group_search_filter: str | None = None
    email_attribute: str = "mail"
    display_name_attribute: str = "displayName"
    department_attribute: str = "department"
    role_group_mapping: dict | list | None = None
    certificate_validation_enabled: bool = True
    allowed_certificate_thumbprints: str | None = None
    ca_chain_reference: str | None = None
    connection_timeout_seconds: int = 10
    plain_ldap_warning_acknowledged: bool = False
    overwrite_local_on_sync: bool = False


class LdapUserLookupIn(BaseModel):
    username: str = Field(min_length=1)


class AiProviderOut(BaseModel):
    provider_code: str
    display_name: str
    provider_type: str
    is_enabled: bool
    is_external: bool


class AiProviderUpdateIn(BaseModel):
    is_enabled: bool


class RedactionRuleOut(BaseModel):
    id: str
    pattern_name: str
    pattern_regex: str
    replacement: str
    is_active: bool


class RedactionRuleIn(BaseModel):
    pattern_name: str
    pattern_regex: str
    replacement: str = "[REDACTED]"
    is_active: bool = True
