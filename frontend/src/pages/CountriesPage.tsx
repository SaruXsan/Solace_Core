import { useEffect, useState } from "react";
import { enterpriseApi, type Country } from "../api/enterprise";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

export default function CountriesPage() {
  const { can } = useAuth();
  const [rows, setRows] = useState<Country[]>([]);
  const [form, setForm] = useState({ name: "", code: "", default_language: "en", is_enabled: true });
  const [msg, setMsg] = useState("");

  async function load() {
    setRows(await enterpriseApi.countries.list());
  }

  useEffect(() => {
    load();
  }, []);

  async function create() {
    await enterpriseApi.countries.create(form);
    setMsg("Country created");
    setForm({ name: "", code: "", default_language: "en", is_enabled: true });
    await load();
  }

  return (
    <>
      <h1 className="page-title">Countries / Jurisdictions</h1>
      <p className="status-msg">Legal and regulatory context for companies in the holding structure.</p>
      {msg && <p className="status-msg ok">{msg}</p>}
      {can("countries.manage") && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Add country</h3>
          <div className="form-grid">
            <div className="form-field"><label>Name</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="form-field"><label>Code</label><input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} /></div>
            <div className="form-field"><label>Default language</label><input value={form.default_language} onChange={(e) => setForm({ ...form, default_language: e.target.value })} /></div>
          </div>
          <button type="button" className="btn-primary" onClick={create}>Save</button>
        </div>
      )}
      <div className="card">
        <table className="data-table">
          <thead><tr><th>Name</th><th>Code</th><th>Language</th><th>Enabled</th></tr></thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}><td>{c.name}</td><td>{c.code}</td><td>{c.default_language}</td><td>{c.is_enabled ? "Yes" : "No"}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
