import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { setupApi } from "../api/client";
import "./SetupPage.css";

export default function SetupPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [msg, setMsg] = useState("");
  const [db, setDb] = useState({
    server: "localhost",
    database: "SolaceEnterpriseCore",
    username: "sa",
    password: "",
    trust_server_certificate: true,
    use_trusted_connection: false,
  });
  const [admin, setAdmin] = useState({
    organization_name: "Default Organization",
    organization_code: "DEFAULT",
    admin_email: "admin@local",
    admin_username: "admin",
    admin_password: "",
    admin_display_name: "System Administrator",
  });

  useEffect(() => {
    setupApi.status().then((s) => {
      if (!s.needs_setup) navigate("/login");
    }).catch(() => {});
  }, [navigate]);

  async function testDb() {
    setMsg("Testing connection...");
    const r = await setupApi.testDb(db);
    setMsg(r.success ? "Connection OK" : (r.message ?? "Connection failed"));
  }

  async function saveAndMigrate() {
    setMsg("Saving...");
    const save = await setupApi.saveDb(db);
    if (!save.success) { setMsg(save.message ?? "Save failed"); return; }
    setMsg("Running migrations...");
    const mig = await setupApi.runMigrations();
    if (!mig.success) { setMsg(mig.message ?? "Migration failed"); return; }
    setMsg("Database ready");
    setStep(2);
  }

  async function finish() {
    setMsg("Creating organization and admin...");
    const r = await setupApi.complete(admin);
    setMsg(r.message);
    navigate("/login");
  }

  return (
    <div className="setup-page">
      <div className="setup-card card">
        <h1>Solace Enterprise Core</h1>
        <p className="subtitle">First-run setup</p>
        {step === 1 && (
          <>
            <h2>SQL Server</h2>
            <label>Server<input value={db.server} onChange={(e) => setDb({ ...db, server: e.target.value })} /></label>
            <label>Database<input value={db.database} onChange={(e) => setDb({ ...db, database: e.target.value })} /></label>
            <label>
              <input type="checkbox" checked={db.use_trusted_connection} onChange={(e) => setDb({ ...db, use_trusted_connection: e.target.checked })} />
              Use Windows trusted connection
            </label>
            {!db.use_trusted_connection && (
              <>
                <label>Username<input value={db.username} onChange={(e) => setDb({ ...db, username: e.target.value })} /></label>
                <label>Password<input type="password" value={db.password} onChange={(e) => setDb({ ...db, password: e.target.value })} /></label>
              </>
            )}
            <div className="btn-row">
              <button className="btn-secondary" onClick={testDb}>Test connection</button>
              <button className="btn-primary" onClick={saveAndMigrate}>Save & migrate</button>
            </div>
          </>
        )}
        {step === 2 && (
          <>
            <h2>Administrator</h2>
            <label>Organization<input value={admin.organization_name} onChange={(e) => setAdmin({ ...admin, organization_name: e.target.value })} /></label>
            <label>Org code<input value={admin.organization_code} onChange={(e) => setAdmin({ ...admin, organization_code: e.target.value })} /></label>
            <label>Email<input value={admin.admin_email} onChange={(e) => setAdmin({ ...admin, admin_email: e.target.value })} /></label>
            <label>Username<input value={admin.admin_username} onChange={(e) => setAdmin({ ...admin, admin_username: e.target.value })} /></label>
            <label>Password<input type="password" value={admin.admin_password} onChange={(e) => setAdmin({ ...admin, admin_password: e.target.value })} /></label>
            <button className="btn-primary" onClick={finish}>Complete setup</button>
          </>
        )}
        {msg && <p className="setup-msg">{msg}</p>}
      </div>
    </div>
  );
}

