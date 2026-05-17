import { useEffect, useState } from "react";
import { securityApi, type SecurityReadinessReport } from "../api/platform";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

export default function SecurityReadinessPage() {
  const { can } = useAuth();
  const [report, setReport] = useState<SecurityReadinessReport | null>(null);
  const [err, setErr] = useState("");
  const [ldapUser, setLdapUser] = useState("");
  const [ldapDiag, setLdapDiag] = useState<Record<string, unknown> | null>(null);
  const [ldapBusy, setLdapBusy] = useState(false);

  async function load() {
    if (!can("security.readiness")) return;
    try {
      setReport(await securityApi.readiness());
      setErr("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load readiness report");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function runLdapDiagnostics() {
    setLdapBusy(true);
    try {
      setLdapDiag(
        await securityApi.ldapDiagnostics(ldapUser.trim() ? { test_username: ldapUser.trim() } : {})
      );
    } catch (e) {
      setLdapDiag({ summary: e instanceof Error ? e.message : "Diagnostics failed" });
    } finally {
      setLdapBusy(false);
    }
  }

  if (!can("security.readiness")) {
    return <p className="status-msg error">Requires security.readiness permission.</p>;
  }

  const cards = report
    ? [
        { label: "MFA-enabled admins", value: `${report.mfa_enabled_admins_count} / ${report.total_admins_count}` },
        { label: "Privileged without MFA", value: report.privileged_users_without_mfa },
        { label: "Failed logins (24h)", value: report.failed_logins_last_24h },
        { label: "Locked users (local)", value: report.locked_users_count },
        { label: "Active sessions", value: report.sessions.active_count },
        { label: "Sessions revoked (24h)", value: report.sessions.revoked_last_24h },
        { label: "Permission denied (24h)", value: report.permission_denied_last_24h },
        { label: "Break-glass users", value: report.break_glass_users.length },
      ]
    : [];

  return (
    <>
      <h1 className="page-title">Security Readiness</h1>
      <p className="status-msg" style={{ marginBottom: "1rem" }}>
        Staging validation snapshot. No secrets are shown on this page.
      </p>
      {err && <p className="status-msg error">{err}</p>}

      <div className="placeholder-grid">
        {cards.map((c) => (
          <div key={c.label} className="card">
            <h3>{c.label}</h3>
            <p style={{ fontSize: "1.5rem", fontWeight: 600 }}>{c.value}</p>
          </div>
        ))}
      </div>

      {report && (
        <>
          <div className="card" style={{ marginTop: "1.5rem" }}>
            <h3>Directory and email</h3>
            <ul className="status-msg">
              <li>LDAP enabled: {report.ldap.enabled ? "Yes" : "No"} ({report.ldap.directory_type || "n/a"})</li>
              {report.ldap.plain_ldap_warning && (
                <li className="status-msg error">{report.ldap.plain_ldap_warning}</li>
              )}
              <li>
                SMTP configured: {report.smtp.configured ? "Yes" : "No"}
                {report.smtp.host ? ` (${report.smtp.host})` : ""}
              </li>
              <li>Encrypted vault reachable: {report.encrypted_settings_vault.reachable ? "Yes" : "No"}</li>
            </ul>
          </div>

          {report.break_glass_users.length > 0 && (
            <div className="card" style={{ marginTop: "1rem" }}>
              <h3>Break-glass administrators</h3>
              <p className="status-msg warn">
                These users rely on is_admin wildcard because they have no roles. Assign system_administrator
                and use RBAC instead.
              </p>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Display name</th>
                    <th>Email</th>
                    <th>Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {report.break_glass_users.map((u) => (
                    <tr key={u.id}>
                      <td>{u.username}</td>
                      <td>{u.display_name}</td>
                      <td>{u.email}</td>
                      <td>{u.recommendation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {can("ldap.test") && (
            <div className="card" style={{ marginTop: "1rem" }}>
              <h3>LDAP diagnostics</h3>
              <p className="status-msg">Runs bind test and optional user lookup. Bind password is never returned.</p>
              <div className="form-grid">
                <div className="form-field">
                  <label>Test username (optional)</label>
                  <input value={ldapUser} onChange={(e) => setLdapUser(e.target.value)} placeholder="sAMAccountName" />
                </div>
              </div>
              <button type="button" className="btn-primary" disabled={ldapBusy} onClick={runLdapDiagnostics}>
                {ldapBusy ? "Running..." : "Run diagnostics"}
              </button>
              {ldapDiag && (
                <pre style={{ marginTop: "1rem", fontSize: "0.85rem", overflow: "auto" }}>
                  {JSON.stringify(ldapDiag, null, 2)}
                </pre>
              )}
            </div>
          )}
        </>
      )}
    </>
  );
}
