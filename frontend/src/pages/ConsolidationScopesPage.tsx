import { useEffect, useState } from "react";
import { enterpriseApi } from "../api/enterprise";
import { usersApi } from "../api/platform";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

const CLASSIFICATIONS = ["Public", "Internal", "Confidential", "Restricted", "Secret"];
const LEVELS = ["global", "country", "organization", "branch", "department"];

export default function ConsolidationScopesPage() {
  const { can } = useAuth();
  const [scopes, setScopes] = useState<Record<string, unknown>[]>([]);
  const [users, setUsers] = useState<{ id: string; username: string }[]>([]);
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({
    user_id: "",
    name: "",
    scope_level: "organization",
    organization_id: "",
    max_classification_allowed: "Internal",
    include_child_scopes: true,
    can_view_raw_restricted: false,
    can_use_ai_summary: false,
    can_export: false,
  });

  async function load() {
    setScopes(await enterpriseApi.consolidationScopes.list());
    const u = await usersApi.list();
    setUsers(u.map((x) => ({ id: x.id, username: x.username })));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <h1 className="page-title">Consolidation Scopes</h1>
      <p className="status-msg">
        Executive consolidation authority â€?separate from operational scope. Grants cross-entity
        reporting rights only when explicitly assigned.
      </p>
      {msg && <p className="status-msg ok">{msg}</p>}
      {can("consolidation.manage") && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Create consolidation scope</h3>
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
              <label>Name</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="form-field">
              <label>Scope level</label>
              <select
                value={form.scope_level}
                onChange={(e) => setForm({ ...form, scope_level: e.target.value })}
              >
                {LEVELS.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
            <div className="form-field">
              <label>Company ID</label>
              <input
                value={form.organization_id}
                onChange={(e) => setForm({ ...form, organization_id: e.target.value })}
              />
            </div>
            <div className="form-field">
              <label>Max classification</label>
              <select
                value={form.max_classification_allowed}
                onChange={(e) => setForm({ ...form, max_classification_allowed: e.target.value })}
              >
                {CLASSIFICATIONS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>
          <label>
            <input
              type="checkbox"
              checked={form.include_child_scopes}
              onChange={(e) => setForm({ ...form, include_child_scopes: e.target.checked })}
            />{" "}
            Include child scopes
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.can_view_raw_restricted}
              onChange={(e) => setForm({ ...form, can_view_raw_restricted: e.target.checked })}
            />{" "}
            Can view raw restricted
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.can_use_ai_summary}
              onChange={(e) => setForm({ ...form, can_use_ai_summary: e.target.checked })}
            />{" "}
            Can use AI summary (future)
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.can_export}
              onChange={(e) => setForm({ ...form, can_export: e.target.checked })}
            />{" "}
            Can export
          </label>
          <button
            type="button"
            className="btn-primary"
            style={{ marginTop: "0.75rem" }}
            onClick={async () => {
              await enterpriseApi.consolidationScopes.create({
                user_id: form.user_id,
                name: form.name,
                scope_level: form.scope_level,
                organization_id: form.organization_id || null,
                include_child_scopes: form.include_child_scopes,
                max_classification_allowed: form.max_classification_allowed,
                can_view_raw_restricted: form.can_view_raw_restricted,
                can_use_ai_summary: form.can_use_ai_summary,
                can_export: form.can_export,
              });
              setMsg("Consolidation scope created");
              await load();
            }}
          >
            Create
          </button>
        </div>
      )}
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>User</th>
              <th>Level</th>
              <th>Max class</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {scopes.map((s) => (
              <tr key={String(s.id)}>
                <td>{String(s.name)}</td>
                <td>{String(s.user_id)}</td>
                <td>{String(s.scope_level)}</td>
                <td>{String(s.max_classification_allowed)}</td>
                <td>{s.is_active ? "yes" : "no"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

