import { useEffect, useState } from "react";
import { api } from "../api/client";
import "../components/forms.css";

type Atom = {
  id: string;
  domain: string;
  category?: string;
  claim: string;
  data_classification: string;
};

export default function SolaceMemoryPage() {
  const [atoms, setAtoms] = useState<Atom[]>([]);
  const [claim, setClaim] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    setAtoms(await api<Atom[]>("/memory/atoms"));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <h1 className="page-title">Solace Memory</h1>
      <p className="status-msg">Foundation memory atoms â€?scoped to current user and organization only.</p>
      {msg && <p className="status-msg ok">{msg}</p>}
      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3>Add atom</h3>
        <div className="form-field">
          <label>Claim</label>
          <input value={claim} onChange={(e) => setClaim(e.target.value)} />
        </div>
        <button
          className="btn-primary"
          style={{ marginTop: "0.5rem" }}
          onClick={async () => {
            await api("/memory/atoms", { method: "POST", body: JSON.stringify({ claim, domain: "USER_SELF" }) });
            setClaim("");
            setMsg("Atom created");
            load();
          }}
        >
          Save
        </button>
      </div>
      <div className="card">
        <table className="data-table">
          <thead><tr><th>Domain</th><th>Classification</th><th>Claim</th></tr></thead>
          <tbody>
            {atoms.map((a) => (
              <tr key={a.id}><td>{a.domain}</td><td>{a.data_classification}</td><td>{a.claim}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
