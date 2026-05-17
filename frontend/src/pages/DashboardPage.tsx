import { useEffect, useState } from "react";
import { dashboardApi } from "../api/platform";

type Stats = {
  total_users: number;
  active_users: number;
  locked_users: number;
  mfa_enabled_users: number;
  failed_logins_today: number;
  enabled_modules: number;
  evidence_records: number;
  open_incidents: number;
  ai_calls_today: number;
  system_health: { database_connected: boolean; setup_complete: boolean };
};

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    dashboardApi.stats().then(setStats).catch(() => setStats(null));
  }, []);

  const cards = stats
    ? [
        { label: "Total users", value: stats.total_users },
        { label: "Active users", value: stats.active_users },
        { label: "Locked users", value: stats.locked_users },
        { label: "MFA enabled", value: stats.mfa_enabled_users },
        { label: "Failed logins today", value: stats.failed_logins_today },
        { label: "Enabled modules", value: stats.enabled_modules },
        { label: "Evidence records", value: stats.evidence_records },
        { label: "Open incidents", value: stats.open_incidents },
        { label: "AI calls today", value: stats.ai_calls_today },
        {
          label: "System health",
          value: stats.system_health.database_connected ? "DB OK" : "DB offline",
        },
      ]
    : [];

  return (
    <>
      <h1 className="page-title">Command Center</h1>
      <div className="placeholder-grid">
        {cards.length > 0 ? (
          cards.map((c) => (
            <div className="card" key={c.label}>
              <h3>{c.label}</h3>
              <p style={{ fontSize: "1.5rem", fontWeight: 600 }}>{c.value}</p>
            </div>
          ))
        ) : (
          <>
            <div className="card"><h3>Loading</h3><p style={{ color: "var(--text-muted)" }}>Fetching dashboard metrics...</p></div>
          </>
        )}
      </div>
    </>
  );
}
