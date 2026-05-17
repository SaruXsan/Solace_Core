import { useEffect, useState } from "react";
import { securityApi, usersApi, type LoginAttemptRow, type SessionRow } from "../api/platform";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

type Tab = "sessions" | "attempts";

export default function SecurityOperationsPage({ defaultTab = "sessions" }: { defaultTab?: Tab }) {
  const { can } = useAuth();
  const [tab, setTab] = useState<Tab>(defaultTab);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [attempts, setAttempts] = useState<LoginAttemptRow[]>([]);
  const [trends, setTrends] = useState<{ hour: number; count: number }[]>([]);
  const [filterUser, setFilterUser] = useState("");
  const [filterSuccess, setFilterSuccess] = useState<string>("");
  const [msg, setMsg] = useState("");
  const [users, setUsers] = useState<{ id: string; username: string }[]>([]);

  async function loadSessions() {
    if (!can("sessions.read")) return;
    setSessions(await securityApi.sessions({ username: filterUser || undefined }));
  }

  async function loadAttempts() {
    if (!can("login_attempts.read")) return;
    const success = filterSuccess === "" ? undefined : filterSuccess === "true";
    setAttempts(
      await securityApi.loginAttempts({
        username: filterUser || undefined,
        success,
      })
    );
    const t = await securityApi.loginTrends(24);
    setTrends(t.failed_by_hour);
  }

  useEffect(() => {
    usersApi.list().then((u) => setUsers(u.map((x) => ({ id: x.id, username: x.username })))).catch(() => {});
  }, []);

  useEffect(() => {
    if (tab === "sessions") loadSessions();
    else loadAttempts();
  }, [tab, filterUser, filterSuccess]);

  return (
    <>
      <h1 className="page-title">Security Operations</h1>
      <div className="tabs">
        {can("sessions.read") && (
          <button type="button" className={`tab ${tab === "sessions" ? "active" : ""}`} onClick={() => setTab("sessions")}>
            Active Sessions
          </button>
        )}
        {can("login_attempts.read") && (
          <button type="button" className={`tab ${tab === "attempts" ? "active" : ""}`} onClick={() => setTab("attempts")}>
            Login Attempts
          </button>
        )}
      </div>
      {msg && <p className="status-msg ok">{msg}</p>}
      <div className="card" style={{ marginBottom: "1rem" }}>
        <div className="form-grid">
          <div className="form-field">
            <label>Filter username</label>
            <input value={filterUser} onChange={(e) => setFilterUser(e.target.value)} placeholder="partial match" />
          </div>
          {tab === "attempts" && (
            <div className="form-field">
              <label>Success</label>
              <select value={filterSuccess} onChange={(e) => setFilterSuccess(e.target.value)}>
                <option value="">All</option>
                <option value="true">Success</option>
                <option value="false">Failed</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {tab === "sessions" && (
        <div className="card">
          <table className="data-table">
            <thead>
              <tr>
                <th>User</th>
                <th>IP</th>
                <th>User agent</th>
                <th>Created</th>
                <th>Expires</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.id}>
                  <td>{s.username}</td>
                  <td>{s.ip_address || "-"}</td>
                  <td style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>{s.user_agent || "-"}</td>
                  <td>{s.created_at ? new Date(s.created_at).toLocaleString() : "-"}</td>
                  <td>{new Date(s.expires_at).toLocaleString()}</td>
                  <td>
                    {can("sessions.revoke") && (
                      <button
                        className="btn-secondary"
                        onClick={async () => {
                          await securityApi.revokeSession(s.id);
                          setMsg("Session revoked");
                          loadSessions();
                        }}
                      >
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {can("sessions.revoke") && users.length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <label>Revoke all sessions for user</label>
              <select
                onChange={async (e) => {
                  const id = e.target.value;
                  if (!id) return;
                  await securityApi.revokeAllSessions(id);
                  setMsg("All sessions revoked for user");
                  loadSessions();
                  e.target.value = "";
                }}
                defaultValue=""
              >
                <option value="">Select user...</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.username}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {tab === "attempts" && (
        <>
          {trends.length > 0 && (
            <div className="card" style={{ marginBottom: "1rem" }}>
              <h3>Failed logins (24h)</h3>
              <p className="status-msg">
                {trends.map((t) => `H${t.hour}: ${t.count}`).join(" ? ")}
              </p>
            </div>
          )}
          <div className="card">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Username</th>
                  <th>Source</th>
                  <th>IP</th>
                  <th>Result</th>
                  <th>Reason</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {attempts.map((a) => (
                  <tr key={a.id}>
                    <td>{a.created_at ? new Date(a.created_at).toLocaleString() : "-"}</td>
                    <td>{a.username}</td>
                    <td>{a.auth_source}</td>
                    <td>{a.ip_address || "-"}</td>
                    <td>{a.success ? "OK" : "Failed"}</td>
                    <td>{a.failure_reason || "-"}</td>
                    <td>
                      {!a.success && can("users.unlock") && (
                        <button
                          className="btn-secondary"
                          onClick={async () => {
                            const u = users.find((x) => x.username === a.username);
                            if (!u) {
                              setMsg("User not in list ??unlock from Users page");
                              return;
                            }
                            await securityApi.unlockUser(u.id);
                            setMsg(`Unlocked ${a.username}`);
                          }}
                        >
                          Unlock
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}



