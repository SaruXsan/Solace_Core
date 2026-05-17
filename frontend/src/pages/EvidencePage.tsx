import { useEffect, useState } from "react";
import { complianceApi, type EvidenceRow } from "../api/platform";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

export default function EvidencePage() {
  const { can } = useAuth();
  const [rows, setRows] = useState<EvidenceRow[]>([]);
  const [msg, setMsg] = useState("");

  async function load() {
    setRows(await complianceApi.evidence());
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <h1 className="page-title">Evidence Library</h1>
      <p className="status-msg">Chain of custody via digital_signature_hash on each record.</p>
      {msg && <p className="status-msg ok">{msg}</p>}

      <div className="form-actions" style={{ marginBottom: "1rem" }}>
        {can("compliance.update") && (
          <button
            className="btn-primary"
            onClick={async () => {
              const r = await complianceApi.runAutoLinker();
              setMsg(`Auto-linker created ${r.created} evidence record(s)`);
              await load();
            }}
          >
            Run Evidence Auto-Linker
          </button>
        )}
        <button className="btn-secondary" onClick={load}>Refresh</button>
      </div>

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Control</th>
              <th>Signature hash</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => (
              <tr key={e.id}>
                <td>{e.title}</td>
                <td>{e.control_id || "—"}</td>
                <td><code style={{ fontSize: "0.7rem" }}>{e.digital_signature_hash.slice(0, 24)}…</code></td>
                <td>{new Date(e.created_at).toLocaleString()}</td>
                <td>
                  {can("evidence.verify") ? (
                    <button
                      className="btn-secondary"
                      onClick={async () => {
                        const r = await complianceApi.verifyEvidence(e.id);
                        setMsg(r.valid ? "Hash verified" : r.message || "Hash mismatch");
                      }}
                    >
                      Verify
                    </button>
                  ) : (
                    <span title="Requires evidence.verify">—</span>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={4} style={{ color: "var(--text-muted)" }}>No evidence yet — run the auto-linker skeleton.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
