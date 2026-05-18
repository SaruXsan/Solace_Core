import { useEffect, useState } from "react";
import { enterpriseApi, type Branch, type Company } from "../api/enterprise";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

const emptyForm = {
  organization_id: "",
  name: "",
  code: "",
  city: "",
  is_active: true,
};

export default function BranchesPage() {
  const { can } = useAuth();
  const canManage = can("branches.update") || can("companies.manage");
  const [branches, setBranches] = useState<Branch[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editId, setEditId] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState(false);

  async function load() {
    const [b, c] = await Promise.all([enterpriseApi.branches.list(), enterpriseApi.companies.list()]);
    setBranches(b);
    setCompanies(c);
  }

  useEffect(() => {
    load();
  }, []);

  function notify(text: string, isError = false) {
    setMsg(text);
    setErr(isError);
  }

  function startEdit(b: Branch) {
    setEditId(b.id);
    setForm({
      organization_id: b.organization_id,
      name: b.name,
      code: b.code,
      city: b.city || "",
      is_active: b.is_active,
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
        name: form.name,
        code: form.code,
        city: form.city || null,
        is_active: form.is_active,
      };
      if (editId) {
        await enterpriseApi.branches.update(editId, body);
        notify("Branch updated");
      } else {
        await enterpriseApi.branches.create(body);
        notify("Branch created");
      }
      cancelEdit();
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Save failed", true);
    }
  }

  async function removeBranch(b: Branch) {
    const message =
      `Remove branch "${b.name}"?\n\n` +
      "The branch and its departments will be marked inactive (soft-deleted).";
    if (!confirm(message)) return;
    try {
      const result = await enterpriseApi.branches.deactivate(b.id);
      notify(
        `Branch removed.${result.departments_disabled ? ` ${result.departments_disabled} department(s) disabled.` : ""}`
      );
      if (editId === b.id) cancelEdit();
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Remove failed", true);
    }
  }

  return (
    <>
      <h1 className="page-title">Branches / Sites</h1>
      {msg && <p className={err ? "status-msg error" : "status-msg ok"}>{msg}</p>}
      {canManage && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>{editId ? "Edit branch" : "Add branch"}</h3>
          <div className="form-grid">
            <label className="form-field">
              Company
              <select
                value={form.organization_id}
                onChange={(e) => setForm({ ...form, organization_id: e.target.value })}
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
              Name
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label className="form-field">
              Code
              <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
            </label>
            <label className="form-field">
              City
              <input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
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
              <th>City</th>
              <th>Active</th>
              {canManage && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {branches.map((b) => (
              <tr key={b.id}>
                <td>{b.name}</td>
                <td>{b.code}</td>
                <td>{companies.find((c) => c.id === b.organization_id)?.name || "—"}</td>
                <td>{b.city || "—"}</td>
                <td>{b.is_active ? "Yes" : "No"}</td>
                {canManage && (
                  <td style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                    <button type="button" className="btn-secondary" onClick={() => startEdit(b)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ color: "var(--danger, #c44)" }}
                      onClick={() => removeBranch(b)}
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
