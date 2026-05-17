import { useEffect, useState } from "react";
import { api } from "../api/client";
import "../components/forms.css";

type Rem = { id: string; proposal_type: string; status: string; payload_preview: string };

export default function SolaceRemPage() {
  const [rows, setRows] = useState<Rem[]>([]);

  useEffect(() => {
    api<Rem[]>("/memory/rem-proposals").then(setRows).catch(() => setRows([]));
  }, []);

  return (
    <>
      <h1 className="page-title">REM Proposals</h1>
      <p className="status-msg">Foundation REM table â€?advanced intelligence not implemented.</p>
      <div className="card">
        <table className="data-table">
          <thead><tr><th>Type</th><th>Status</th><th>Payload</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}><td>{r.proposal_type}</td><td>{r.status}</td><td><code>{r.payload_preview}</code></td></tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={3}>No REM proposals.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
