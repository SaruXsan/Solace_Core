import { api } from "./client";

export type Country = {
  id: string;
  name: string;
  code: string;
  default_language: string;
  is_enabled: boolean;
};

export type CountryDeactivateResult = Country & {
  cascade?: boolean;
  companies_disabled?: number;
  branches_disabled?: number;
  departments_disabled?: number;
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

export type Branch = {
  id: string;
  organization_id: string;
  country_id?: string | null;
  name: string;
  code: string;
  branch_code?: string | null;
  branch_type?: string | null;
  address?: string | null;
  city?: string | null;
  region?: string | null;
  timezone?: string | null;
  is_active: boolean;
};

export type Department = {
  id: string;
  organization_id: string;
  branch_id?: string | null;
  parent_department_id?: string | null;
  manager_user_id?: string | null;
  name: string;
  code: string;
  is_active: boolean;
};

export const enterpriseApi = {
  countries: {
    list: () => api<Country[]>("/countries"),
    create: (body: object) => api<Country>("/countries", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: object) =>
      api<Country>(`/countries/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    deactivate: (id: string, cascade = true) =>
      api<CountryDeactivateResult>(`/countries/${id}?cascade=${cascade}`, { method: "DELETE" }),
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
      api<Branch[]>(
        `/organizations/branches${organization_id ? `?organization_id=${organization_id}` : ""}`
      ),
    create: (body: object) =>
      api<Branch>("/organizations/branches", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: object) =>
      api<Branch>(`/organizations/branches/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    deactivate: (id: string) =>
      api<Branch & { departments_disabled?: number }>(`/organizations/branches/${id}`, {
        method: "DELETE",
      }),
  },
  departments: {
    list: (organization_id?: string, branch_id?: string) => {
      const params = new URLSearchParams();
      if (organization_id) params.set("organization_id", organization_id);
      if (branch_id) params.set("branch_id", branch_id);
      const q = params.toString();
      return api<Department[]>(`/organizations/departments${q ? `?${q}` : ""}`);
    },
    create: (body: object) =>
      api<Department>("/organizations/departments", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: object) =>
      api<Department>(`/organizations/departments/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deactivate: (id: string) =>
      api<Department>(`/organizations/departments/${id}`, { method: "DELETE" }),
  },
  userScopes: {
    userOptions: () =>
      api<{ id: string; username: string; display_name: string; organization_id: string }[]>(
        "/scopes/user-options"
      ),
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
