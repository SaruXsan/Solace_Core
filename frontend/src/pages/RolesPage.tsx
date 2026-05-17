import { useEffect, useState } from "react";
import { rolesApi, type Permission, type RoleInput, type RoleRow } from "../api/platform";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

export default function RolesPage() {
  const { can } = useAuth();
  const [roles, setRoles] = useState<RoleRow[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [modal, setModal] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<RoleInput>({ name: "", code: "", permission_ids: [] });
  const [msg, setMsg] = useState("");

  async function load() {
    setRoles(await rolesApi.list());
    setPermissions(await rolesApi.permissions());
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className="page-title">Roles & Permissions</h1>
        {can("roles.create") && (
          <button className="btn-primary" onClick={() => { setEditId(null); setForm({ name: "", code: "", permission_ids: [] }); setModal(true); }}>Create role</button>
        )}
      </div>
      {msg && <p className="status-msg ok">{msg}</p>}

      <div className="card" style={{ marginTop: "1rem" }}>
        <table className="data-table">
          <thead>
            <tr><th>Role</th><th>Code</th><th>MFA required</th><th>System</th><th>Permissions</th><th></th></tr>
          </thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td><code>{r.code}</code></td>
                <td>{r.requires_mfa ? "Yes" : "No"}</td>
                <td>{r.is_system_role ? <span className="badge warn">System</span> : "¡ª"}</td>
                <td>{r.permission_ids.length} assigned</td>
                <td>
                  {can("roles.update") && (
                    <button className="btn-secondary" onClick={() => {
                      setEditId(r.id);
                      setForm({ name: r.name, code: r.code, description: r.description, permission_ids: r.permission_ids });
                      setModal(true);
                    }}>Edit</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <h3 style={{ marginBottom: "0.75rem" }}>All permissions</h3>
        <table className="data-table">
          <thead><tr><th>Code</th><th>Name</th><th>Module</th></tr></thead>
          <tbody>
            {permissions.map((p) => (
              <tr key={p.id}><td><code>{p.code}</code></td><td>{p.name}</td><td>{p.module_code || "¡ª"}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      {modal && (
        <div className="modal-backdrop" onClick={() => setModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{editId ? "Edit role" : "Create role"}</h2>
            <div className="form-grid">
              <div className="form-field"><label>Name</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
              <div className="form-field"><label>Code</label><input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} /></div>
              <div className="form-field full-width">
                <label>Permissions</label>
                <select multiple value={form.permission_ids as string[]} onChange={(e) => setForm({ ...form, permission_ids: Array.from(e.target.selectedOptions, (o) => o.value) })}>
                  {permissions.map((p) => <option key={p.id} value={p.id}>{p.code}</option>)}
                </select>
              </div>
            </div>
            <div className="form-actions">
              <button className="btn-primary" onClick={async () => {
                if (editId) {
                  await rolesApi.update(editId, form);
                  setMsg("Role updated");
                } else {
                  await rolesApi.create(form);
                  setMsg("Role created");
                }
                setModal(false);
                await load();
              }}>Save</button>
              <button className="btn-secondary" onClick={() => setModal(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}


