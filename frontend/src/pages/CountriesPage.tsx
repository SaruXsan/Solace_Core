import { useEffect, useState } from "react";
import { enterpriseApi, type Country } from "../api/enterprise";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

export default function CountriesPage() {
  const { can } = useAuth();
  const [rows, setRows] = useState<Country[]>([]);
  const [form, setForm] = useState({ name: "", code: "", default_language: "en", is_enabled: true });
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState(false);

  async function load() {
    setRows(await enterpriseApi.countries.list());
  }

  useEffect(() => {
    load();
  }, []);

  function notify(text: string, isError = false) {
    setMsg(text);
    setErr(isError);
  }

  async function create() {
    try {
      await enterpriseApi.countries.create(form);
      notify("Country created");
      setForm({ name: "", code: "", default_language: "en", is_enabled: true });
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Create failed", true);
    }
  }

  async function toggleEnabled(c: Country) {
    try {
      await enterpriseApi.countries.update(c.id, { is_enabled: !c.is_enabled });
      notify(c.is_enabled ? "Country disabled" : "Country enabled");
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Update failed", true);
    }
  }

  async function removeCountry(c: Country) {
    const message =
      "Disable this country and cascade to all companies, branches, and departments under it?\n\n" +
      "Records are marked inactive (not permanently deleted). You can re-enable the country later; " +
      "child companies must be re-enabled separately.";
    if (!confirm(message)) return;
    try {
      const result = await enterpriseApi.countries.deactivate(c.id, true);
      notify(
        `Country disabled. Companies: ${result.companies_disabled ?? 0}, ` +
          `branches: ${result.branches_disabled ?? 0}, departments: ${result.departments_disabled ?? 0}.`
      );
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Remove failed", true);
    }
  }

  return (
    <>
      <h1 className="page-title">Countries / Jurisdictions</h1>
      <p className="status-msg">Legal and regulatory context for companies in the holding structure.</p>
      {msg && <p className={err ? "status-msg error" : "status-msg ok"}>{msg}</p>}
      {can("countries.manage") && (
        <AddCountryForm form={form} setForm={setForm} onSave={create} />
      )}
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Code</th>
              <th>Language</th>
              <th>Status</th>
              {can("countries.manage") && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.code}</td>
                <td>{c.default_language}</td>
                <td>{c.is_enabled ? "Enabled" : "Disabled"}</td>
                {can("countries.manage") && (
                  <td style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                    <button type="button" className="btn-secondary" onClick={() => toggleEnabled(c)}>
                      {c.is_enabled ? "Disable" : "Enable"}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ color: "var(--danger, #c44)" }}
                      onClick={() => removeCountry(c)}
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

function AddCountryForm({
  form,
  setForm,
  onSave,
}: {
  form: { name: string; code: string; default_language: string; is_enabled: boolean };
  setForm: (f: { name: string; code: string; default_language: string; is_enabled: boolean }) => void;
  onSave: () => void;
}) {
  return (
    <div className="card" style={{ marginBottom: "1rem" }}>
      <h3>Add country</h3>
      <div className="form-grid">
        <label className="form-field">
          Name
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label className="form-field">
          Code
          <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
        </label>
        <label className="form-field">
          Default language
          <input
            value={form.default_language}
            onChange={(e) => setForm({ ...form, default_language: e.target.value })}
          />
        </label>
        <label className="form-field" style={{ alignSelf: "end" }}>
          <input
            type="checkbox"
            checked={form.is_enabled}
            onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })}
          />{" "}
          Enabled on create
        </label>
      </div>
      <button type="button" className="btn-primary" onClick={onSave}>
        Save
      </button>
    </div>
  );
}