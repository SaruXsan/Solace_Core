import { useEffect, useState } from "react";
import { api } from "../api/client";
import { settingsApi, type RedactionRule } from "../api/platform";
import { useAuth } from "../context/AuthContext";
import ReadOnlyNotice from "../components/ReadOnlyNotice";
import "../components/forms.css";

export default function RedactionPage() {
  const { can } = useAuth();
  const [rules, setRules] = useState<RedactionRule[]>([]);
  const [sample, setSample] = useState("Contact admin@example.com or call +1-555-0100. API key sk-live-abc123");
  const [result, setResult] = useState("");

  useEffect(() => {
    settingsApi.redaction.list().then(setRules).catch(() => setRules([]));
  }, []);

  return (
    <>
      <h1 className="page-title">Redaction Rules</h1>
      <p className="status-msg">Patterns applied before logs and external AI calls.</p>
      {can("redaction.read") && !can("settings.update") && <ReadOnlyNotice />}
      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3>Active rules</h3>
        <table className="data-table">
          <thead><tr><th>Name</th><th>Pattern</th><th>Replacement</th></tr></thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id}><td>{r.pattern_name}</td><td><code>{r.pattern_regex}</code></td><td>{r.replacement}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h3>Test redaction</h3>
        <textarea rows={4} style={{ width: "100%" }} value={sample} onChange={(e) => setSample(e.target.value)} />
        <button
          className="btn-primary"
          style={{ marginTop: "0.5rem" }}
          disabled={!can("redaction.test")}
          title={can("redaction.test") ? undefined : "Requires redaction.test"}
          onClick={async () => {
            const r = await api<{ redacted: string }>("/compliance/redaction/test", {
              method: "POST",
              body: JSON.stringify({ text: sample }),
            });
            setResult(r.redacted);
          }}
        >
          Run test
        </button>
        {result && <pre style={{ marginTop: "1rem", whiteSpace: "pre-wrap" }}>{result}</pre>}
      </div>
    </>
  );
}
