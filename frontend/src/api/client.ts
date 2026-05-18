const API = "/api/v1";

/** Turn FastAPI error bodies into a readable message. */
export function formatApiError(data: unknown, status?: number): string {
  if (data && typeof data === "object") {
    const body = data as { detail?: unknown; message?: string };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      const parts = body.detail.map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          const loc = "loc" in item && Array.isArray(item.loc) ? item.loc.join(".") : "";
          return loc ? `${loc}: ${String((item as { msg: string }).msg)}` : String((item as { msg: string }).msg);
        }
        return String(item);
      });
      if (parts.length) return parts.join("; ");
    }
    if (typeof body.message === "string") return body.message;
  }
  if (status === 422) return "Invalid request — check required fields.";
  return "Request failed";
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("access_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(formatApiError(data, res.status));
  }
  return data as T;
}

type SetupDbResult = { success: boolean; message?: string };
type SetupCompleteResult = { message: string; organization_id?: string; admin_user_id?: string };

export const setupApi = {
  status: () => api<{ needs_setup: boolean; database_configured: boolean }>("/setup/status"),
  testDb: (body: object) =>
    api<SetupDbResult>("/setup/test-database", { method: "POST", body: JSON.stringify(body) }),
  saveDb: (body: object) =>
    api<SetupDbResult>("/setup/save-database", { method: "POST", body: JSON.stringify(body) }),
  runMigrations: () => api<SetupDbResult>("/setup/run-migrations", { method: "POST" }),
  complete: (body: object) =>
    api<SetupCompleteResult>("/setup/complete", { method: "POST", body: JSON.stringify(body) }),
};

export const authApi = {
  login: (body: object) =>
    api<{
      access_token: string;
      mfa_required?: boolean;
      challenge_id?: string;
      destination_masked?: string;
      expires_at?: string;
    }>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  mfaVerify: (body: { challenge_id: string; otp: string }) =>
    api<{ access_token: string }>("/auth/mfa/verify", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  mfaResend: (body: { challenge_id: string }) =>
    api<{ cooldown_seconds_remaining: number; expired: boolean; attempts_remaining: number }>(
      "/auth/mfa/resend",
      { method: "POST", body: JSON.stringify(body) }
    ),
  mfaStatus: (challengeId: string) =>
    api<{
      cooldown_seconds_remaining: number;
      expired: boolean;
      attempts_remaining: number;
      destination_masked: string;
    }>(`/auth/mfa/challenge/${challengeId}/status`),
  me: () =>
    api<{
      id: string;
      username: string;
      email: string;
      display_name: string;
      is_admin: boolean;
      organization_id: string;
      permissions?: string[];
      active_scope?: ActiveScope | null;
      available_scopes?: ActiveScope[];
      active_consolidation_scope?: ConsolidationScope | null;
      available_consolidation_scopes?: ConsolidationScope[];
    }>("/auth/me"),
  availableScopes: () => api<ActiveScope[]>("/auth/available-scopes"),
  switchConsolidationScope: (consolidation_scope_id: string | null) =>
    api<{ active_consolidation_scope: ConsolidationScope | null }>(
      "/auth/switch-consolidation-scope",
      { method: "POST", body: JSON.stringify({ consolidation_scope_id }) }
    ),
  activeConsolidationScope: () =>
    api<{ active_consolidation_scope: ConsolidationScope | null }>(
      "/auth/active-consolidation-scope"
    ),
  switchScope: (body: {
    scope_type: string;
    country_id?: string;
    organization_id?: string;
    branch_id?: string;
    department_id?: string;
  }) =>
    api<{ access_token: string; token_type: string; active_scope: ActiveScope }>(
      "/auth/switch-scope",
      { method: "POST", body: JSON.stringify(body) }
    ),
  logout: () => api<{ success: boolean }>("/auth/logout", { method: "POST" }),
};

export type ActiveScope = {
  scope_type: string;
  country_id?: string | null;
  organization_id?: string | null;
  branch_id?: string | null;
  department_id?: string | null;
  label?: string | null;
};

export type ConsolidationScope = {
  id: string;
  name?: string;
  scope_level: string;
  country_id?: string | null;
  organization_id?: string | null;
  branch_id?: string | null;
  department_id?: string | null;
  max_classification_allowed?: string | null;
  label?: string | null;
};
