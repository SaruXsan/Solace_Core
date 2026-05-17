import { useEffect, useState } from "react";
import { enterpriseApi, type Company, type Country } from "../api/enterprise";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

export default function CompaniesPage() {
  const { can } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [form, setForm] = useState({ name: "", code: "", country_id: "" });
  const [msg, setMsg] = useState("");

  async function load() {
    const [c, co] = await Promise.all([
      enterpriseApi.companies.list(),
      enterpriseApi.countries.list(),
    ]);
    setCompanies(c);
    setCountries(co);
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <h1 className="page-title">Companies / Legal Entities</h1>
      <p className="status-msg">
        Core_Organizations represents companies. The active company scope drives tenant isolation.
      </p>
      {msg && <p className="status-msg ok">{msg}</p>}
      {can("companies.manage") && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Add company</h3>
          <div className="form-grid">
            <div className="form-field"><label>Name</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="form-field"><label>Code</label><input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} /></div>
            <div className="form-field">
              <label>Country</label>
              <select value={form.country_id} onChange={(e) => setForm({ ...form, country_id: e.target.value })}>
                <option value="">—</option>
                {countries.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>
          <button
            type="button"
            className="btn-primary"
            onClick={async () => {
              await enterpriseApi.companies.create({ ...form, country_id: form.country_id || null });
              setMsg("Company created");
              await load();
            }}
          >
            Save
          </button>
        </div>
      )}
      <div className="card">
        <table className="data-table">
          <thead><tr><th>Name</th><th>Code</th><th>Country</th><th>Active</th></tr></thead>
          <tbody>
            {companies.map((o) => (
              <tr key={o.id}>
                <td>{o.commercial_name || o.name}</td>
                <td>{o.code}</td>
                <td>{countries.find((c) => c.id === o.country_id)?.name || "—"}</td>
                <td>{o.is_active ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
