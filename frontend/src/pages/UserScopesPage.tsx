import { useEffect, useState } from "react";
import { enterpriseApi, type Company, type Country } from "../api/enterprise";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

export default function UserScopesPage() {
  const { can } = useAuth();
  const [scopes, setScopes] = useState<Record<string, unknown>[]>([]);
  const [users, setUsers] = useState<{ id: string; username: string }[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [form, setForm] = useState({
    user_id: "",
    scope_type: "organization",
    country_id: "",
    organization_id: "",
    is_default: false,
  });
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState(false);

  async function load() {
    try {
      const [s, u, c, co] = await Promise.all([
        enterpriseApi.userScopes.list(),
        enterpriseApi.userScopes.userOptions(),
        enterpriseApi.companies.list(),
        enterpriseApi.countries.list(),
      ]);
      setScopes(s);
      setUsers(
        u
          .filter((x) => !x.username.endsWith("$"))
          .map((x) => ({
            id: x.id,
            username: x.display_name ? `${x.username} — ${x.display_name}` : x.username,
          }))
      );
      setCompanies(c);
      setCountries(co.filter((x) => x.is_enabled));
    } catch (e) {
      notify(e instanceof Error ? e.message : "Failed to load", true);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function notify(text: string, isError = false) {
    setMsg(text);
    setErr(isError);
  }

  function validateForm(): string | null {
    if (!form.user_id) return "Select a user.";
    if (form.scope_type === "organization" && !form.organization_id) {
      return "Select a company for organization scope.";
    }
    if (form.scope_type === "country" && !form.country_id) {
      return "Select a country for country scope.";
    }
    return null;
  }

  async function assign() {
    const problem = validateForm();
    if (problem) {
      notify(problem, true);
      return;
    }
    try {
      await enterpriseApi.userScopes.assign({
        user_id: form.user_id,
        scope_type: form.scope_type,
        country_id: form.scope_type === "country" ? form.country_id : null,
        organization_id:
          form.scope_type === "organization" ? form.organization_id : null,
        is_default: form.is_default,
      });
      notify("Scope assigned");
      setForm({
        user_id: "",
        scope_type: "organization",
        country_id: "",
        organization_id: "",
        is_default: false,
      });
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Assign failed", true);
    }
  }

  const companyName = (id: unknown) =>
    companies.find((c) => c.id === id)?.name || (id ? String(id) : "—");
  const userName = (id: unknown) =>
    users.find((u) => u.id === id)?.username || (id ? String(id) : "—");

  return (
    <>
      <h1 className="page-title">User Scope Assignments</h1>
      <p className="status-msg">Controls which companies and levels a user may access and switch to.</p>
      <p className="status-msg">
        <strong>Preview Sync</strong> only shows what LDAP would import — it does not add users.
        You must click the orange <strong>Apply Sync</strong> button, then refresh this page.
        Check Platform → Users to confirm imports.
      </p>
      {users.length === 0 && (
        <p className="status-msg warn">
          No users loaded yet. If you only ran Preview Sync, run Apply Sync under Settings → LDAP,
          restart the API if you updated today, then refresh. Also open Platform → Users to verify
          the import.
        </p>
      )}
      {msg && <p className={err ? "status-msg error" : "status-msg ok"}>{msg}</p>}
      {can("user_scopes.manage") && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Assign scope</h3>
          <div className="form-grid">
            <label className="form-field">
              User
              <select value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })}>
                <option value="">Select...</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.username}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              Scope type
              <select
                value={form.scope_type}
                onChange={(e) =>
                  setForm({
                    ...form,
                    scope_type: e.target.value,
                    country_id: "",
                    organization_id: "",
                  })
                }
              >
                <option value="global">global</option>
                <option value="country">country</option>
                <option value="organization">organization</option>
              </select>
            </label>
            {form.scope_type === "country" && (
              <label className="form-field">
                Country
                <select
                  value={form.country_id}
                  onChange={(e) => setForm({ ...form, country_id: e.target.value })}
                >
                  <option value="">Select...</option>
                  {countries.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.code})
                    </option>
                  ))}
                </select>
              </label>
            )}
            {form.scope_type === "organization" && (
              <label className="form-field">
                Company
                <select
                  value={form.organization_id}
                  onChange={(e) => setForm({ ...form, organization_id: e.target.value })}
                >
                  <option value="">Select...</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.code})
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="form-field" style={{ alignSelf: "end" }}>
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
              />{" "}
              Default scope
            </label>
          </div>
          <p className="status-msg" style={{ marginTop: "0.5rem" }}>
            Branch and department scopes can be added via API; use global, country, or organization here.
          </p>
          <button type="button" className="btn-primary" onClick={assign}>
            Assign
          </button>
        </div>
      )}
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>User</th>
              <th>Company</th>
              <th>Country</th>
              <th>Default</th>
            </tr>
          </thead>
          <tbody>
            {scopes.map((s) => (
              <tr key={String(s.id)}>
                <td>{String(s.scope_type)}</td>
                <td>{userName(s.user_id)}</td>
                <td>{companyName(s.organization_id)}</td>
                <td>
                  {s.country_id
                    ? countries.find((c) => c.id === s.country_id)?.name || String(s.country_id)
                    : "—"}
                </td>
                <td>{s.is_default ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
