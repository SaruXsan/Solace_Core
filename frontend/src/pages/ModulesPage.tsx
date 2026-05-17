import { useEffect, useState } from "react";
import { modulesApi, type ModuleRow } from "../api/platform";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

export default function ModulesPage() {
  const { can } = useAuth();
  const [modules, setModules] = useState<ModuleRow[]>([]);
  const [msg, setMsg] = useState("");

  async function load() {
    setModules(await modulesApi.list());
  }

  useEffect(() => {
    load();
  }, []);

  async function toggleEnabled(m: ModuleRow) {
    if (m.is_placeholder && !m.enabled) {
      setMsg("Placeholder modules cannot be enabled until implemented.");
      return;
    }
    await modulesApi.update(m.id, { enabled: !m.enabled });
    setMsg(`${m.display_name} updated`);
    await load();
  }

  return (
    <>
      <h1 className="page-title">Module Registry</h1>
      {msg && <p className="status-msg ok">{msg}</p>}
      <p className="status-msg">Business modules are registered placeholders only — no business logic yet.</p>

      <div className="card" style={{ marginTop: "1rem" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Module</th>
              <th>Version</th>
              <th>Status</th>
              <th>Permissions</th>
              <th>Enabled</th>
            </tr>
          </thead>
          <tbody>
            {modules.map((m) => (
              <tr key={m.id}>
                <td>
                  <strong>{m.display_name}</strong>
                  <br />
                  <code style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{m.module_name}</code>
                </td>
                <td>{m.version}</td>
                <td>
                  {m.is_placeholder ? <span className="badge warn">Placeholder</span> : <span className="badge ok">Active</span>}
                </td>
                <td>{m.permissions.join(", ") || "—"}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={m.enabled}
                    disabled={m.is_placeholder || !can("modules.update")}
                    title={can("modules.update") ? undefined : "Requires modules.update"}
                    onChange={() => toggleEnabled(m)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
