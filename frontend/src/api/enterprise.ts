import { api } from "./client";

export type Country = {
  id: string;
  name: string;
  code: string;
  default_language: string;
  is_enabled: boolean;
};

export type Company = {
  id: string;
  name: string;
  code: string;
  country_id?: string | null;
  legal_name?: string | null;
  commercial_name?: string | null;
  is_active: boolean;
};

export const enterpriseApi = {
  countries: {
    list: () => api<Country[]>("/countries"),
    create: (body: object) => api<Country>("/countries", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: object) =>
      api<Country>(`/countries/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  },
  companies: {
    list: () => api<Company[]>("/organizations/companies"),
    create: (body: object) =>
      api<Company>("/organizations/companies", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: object) =>
      api<Company>(`/organizations/companies/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  },
  branches: {
    list: (organization_id?: string) =>
      api<Record<string, unknown>[]>(
        `/organizations/branches${organization_id ? `?organization_id=${organization_id}` : ""}`
      ),
    create: (body: object) =>
      api("/organizations/branches", { method: "POST", body: JSON.stringify(body) }),
  },
  departments: {
    list: () => api<Record<string, unknown>[]>("/organizations/departments"),
    create: (body: object) =>
      api("/organizations/departments", { method: "POST", body: JSON.stringify(body) }),
  },
  userScopes: {
    list: (user_id?: string) =>
      api<Record<string, unknown>[]>(`/scopes/users${user_id ? `?user_id=${user_id}` : ""}`),
    assign: (body: object) => api("/scopes/users", { method: "POST", body: JSON.stringify(body) }),
  },
  consolidationScopes: {
    list: (user_id?: string) =>
      api<Record<string, unknown>[]>(
        `/consolidation/scopes${user_id ? `?user_id=${user_id}` : ""}`
      ),
    create: (body: object) =>
      api<Record<string, unknown>>("/consolidation/scopes", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    update: (id: string, body: object) =>
      api<Record<string, unknown>>(`/consolidation/scopes/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
  },
};
