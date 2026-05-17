import { useEffect, useState } from "react";
import { enterpriseApi } from "../api/enterprise";
import { usersApi } from "../api/platform";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

export default function UserScopesPage() {
  const { can } = useAuth();
  const [scopes, setScopes] = useState<Record<string, unknown>[]>([]);
  const [users, setUsers] = useState<{ id: string; username: string }[]>([]);
  const [form, setForm] = useState({
    user_id: "",
    scope_type: "organization",
    organization_id: "",
    is_default: false,
  });
  const [msg, setMsg] = useState("");

  async function load() {
    setScopes(await enterpriseApi.userScopes.list());
    const u = await usersApi.list();
    setUsers(u.map((x) => ({ id: x.id, username: x.username })));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <h1 className="page-title">User Scope Assignments</h1>
      <p className="status-msg">Controls which companies and levels a user may access and switch to.</p>
      {msg && <p className="status-msg ok">{msg}</p>}
      {can("user_scopes.manage") && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Assign scope</h3>
          <div className="form-grid">
            <div className="form-field">
              <label>User</label>
              <select value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })}>
                <option value="">Select...</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.username}</option>
                ))}
              </select>
            </div>
            <div className="form-field">
              <label>Scope type</label>
              <select value={form.scope_type} onChange={(e) => setForm({ ...form, scope_type: e.target.value })}>
                <option value="global">global</option>
                <option value="organization">organization</option>
                <option value="branch">branch</option>
                <option value="department">department</option>
              </select>
            </div>
            <div className="form-field">
              <label>Company ID</label>
              <input value={form.organization_id} onChange={(e) => setForm({ ...form, organization_id: e.target.value })} />
            </div>
          </div>
          <button
            type="button"
            className="btn-primary"
            onClick={async () => {
              await enterpriseApi.userScopes.assign({
                user_id: form.user_id,
                scope_type: form.scope_type,
                organization_id: form.organization_id || null,
                is_default: form.is_default,
              });
              setMsg("Scope assigned");
              await load();
            }}
          >
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
              <th>Default</th>
            </tr>
          </thead>
          <tbody>
            {scopes.map((s) => (
              <tr key={String(s.id)}>
                <td>{String(s.scope_type)}</td>
                <td>{String(s.user_id)}</td>
                <td>{s.organization_id ? String(s.organization_id) : "—"}</td>
                <td>{s.is_default ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
