import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

type OrgData = {
  organizations: { id: string; name: string; code: string }[];
  branches: { id: string; name: string; code: string; organization_id: string }[];
  departments: { id: string; name: string; code: string; organization_id: string }[];
};

export default function OrganizationsPage() {
  const { can } = useAuth();
  const [data, setData] = useState<OrgData | null>(null);
  const [branch, setBranch] = useState({ name: "", code: "", organization_id: "" });
  const [msg, setMsg] = useState("");

  async function load() {
    setData(await api<OrgData>("/organizations"));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <h1 className="page-title">Organizations & Branches</h1>
      {msg && <p className="status-msg ok">{msg}</p>}
      {data && (
        <>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3>Organizations</h3>
            <table className="data-table">
              <thead><tr><th>Name</th><th>Code</th></tr></thead>
              <tbody>
                {data.organizations.map((o) => (
                  <tr key={o.id}><td>{o.name}</td><td>{o.code}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3>Branches</h3>
            <table className="data-table">
              <thead><tr><th>Name</th><th>Code</th></tr></thead>
              <tbody>
                {data.branches.map((b) => (
                  <tr key={b.id}><td>{b.name}</td><td>{b.code}</td></tr>
                ))}
              </tbody>
            </table>
            <h4 style={{ marginTop: "1rem" }}>Add branch</h4>
            <div className="form-grid">
              <div className="form-field">
                <label>Organization</label>
                <select value={branch.organization_id} onChange={(e) => setBranch({ ...branch, organization_id: e.target.value })}>
                  <option value="">--</option>
                  {data.organizations.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
              </div>
              <div className="form-field"><label>Name</label><input value={branch.name} onChange={(e) => setBranch({ ...branch, name: e.target.value })} /></div>
              <div className="form-field"><label>Code</label><input value={branch.code} onChange={(e) => setBranch({ ...branch, code: e.target.value })} /></div>
            </div>
            <button className="btn-primary" style={{ marginTop: "0.5rem" }} disabled={!can("branches.update")} title={can("branches.update") ? undefined : "Requires branches.update"} onClick={async () => {
              await api("/organizations/branches", { method: "POST", body: JSON.stringify(branch) });
              setMsg("Branch created");
              load();
            }}>Add branch</button>
          </div>
          <div className="card">
            <h3>Departments</h3>
            <table className="data-table">
              <thead><tr><th>Name</th><th>Code</th></tr></thead>
              <tbody>
                {data.departments.map((d) => (
                  <tr key={d.id}><td>{d.name}</td><td>{d.code}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
