import { useEffect, useState } from "react";
import { api } from "../api/client";
import "../components/forms.css";

type Tab = "audit" | "login" | "admin" | "config" | "permissions" | "llm" | "posture" | "errors";

const TABS: { id: Tab; label: string; path: string }[] = [
  { id: "audit", label: "Audit Trail", path: "/logs/audit-trail" },
  { id: "login", label: "Login Events", path: "/logs/login-events" },
  { id: "admin", label: "Admin Actions", path: "/logs/admin-actions" },
  { id: "config", label: "Config Changes", path: "/logs/config-changes" },
  { id: "permissions", label: "Permission Changes", path: "/logs/permission-changes" },
  { id: "llm", label: "LLM Calls", path: "/logs/llm-calls" },
  { id: "posture", label: "Posture Violations", path: "/logs/posture-violations" },
  { id: "errors", label: "System Errors", path: "/logs/system-errors" },
];

export default function LogsPage({ defaultTab = "audit" }: { defaultTab?: Tab }) {
  const [tab, setTab] = useState<Tab>(defaultTab);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    setTab(defaultTab);
  }, [defaultTab]);

  useEffect(() => {
    const t = TABS.find((x) => x.id === tab)!;
    api<Record<string, unknown>[]>(t.path).then(setRows).catch(() => setRows([]));
  }, [tab]);

  const keys = rows[0] ? Object.keys(rows[0]).filter((k) => k !== "id") : [];

  return (
    <>
      <h1 className="page-title">Logs</h1>
      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.id} type="button" className={`tab ${tab === t.id ? "active" : ""}`} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>{keys.map((k) => <th key={k}>{k}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={String(r.id || i)}>
                {keys.map((k) => (
                  <td key={k}>{String(r[k] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="status-msg">No records.</p>}
      </div>
    </>
  );
}
