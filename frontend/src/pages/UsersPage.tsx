import { useEffect, useState } from "react";
import { securityApi, usersApi, type OrgStructure, type UserInput, type UserRow } from "../api/platform";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

const emptyUser: UserInput = {
  username: "",
  email: "",
  display_name: "",
  password: "",
  mfa_enabled: false,
  is_admin: false,
  is_service_account: false,
  is_privileged_account: false,
  role_ids: [],
};

export default function UsersPage() {
  const { can } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [structure, setStructure] = useState<OrgStructure | null>(null);
  const [modal, setModal] = useState<"create" | "edit" | null>(null);
  const [form, setForm] = useState<UserInput & { id?: string; is_active?: boolean }>(emptyUser);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [breakGlass, setBreakGlass] = useState<{ id: string; username: string }[]>([]);

  async function load() {
    try {
      setUsers(await usersApi.list());
      setStructure(await usersApi.structure());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load users");
    }
  }

  useEffect(() => {
    load();
    if (can("security.readiness")) {
      securityApi.breakGlassUsers().then(setBreakGlass).catch(() => setBreakGlass([]));
    }
  }, []);

  function openCreate() {
    setForm(emptyUser);
    setModal("create");
  }

  function openEdit(u: UserRow) {
    setForm({
      id: u.id,
      username: u.username,
      email: u.email,
      display_name: u.display_name,
      is_active: u.is_active,
      is_admin: u.is_admin,
      is_service_account: u.is_service_account,
      is_privileged_account: u.is_privileged_account,
      mfa_enabled: u.mfa_enabled,
      branch_id: u.branch_id,
      department_id: u.department_id,
      role_ids: u.role_ids,
    });
    setModal("edit");
  }

  async function save() {
    try {
      if (modal === "create") {
        await usersApi.create(form);
        setMsg("User created");
      } else if (form.id) {
        await usersApi.update(form.id, {
          email: form.email,
          display_name: form.display_name,
          password: form.password || undefined,
          is_active: form.is_active,
          is_admin: form.is_admin,
          is_service_account: form.is_service_account,
          is_privileged_account: form.is_privileged_account,
          mfa_enabled: form.mfa_enabled,
          branch_id: form.branch_id,
          department_id: form.department_id,
          role_ids: form.role_ids,
        });
        setMsg("User updated");
      }
      setModal(null);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    }
  }

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className="page-title">Users</h1>
        {can("users.create") && (
          <button className="btn-primary" onClick={openCreate}>Create user</button>
        )}
      </div>
      {msg && <p className="status-msg ok">{msg}</p>}
      {err && <p className="status-msg error">{err}</p>}

      {breakGlass.length > 0 && (
        <div className="card" style={{ marginTop: "1rem", borderColor: "var(--warn, #c90)" }}>
          <h3>Break-glass administrators</h3>
          <p className="status-msg warn">
            {breakGlass.map((u) => u.username).join(", ")} still use is_admin wildcard (no roles). Assign
            system_administrator and remove reliance on wildcard access.
          </p>
        </div>
      )}

      <div className="card" style={{ marginTop: "1rem" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Display name</th>
              <th>Email</th>
              <th>Auth</th>
              <th>Status</th>
              <th>Flags</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.display_name}</td>
                <td>{u.email}</td>
                <td><span className="badge">{u.directory_source}</span></td>
                <td><span className={`badge ${u.is_active ? "ok" : "off"}`}>{u.is_active ? "Active" : "Disabled"}</span></td>
                <td>
                  {u.is_admin && <span className="badge warn">Admin</span>}{" "}
                  {u.mfa_enabled && <span className="badge">MFA</span>}{" "}
                  {u.is_privileged_account && <span className="badge warn">Privileged</span>}
                </td>
                <td>
                  {can("users.update") ? (
                    <button className="btn-secondary" onClick={() => openEdit(u)}>Edit</button>
                  ) : (
                    <span className="status-msg" title="Requires users.update">¡ª</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modal && (
        <div className="modal-backdrop" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{modal === "create" ? "Create user" : "Edit user"}</h2>
            <div className="form-grid">
              {modal === "create" && (
                <div className="form-field"><label>Username</label><input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></div>
              )}
              <div className="form-field"><label>Email</label><input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
              <div className="form-field"><label>Display name</label><input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} /></div>
              <div className="form-field"><label>{modal === "create" ? "Password" : "New password (optional)"}</label><input type="password" value={form.password || ""} onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
              {structure && (
                <>
                  <div className="form-field">
                    <label>Branch</label>
                    <select value={form.branch_id || ""} onChange={(e) => setForm({ ...form, branch_id: e.target.value || undefined })}>
                      <option value="">¡ª</option>
                      {structure.branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                    </select>
                  </div>
                  <div className="form-field">
                    <label>Department</label>
                    <select value={form.department_id || ""} onChange={(e) => setForm({ ...form, department_id: e.target.value || undefined })}>
                      <option value="">¡ª</option>
                      {structure.departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                    </select>
                  </div>
                  <div className="form-field full-width">
                    <label>Roles</label>
                    <select multiple value={form.role_ids || []} onChange={(e) => setForm({ ...form, role_ids: Array.from(e.target.selectedOptions, (o) => o.value) })}>
                      {structure.roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                  </div>
                </>
              )}
              <div className="form-field"><label><input type="checkbox" checked={form.is_active !== false} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Active</label></div>
              <div className="form-field">
                <label><input type="checkbox" checked={form.is_admin} onChange={(e) => setForm({ ...form, is_admin: e.target.checked })} /> Admin</label>
                {form.is_admin && (!form.role_ids || form.role_ids.length === 0) && (
                  <p className="status-msg warn" style={{ marginTop: "0.5rem" }}>
                    Admin without roles uses break-glass wildcard. Assign system_administrator for production.
                  </p>
                )}
              </div>
              <div className="form-field"><label><input type="checkbox" checked={form.mfa_enabled} onChange={(e) => setForm({ ...form, mfa_enabled: e.target.checked })} /> MFA enabled</label></div>
              <div className="form-field"><label><input type="checkbox" checked={form.is_privileged_account} onChange={(e) => setForm({ ...form, is_privileged_account: e.target.checked })} /> Privileged account</label></div>
              <div className="form-field"><label><input type="checkbox" checked={form.is_service_account} onChange={(e) => setForm({ ...form, is_service_account: e.target.checked })} /> Service account</label></div>
            </div>
            <div className="form-actions">
              <button className="btn-primary" onClick={save}>Save</button>
              <button className="btn-secondary" onClick={() => setModal(null)}>Cancel</button>
            </div>
            {modal === "edit" && form.id && can("mfa.manage") && (
              <div style={{ marginTop: "1.5rem", borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
                <h3 style={{ fontSize: "0.95rem" }}>MFA administration</h3>
                <div className="form-actions" style={{ flexWrap: "wrap" }}>
                  <button type="button" className="btn-secondary" onClick={async () => {
                    await securityApi.mfaResetCooldown(form.id!);
                    setMsg("MFA cooldown reset");
                  }}>Reset cooldown</button>
                  <button type="button" className="btn-secondary" onClick={async () => {
                    const r = await securityApi.mfaClearChallenges(form.id!);
                    setMsg(`Cleared ${r.cleared} challenge(s)`);
                  }}>Clear challenges</button>
                  <button type="button" className="btn-secondary" onClick={async () => {
                    const reason = prompt("Audit reason for temporary MFA disable (min 8 chars):");
                    if (!reason) return;
                    await securityApi.mfaTempDisable(form.id!, 8, reason);
                    setMsg("MFA temporarily disabled (8h)");
                  }}>Disable MFA 8h</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}


