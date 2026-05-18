import { useEffect, useState } from "react";
import { enterpriseApi, type Branch, type Company, type Department } from "../api/enterprise";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

const emptyForm = {
  organization_id: "",
  branch_id: "",
  name: "",
  code: "",
  is_active: true,
};

export default function DepartmentsPage() {
  const { can } = useAuth();
  const canManage = can("departments.update") || can("companies.manage");
  const [rows, setRows] = useState<Department[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editId, setEditId] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState(false);

  async function load() {
    const [d, c, b] = await Promise.all([
      enterpriseApi.departments.list(),
      enterpriseApi.companies.list(),
      enterpriseApi.branches.list(),
    ]);
    setRows(d);
    setCompanies(c);
    setBranches(b);
  }

  useEffect(() => {
    load();
  }, []);

  const branchesForCompany = branches.filter((b) => b.organization_id === form.organization_id);

  function notify(text: string, isError = false) {
    setMsg(text);
    setErr(isError);
  }

  function startEdit(d: Department) {
    setEditId(d.id);
    setForm({
      organization_id: d.organization_id,
      branch_id: d.branch_id || "",
      name: d.name,
      code: d.code,
      is_active: d.is_active,
    });
  }

  function cancelEdit() {
    setEditId(null);
    setForm(emptyForm);
  }

  async function save() {
    if (!form.organization_id) {
      notify("Select a company", true);
      return;
    }
    try {
      const body = {
        organization_id: form.organization_id,
        branch_id: form.branch_id || null,
        name: form.name,
        code: form.code,
        is_active: form.is_active,
      };
      if (editId) {
        await enterpriseApi.departments.update(editId, body);
        notify("Department updated");
      } else {
        await enterpriseApi.departments.create(body);
        notify("Department created");
      }
      cancelEdit();
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Save failed", true);
    }
  }

  async function removeDepartment(d: Department) {
    const message = `Remove department "${d.name}"?\n\nIt will be marked inactive (soft-deleted).`;
    if (!confirm(message)) return;
    try {
      await enterpriseApi.departments.deactivate(d.id);
      notify("Department removed");
      if (editId === d.id) cancelEdit();
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Remove failed", true);
    }
  }

  return (
    <>
      <h1 className="page-title">Departments / Business Units</h1>
      {msg && <p className={err ? "status-msg error" : "status-msg ok"}>{msg}</p>}
      {canManage && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>{editId ? "Edit department" : "Add department"}</h3>
          <div className="form-grid">
            <label className="form-field">
              Company
              <select
                value={form.organization_id}
                onChange={(e) =>
                  setForm({ ...form, organization_id: e.target.value, branch_id: "" })
                }
              >
                <option value="">— Select —</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              Branch (optional)
              <select
                value={form.branch_id}
                onChange={(e) => setForm({ ...form, branch_id: e.target.value })}
                disabled={!form.organization_id}
              >
                <option value="">— None —</option>
                {branchesForCompany.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field">
              Name
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label className="form-field">
              Code
              <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
            </label>
            <label className="form-field" style={{ alignSelf: "end" }}>
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              />{" "}
              Active
            </label>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
            <button type="button" className="btn-primary" onClick={save}>
              {editId ? "Update" : "Save"}
            </button>
            {editId && (
              <button type="button" className="btn-secondary" onClick={cancelEdit}>
                Cancel
              </button>
            )}
          </div>
        </div>
      )}
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Code</th>
              <th>Company</th>
              <th>Branch</th>
              <th>Active</th>
              {canManage && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.id}>
                <td>{d.name}</td>
                <td>{d.code}</td>
                <td>{companies.find((c) => c.id === d.organization_id)?.name || "—"}</td>
                <td>{branches.find((b) => b.id === d.branch_id)?.name || "—"}</td>
                <td>{d.is_active ? "Yes" : "No"}</td>
                {canManage && (
                  <td style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                    <button type="button" className="btn-secondary" onClick={() => startEdit(d)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ color: "var(--danger, #c44)" }}
                      onClick={() => removeDepartment(d)}
                    >
                      Remove
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
