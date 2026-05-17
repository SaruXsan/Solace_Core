/** Route path → required permission(s). Authenticated users without a rule may access. */

export type RoutePermissionRule = string | string[];

export const ROUTE_PERMISSIONS: Record<string, RoutePermissionRule> = {
  "/": "dashboard.read",
  "/platform/users": "users.read",
  "/platform/roles": "roles.read",
  "/platform/organizations": ["organizations.read", "branches.read", "departments.read"],
  "/platform/countries": "countries.read",
  "/platform/companies": "companies.read",
  "/platform/branches": "branches.read",
  "/platform/departments": "departments.read",
  "/platform/user-scopes": "scopes.read",
  "/platform/modules": "modules.read",
  "/platform/settings": "settings.read",
  "/security/ldap": "ldap.read",
  "/security/mfa": "mfa.read",
  "/security/sessions": "sessions.read",
  "/security/login-attempts": "login_attempts.read",
  "/security/readiness": "security.readiness",
  "/solace/ai-providers": "ai_providers.read",
  "/solace/memory": "memory.read",
  "/solace/personas": "personas.read",
  "/solace/rem": "rem.read",
  "/solace/llm-calls": "logs.read",
  "/compliance/rfi": "compliance.read",
  "/compliance/controls": "compliance.read",
  "/compliance/evidence": "evidence.read",
  "/compliance/access-reviews": "compliance.read",
  "/compliance/incidents": "compliance.read",
  "/compliance/changes": "compliance.read",
  "/compliance/infra": "compliance.read",
  "/compliance/appsec": "compliance.read",
  "/compliance/redaction": "redaction.read",
  "/logs": ["audit.read", "logs.read"],
  "/logs/audit-trail": ["audit.read", "logs.read"],
  "/logs/login-events": "logs.read",
  "/logs/admin-actions": "logs.read",
  "/logs/config-changes": "logs.read",
  "/logs/permission-changes": "logs.read",
  "/logs/llm-calls": "logs.read",
  "/logs/posture-violations": "logs.read",
  "/logs/system-errors": "logs.read",
};

export function routeRequiresPermission(pathname: string): RoutePermissionRule | null {
  return ROUTE_PERMISSIONS[pathname] ?? null;
}
