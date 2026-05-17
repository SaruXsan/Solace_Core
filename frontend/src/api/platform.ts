import { api } from "./client";

export const settingsApi = {
  system: {
    get: () => api<SystemSettings>("/settings/system"),
    put: (body: Partial<SystemSettings>) =>
      api<SystemSettings>("/settings/system", { method: "PUT", body: JSON.stringify(body) }),
  },
  database: {
    get: () => api<DatabaseStatus>("/settings/database"),
    test: () => api<{ success: boolean; message?: string }>("/settings/database/test", { method: "POST" }),
  },
  security: {
    get: () => api<SecuritySettings>("/settings/security"),
  },
  ldap: {
    get: () => api<LdapSettings>("/settings/ldap"),
    put: (body: LdapSettingsInput) =>
      api<{ success: boolean; warning?: string }>("/settings/ldap", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    testConnection: () =>
      api<{ success: boolean; message: string; warnings?: string[] }>("/settings/ldap/test-connection", {
        method: "POST",
      }),
    testUser: (username: string) =>
      api<LdapUserLookupResult>("/settings/ldap/test-user-lookup", {
        method: "POST",
        body: JSON.stringify({ username }),
      }),
    groupMappings: {
      list: () => api<GroupRoleMapping[]>("/settings/ldap/group-mappings"),
      save: (mappings: { directory_group_dn: string; role_id: string }[]) =>
        api<GroupRoleMapping[]>("/settings/ldap/group-mappings", {
          method: "PUT",
          body: JSON.stringify({ mappings }),
        }),
    },
    previewRoles: (groups: string[]) =>
      api<{ roles: string[] }>("/settings/ldap/preview-roles", {
        method: "POST",
        body: JSON.stringify({ groups }),
      }),
    syncPreview: () => api<LdapSyncPreview>("/settings/ldap/sync/preview", { method: "POST" }),
    syncApply: () =>
      api<{ success: boolean; counts: Record<string, number> }>("/settings/ldap/sync/apply", {
        method: "POST",
      }),
  },
  mfa: {
    get: () => api<MfaSettings>("/settings/mfa"),
    put: (body: Partial<MfaSettingsInput>) =>
      api<MfaSettings>("/settings/mfa", { method: "PUT", body: JSON.stringify(body) }),
    testSmtp: (to_email: string) =>
      api<{ success: boolean; message: string }>("/settings/mfa/test-smtp", {
        method: "POST",
        body: JSON.stringify({ to_email }),
      }),
  },
  aiProviders: {
    list: () => api<AiProvider[]>("/settings/ai-providers"),
    patch: (code: string, is_enabled: boolean) =>
      api(`/settings/ai-providers/${code}`, {
        method: "PATCH",
        body: JSON.stringify({ is_enabled }),
      }),
  },
  redaction: {
    list: () => api<RedactionRule[]>("/settings/redaction"),
    create: (body: RedactionRuleInput) =>
      api<RedactionRule>("/settings/redaction", { method: "POST", body: JSON.stringify(body) }),
  },
};

export const usersApi = {
  structure: () => api<OrgStructure>("/users/structure"),
  list: () => api<UserRow[]>("/users"),
  get: (id: string) => api<UserRow>(`/users/${id}`),
  create: (body: UserInput) =>
    api<UserRow>("/users", { method: "POST", body: JSON.stringify(body) }),
  update: (id: string, body: Partial<UserInput>) =>
    api<UserRow>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
};

export const rolesApi = {
  permissions: () => api<Permission[]>("/roles/permissions"),
  list: () => api<RoleRow[]>("/roles"),
  create: (body: RoleInput) =>
    api<RoleRow>("/roles", { method: "POST", body: JSON.stringify(body) }),
  update: (id: string, body: Partial<RoleInput>) =>
    api<RoleRow>(`/roles/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
};

export const modulesApi = {
  list: () => api<ModuleRow[]>("/modules"),
  update: (id: string, body: { enabled?: boolean; description?: string }) =>
    api<ModuleRow>(`/modules/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
};

export const dashboardApi = {
  stats: () =>
    api<{
      total_users: number;
      active_users: number;
      locked_users: number;
      mfa_enabled_users: number;
      failed_logins_today: number;
      enabled_modules: number;
      evidence_records: number;
      open_incidents: number;
      ai_calls_today: number;
      system_health: { database_connected: boolean; setup_complete: boolean };
    }>("/dashboard/stats"),
};

export const complianceApi = {
  rfiSections: () => api<RfiSection[]>("/compliance/rfi/sections"),
  saveAnswer: (questionId: string, answer_text: string, status: string) =>
    api(`/compliance/rfi/questions/${questionId}/answer`, {
      method: "PUT",
      body: JSON.stringify({ answer_text, status }),
    }),
  evidence: () => api<EvidenceRow[]>("/compliance/evidence"),
  runAutoLinker: () =>
    api<{ created: number }>("/compliance/evidence/auto-linker/run", { method: "POST" }),
  verifyEvidence: (id: string) =>
    api<{ valid: boolean; message?: string }>(`/compliance/evidence/${id}/verify`, { method: "POST" }),
};

export const mfaApi = {
  createChallenge: (user_id: string) =>
    api<{ challenge_id: string; destination_masked: string }>("/mfa/challenges", {
      method: "POST",
      body: JSON.stringify({ user_id }),
    }),
  verify: (user_id: string, otp: string) =>
    api<{ success: boolean }>("/mfa/challenges/verify", {
      method: "POST",
      body: JSON.stringify({ user_id, otp }),
    }),
  resend: (user_id: string) =>
    api("/mfa/challenges/resend", { method: "POST", body: JSON.stringify({ user_id }) }),
};

export type SystemSettings = {
  app_display_name: string;
  environment_label: string;
  session_timeout_minutes: number;
  login_max_attempts: number;
  login_lockout_minutes: number;
};

export type DatabaseStatus = {
  configured: boolean;
  connected: boolean;
  server_hint?: string;
  database_name?: string;
  message?: string;
};

export type SecuritySettings = {
  session_timeout_minutes: number;
  login_max_attempts: number;
  login_lockout_minutes: number;
};

export type LdapSettings = {
  configured: boolean;
  directory_enabled?: boolean;
  directory_type?: string;
  host?: string;
  port?: number;
  use_ssl?: boolean;
  use_starttls?: boolean;
  bind_dn?: string;
  bind_username?: string;
  has_bind_password?: boolean;
  bind_password_masked?: string;
  base_dn?: string;
  user_search_filter?: string;
  group_search_filter?: string;
  email_attribute?: string;
  display_name_attribute?: string;
  department_attribute?: string;
  role_group_mapping?: unknown;
  certificate_validation_enabled?: boolean;
  connection_timeout_seconds?: number;
  plain_ldap_warning_acknowledged?: boolean;
  production_warning?: string;
};

export type LdapSettingsInput = LdapSettings & { bind_password?: string; overwrite_local_on_sync?: boolean };

export type LdapUserLookupResult = {
  found: boolean;
  username?: string;
  email?: string;
  display_name?: string;
  department?: string;
  directory_object_id?: string;
  groups?: string[];
  error?: string;
};

export type GroupRoleMapping = {
  id: string;
  directory_group_dn: string;
  role_id: string;
  role_code?: string;
  role_name?: string;
};

export type LdapSyncPreview = {
  created: { username: string; email?: string; roles?: string[] }[];
  updated: { username: string; email?: string; roles?: string[] }[];
  unchanged: { username: string }[];
  disabled: { username: string; reason?: string }[];
};

export type MfaSettings = {
  enable_mfa: boolean;
  require_mfa_for_admins: boolean;
  otp_expiry_minutes: number;
  otp_retry_limit: number;
  resend_cooldown_seconds: number;
  smtp_host?: string;
  smtp_port: number;
  smtp_use_tls: boolean;
  smtp_username?: string;
  from_email?: string;
  has_smtp_password: boolean;
  smtp_password_masked?: string;
};

export type MfaSettingsInput = MfaSettings & { smtp_password?: string };

export type AiProvider = {
  provider_code: string;
  display_name: string;
  provider_type: string;
  is_enabled: boolean;
  is_external: boolean;
};

export type RedactionRule = {
  id: string;
  pattern_name: string;
  pattern_regex: string;
  replacement: string;
  is_active: boolean;
};

export type RedactionRuleInput = {
  pattern_name: string;
  pattern_regex: string;
  replacement?: string;
};

export type UserRow = {
  id: string;
  username: string;
  email: string;
  display_name: string;
  is_active: boolean;
  is_admin: boolean;
  is_service_account: boolean;
  is_privileged_account: boolean;
  mfa_enabled: boolean;
  directory_source: string;
  organization_id: string;
  branch_id?: string;
  department_id?: string;
  role_ids: string[];
};

export type UserInput = {
  username: string;
  email: string;
  display_name: string;
  password?: string;
  branch_id?: string;
  department_id?: string;
  is_active?: boolean;
  is_admin?: boolean;
  is_service_account?: boolean;
  is_privileged_account?: boolean;
  mfa_enabled?: boolean;
  role_ids?: string[];
};

export type Permission = { id: string; code: string; name: string; module_code?: string };
export type RoleRow = {
  id: string;
  name: string;
  code: string;
  description?: string;
  requires_mfa: boolean;
  is_system_role: boolean;
  permission_ids: string[];
};
export type RoleInput = {
  name: string;
  code: string;
  description?: string;
  requires_mfa?: boolean;
  permission_ids?: string[];
};

export type ModuleRow = {
  id: string;
  module_name: string;
  display_name: string;
  version: string;
  description?: string;
  enabled: boolean;
  is_placeholder: boolean;
  permissions: string[];
};

export type OrgStructure = {
  organizations: { id: string; name: string; code: string }[];
  branches: { id: string; name: string; code: string; organization_id: string }[];
  departments: { id: string; name: string; code: string; organization_id: string; branch_id?: string }[];
  roles: { id: string; name: string; code: string }[];
};

export type RfiSection = {
  section: string;
  title: string;
  questions: {
    id: string;
    question_code: string;
    question_text: string;
    answer_text?: string;
    answer_status?: string;
  }[];
};

export type EvidenceRow = {
  id: string;
  title: string;
  control_id?: string;
  digital_signature_hash: string;
  created_at: string;
};

export type SecurityReadinessReport = {
  mfa_enabled_admins_count: number;
  total_admins_count: number;
  privileged_users_without_mfa: number;
  break_glass_users: {
    id: string;
    username: string;
    display_name: string;
    email: string;
    recommendation: string;
  }[];
  failed_logins_last_24h: number;
  locked_users_count: number;
  ldap: {
    enabled: boolean;
    directory_type?: string | null;
    plain_ldap_warning?: string | null;
  };
  smtp: { configured: boolean; host?: string | null };
  sessions: { active_count: number; revoked_last_24h: number };
  permission_denied_last_24h: number;
  encrypted_settings_vault: { reachable: boolean; smtp_password_stored: boolean };
};

export const securityApi = {
  readiness: () => api<SecurityReadinessReport>("/security/readiness"),
  breakGlassUsers: () =>
    api<SecurityReadinessReport["break_glass_users"]>("/security/break-glass-users"),
  ldapDiagnostics: (body?: { test_username?: string }) =>
    api<Record<string, unknown>>("/security/ldap/diagnostics", {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
  sessions: (params?: { user_id?: string; username?: string }) => {
    const q = new URLSearchParams();
    if (params?.user_id) q.set("user_id", params.user_id);
    if (params?.username) q.set("username", params.username);
    const qs = q.toString();
    return api<SessionRow[]>(`/security/sessions${qs ? `?${qs}` : ""}`);
  },
  revokeSession: (sessionId: string) =>
    api<{ success: boolean }>(`/security/sessions/${sessionId}/revoke`, { method: "POST" }),
  revokeAllSessions: (userId: string) =>
    api<{ success: boolean; revoked: number }>(`/security/sessions/revoke-all/${userId}`, {
      method: "POST",
    }),
  revokeCurrentSession: () =>
    api<{ success: boolean }>("/security/sessions/revoke-current", { method: "POST" }),
  revokeOtherSessions: () =>
    api<{ success: boolean; revoked: number }>("/security/sessions/revoke-others", {
      method: "POST",
    }),
  loginAttempts: (params?: {
    username?: string;
    success?: boolean;
    auth_source?: string;
    ip_address?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.username) q.set("username", params.username);
    if (params?.success !== undefined) q.set("success", String(params.success));
    if (params?.auth_source) q.set("auth_source", params.auth_source);
    if (params?.ip_address) q.set("ip_address", params.ip_address);
    const qs = q.toString();
    return api<LoginAttemptRow[]>(`/security/login-attempts${qs ? `?${qs}` : ""}`);
  },
  loginTrends: (hours = 24) =>
    api<{ hours: number; failed_by_hour: { hour: number; count: number }[] }>(
      `/security/login-attempts/trends?hours=${hours}`
    ),
  unlockUser: (user_id: string) =>
    api<{ success: boolean }>("/security/users/unlock", {
      method: "POST",
      body: JSON.stringify({ user_id }),
    }),
  mfaResetCooldown: (userId: string) =>
    api<{ success: boolean }>(`/security/users/${userId}/mfa/reset-cooldown`, { method: "POST" }),
  mfaClearChallenges: (userId: string) =>
    api<{ success: boolean; cleared: number }>(`/security/users/${userId}/mfa/clear-challenges`, {
      method: "POST",
    }),
  mfaTempDisable: (userId: string, hours: number, reason: string) =>
    api<{ success: boolean }>(`/security/users/${userId}/mfa/temporary-disable`, {
      method: "POST",
      body: JSON.stringify({ hours, reason }),
    }),
  mfaRequirePrivileged: (userId: string, required: boolean) =>
    api<{ success: boolean }>(
      `/security/users/${userId}/mfa/require-privileged?required=${required}`,
      { method: "POST" }
    ),
};

export type SessionRow = {
  id: string;
  user_id: string;
  username: string;
  display_name: string;
  ip_address?: string;
  user_agent?: string;
  created_at?: string;
  expires_at: string;
  is_current?: boolean;
  status?: string;
};

export type LoginAttemptRow = {
  id: string;
  username: string;
  ip_address?: string;
  success: boolean;
  auth_source: string;
  failure_reason?: string;
  created_at?: string;
};
