"""Foundation permission catalog — single source of truth for RBAC codes."""

from __future__ import annotations

# (code, display name, module_code)
FOUNDATION_PERMISSIONS: list[tuple[str, str, str | None]] = [
    ("dashboard.read", "View Dashboard", "core"),
    ("users.read", "View Users", "core"),
    ("users.create", "Create Users", "core"),
    ("users.update", "Update Users", "core"),
    ("users.disable", "Disable Users", "core"),
    ("roles.read", "View Roles", "core"),
    ("roles.create", "Create Roles", "core"),
    ("roles.update", "Update Roles", "core"),
    ("permissions.manage", "Manage Permission Assignments", "core"),
    ("settings.read", "View Settings", "core"),
    ("settings.update", "Update Settings", "core"),
    ("ldap.read", "View LDAP Settings", "core"),
    ("ldap.update", "Update LDAP Settings", "core"),
    ("ldap.test", "Test LDAP Connection", "core"),
    ("mfa.read", "View MFA Settings", "core"),
    ("mfa.update", "Update MFA Settings", "core"),
    ("modules.read", "View Modules", "core"),
    ("modules.update", "Enable/Disable Modules", "core"),
    ("compliance.read", "View Compliance", "compliance"),
    ("compliance.update", "Update Compliance / RFI", "compliance"),
    ("evidence.read", "View Evidence", "compliance"),
    ("evidence.verify", "Verify Evidence Hash", "compliance"),
    ("redaction.read", "View Redaction Rules", "compliance"),
    ("redaction.test", "Test Redaction", "compliance"),
    ("audit.read", "View Audit Trail", "core"),
    ("logs.read", "View System Logs", "core"),
    ("ai_providers.read", "View AI Providers", "solace"),
    ("ai_providers.update", "Update AI Providers", "solace"),
    ("memory.read", "View Memory Atoms", "solace"),
    ("personas.read", "View Personas", "solace"),
    ("rem.read", "View REM Proposals", "solace"),
    ("organizations.read", "View Organizations", "core"),
    ("organizations.update", "Update Organizations", "core"),
    ("branches.read", "View Branches", "core"),
    ("branches.update", "Create/Update Branches", "core"),
    ("departments.read", "View Departments", "core"),
    ("departments.update", "Create/Update Departments", "core"),
]

ALL_PERMISSION_CODES: frozenset[str] = frozenset(c for c, _, _ in FOUNDATION_PERMISSIONS)

READ_ONLY_PERMISSIONS: frozenset[str] = frozenset(
    c for c in ALL_PERMISSION_CODES if c.endswith(".read") or c == "redaction.test"
)

COMPLIANCE_REVIEWER_PERMISSIONS: frozenset[str] = READ_ONLY_PERMISSIONS | frozenset(
    {"compliance.update", "evidence.verify"}
)

SECURITY_ADMIN_PERMISSIONS: frozenset[str] = READ_ONLY_PERMISSIONS | frozenset(
    {
        "settings.update",
        "ldap.update",
        "ldap.test",
        "mfa.update",
        "users.update",
        "users.disable",
        "roles.read",
        "roles.update",
        "permissions.manage",
        "modules.update",
        "ai_providers.update",
    }
)

STANDARD_USER_PERMISSIONS: frozenset[str] = frozenset(
    {"dashboard.read", "memory.read", "personas.read", "rem.read"}
)
