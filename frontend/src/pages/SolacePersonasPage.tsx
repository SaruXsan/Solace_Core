import { useEffect, useState } from "react";
import { api } from "../api/client";
import "../components/forms.css";

type Persona = { id: string; persona_name: string; conflict_policy: string };

export default function SolacePersonasPage() {
  const [rows, setRows] = useState<Persona[]>([]);

  useEffect(() => {
    api<Persona[]>("/memory/personas").then(setRows).catch(() => setRows([]));
  }, []);

  return (
    <>
      <h1 className="page-title">Solace Personas</h1>
      <p className="status-msg">Foundation personas â€?user-scoped with conflict policy.</p>
      <div className="card">
        <table className="data-table">
          <thead><tr><th>Name</th><th>Conflict policy</th></tr></thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id}><td>{p.persona_name}</td><td>{p.conflict_policy}</td></tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={2}>No personas yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
