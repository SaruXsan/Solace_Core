const API = "/api/v1";

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
    const detail = typeof data.detail === "string" ? data.detail : data.message;
    throw new Error(detail || "Request failed");
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
    api<{ access_token: string; mfa_required?: boolean; challenge_id?: string }>(
      "/auth/login",
      { method: "POST", body: JSON.stringify(body) }
    ),
  me: () =>
    api<{
      id: string;
      username: string;
      email: string;
      display_name: string;
      is_admin: boolean;
      permissions?: string[];
    }>("/auth/me"),
  logout: () => api<{ success: boolean }>("/auth/logout", { method: "POST" }),
};
