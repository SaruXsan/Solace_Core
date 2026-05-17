import { useEffect, useState } from "react";
import { rolesApi, settingsApi, type LdapSettingsInput, type MfaSettingsInput } from "../api/platform";
import { useAuth } from "../context/AuthContext";
import ReadOnlyNotice from "../components/ReadOnlyNotice";
import "../components/forms.css";

type Tab = "system" | "database" | "security" | "ldap" | "mfa" | "ai" | "redaction";

export default function SettingsPage({ initialTab = "system" }: { initialTab?: Tab }) {
  const { can } = useAuth();
  const [tab, setTab] = useState<Tab>(initialTab);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const [system, setSystem] = useState({
    app_display_name: "",
    environment_label: "",
    session_timeout_minutes: 480,
    login_max_attempts: 5,
    login_lockout_minutes: 5,
  });
  const [dbStatus, setDbStatus] = useState<{
    configured: boolean;
    connected: boolean;
    server_hint?: string;
    database_name?: string;
    message?: string;
  } | null>(null);
  const [ldap, setLdap] = useState<LdapSettingsInput>({
    configured: false,
    directory_enabled: false,
    directory_type: "LDAPS",
    port: 636,
    use_ssl: true,
    user_search_filter: "(sAMAccountName={username})",
    email_attribute: "mail",
    display_name_attribute: "displayName",
    department_attribute: "department",
    certificate_validation_enabled: true,
    connection_timeout_seconds: 10,
    plain_ldap_warning_acknowledged: false,
  });
  const [ldapTestUser, setLdapTestUser] = useState("");
  const [ldapLookup, setLdapLookup] = useState<Record<string, unknown> | null>(null);
  const [groupMappings, setGroupMappings] = useState<{ directory_group_dn: string; role_id: string }[]>([]);
  const [roles, setRoles] = useState<{ id: string; code: string; name: string }[]>([]);
  const [syncPreview, setSyncPreview] = useState<Record<string, unknown[]> | null>(null);
  const [smtpTestTo, setSmtpTestTo] = useState("");
  const [mfa, setMfa] = useState<MfaSettingsInput>({
    enable_mfa: false,
    require_mfa_for_admins: true,
    otp_expiry_minutes: 10,
    otp_retry_limit: 5,
    resend_cooldown_seconds: 60,
    smtp_port: 587,
    smtp_use_tls: true,
    has_smtp_password: false,
  });
  const [aiProviders, setAiProviders] = useState<
    { provider_code: string; display_name: string; is_enabled: boolean; is_external: boolean }[]
  >([]);
  const [redaction, setRedaction] = useState<
    { id: string; pattern_name: string; pattern_regex: string; is_active: boolean }[]
  >([]);
  const [newRule, setNewRule] = useState({ pattern_name: "", pattern_regex: "" });

  useEffect(() => {
    loadTab(tab);
  }, [tab]);

  async function loadTab(t: Tab) {
    setErr("");
  try {
      if (t === "system" || t === "security") {
        const s = await settingsApi.system.get();
        setSystem(s);
      }
      if (t === "database") {
        setDbStatus(await settingsApi.database.get());
      }
      if (t === "ldap") {
        const l = await settingsApi.ldap.get();
        setLdap({ ...ldap, ...l, bind_password: undefined });
        const maps = await settingsApi.ldap.groupMappings.list();
        setGroupMappings(maps.map((m) => ({ directory_group_dn: m.directory_group_dn, role_id: m.role_id })));
        const r = await rolesApi.list();
        setRoles(r.map((x) => ({ id: x.id, code: x.code, name: x.name })));
      }
      if (t === "mfa") {
        const m = await settingsApi.mfa.get();
        setMfa({ ...m, smtp_password: undefined });
      }
      if (t === "ai") setAiProviders(await settingsApi.aiProviders.list());
      if (t === "redaction") setRedaction(await settingsApi.redaction.list());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Load failed");
    }
  }

  const allTabs: { id: Tab; label: string; perm: string }[] = [
    { id: "system", label: "System", perm: "settings.read" },
    { id: "database", label: "Database", perm: "settings.read" },
    { id: "security", label: "Security", perm: "settings.read" },
    { id: "ldap", label: "LDAP / LDAPS", perm: "ldap.read" },
    { id: "mfa", label: "MFA / Email OTP", perm: "mfa.read" },
    { id: "ai", label: "AI Providers", perm: "ai_providers.read" },
    { id: "redaction", label: "Redaction", perm: "redaction.read" },
  ];
  const tabs = allTabs.filter((t) => can(t.perm));
  const roSettings = can("settings.read") && !can("settings.update");
  const roLdap = can("ldap.read") && !can("ldap.update");
  const roMfa = can("mfa.read") && !can("mfa.update");
  const roAi = can("ai_providers.read") && !can("ai_providers.update");
  const roRedaction = can("redaction.read") && !can("settings.update");

  return (
    <>
      <h1 className="page-title">Settings</h1>
      <div className="tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`tab ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {err && <p className="status-msg error">{err}</p>}
      {msg && <p className="status-msg ok">{msg}</p>}

      {tab === "system" && (
        <div className="card">
          {roSettings && <ReadOnlyNotice />}
          <div className="form-grid">
            <div className="form-field">
              <label>App display name</label>
              <input readOnly={roSettings} disabled={roSettings} value={system.app_display_name} onChange={(e) => setSystem({ ...system, app_display_name: e.target.value })} />
            </div>
            <div className="form-field">
              <label>Environment label</label>
              <input readOnly={roSettings} disabled={roSettings} value={system.environment_label} onChange={(e) => setSystem({ ...system, environment_label: e.target.value })} />
            </div>
          </div>
          {!roSettings && (
            <div className="form-actions">
              <button className="btn-primary" onClick={async () => {
                await settingsApi.system.put(system);
                setMsg("System settings saved");
              }}>Save Settings</button>
            </div>
          )}
        </div>
      )}

      {tab === "database" && dbStatus && (
        <div className="card">
          {roSettings && <ReadOnlyNotice />}
          <p><strong>Configured:</strong> {dbStatus.configured ? "Yes" : "No"}</p>
          <p><strong>Connected:</strong>{" "}
            <span className={`badge ${dbStatus.connected ? "ok" : "warn"}`}>
              {dbStatus.connected ? "Online" : "Offline"}
            </span>
          </p>
          {dbStatus.server_hint && <p><strong>Server:</strong> {dbStatus.server_hint}</p>}
          {dbStatus.database_name && <p><strong>Database:</strong> {dbStatus.database_name}</p>}
          {dbStatus.message && <p className="status-msg">{dbStatus.message}</p>}
          {!roSettings && (
          <div className="form-actions">
            <button className="btn-secondary" onClick={async () => {
              const r = await settingsApi.database.test();
              setMsg(r.message || (r.success ? "Connection OK" : "Connection failed"));
              setDbStatus(await settingsApi.database.get());
            }}>Test Connection</button>
          </div>
          )}
        </div>
      )}

      {tab === "security" && (
        <div className="card">
          {roSettings && <ReadOnlyNotice />}
          <div className="form-grid">
            <div className="form-field">
              <label>Session timeout (minutes)</label>
              <input type="number" readOnly={roSettings} disabled={roSettings} value={system.session_timeout_minutes} onChange={(e) => setSystem({ ...system, session_timeout_minutes: +e.target.value })} />
            </div>
            <div className="form-field">
              <label>Max login attempts</label>
              <input type="number" readOnly={roSettings} disabled={roSettings} value={system.login_max_attempts} onChange={(e) => setSystem({ ...system, login_max_attempts: +e.target.value })} />
            </div>
            <div className="form-field">
              <label>Lockout duration (minutes)</label>
              <input type="number" readOnly={roSettings} disabled={roSettings} value={system.login_lockout_minutes} onChange={(e) => setSystem({ ...system, login_lockout_minutes: +e.target.value })} />
            </div>
          </div>
          <p className="status-msg">5 failed attempts triggers a 5-minute lockout when using defaults.</p>
          {!roSettings && (
            <div className="form-actions">
              <button className="btn-primary" onClick={async () => {
                await settingsApi.system.put(system);
                setMsg("Security settings saved");
              }}>Save Settings</button>
            </div>
          )}
        </div>
      )}

      {tab === "ldap" && (
        <div className="card">
          {roLdap && <ReadOnlyNotice />}
          {ldap.production_warning && <div className="alert-warning">{ldap.production_warning}</div>}
          <fieldset disabled={roLdap} style={{ border: 0, margin: 0, padding: 0 }}>
          <div className="form-grid">
            <div className="form-field">
              <label><input type="checkbox" checked={ldap.directory_enabled} onChange={(e) => setLdap({ ...ldap, directory_enabled: e.target.checked })} /> Directory enabled</label>
            </div>
            <div className="form-field">
              <label>Directory type</label>
              <select value={ldap.directory_type} onChange={(e) => setLdap({ ...ldap, directory_type: e.target.value })}>
                <option value="LDAP">LDAP</option>
                <option value="LDAPS">LDAPS</option>
                <option value="Active Directory">Active Directory</option>
              </select>
            </div>
            <div className="form-field"><label>Host</label><input value={ldap.host || ""} onChange={(e) => setLdap({ ...ldap, host: e.target.value })} /></div>
            <div className="form-field"><label>Port</label><input type="number" value={ldap.port || 389} onChange={(e) => setLdap({ ...ldap, port: +e.target.value })} /></div>
            <div className="form-field"><label><input type="checkbox" checked={ldap.use_ssl} onChange={(e) => setLdap({ ...ldap, use_ssl: e.target.checked })} /> Use SSL</label></div>
            <div className="form-field"><label><input type="checkbox" checked={ldap.use_starttls} onChange={(e) => setLdap({ ...ldap, use_starttls: e.target.checked })} /> Use STARTTLS</label></div>
            <div className="form-field"><label>Bind DN</label><input value={ldap.bind_dn || ""} onChange={(e) => setLdap({ ...ldap, bind_dn: e.target.value })} /></div>
            <div className="form-field"><label>Bind username</label><input value={ldap.bind_username || ""} onChange={(e) => setLdap({ ...ldap, bind_username: e.target.value })} /></div>
            <div className="form-field">
              <label>Bind password {ldap.has_bind_password && ldap.bind_password_masked ? `(stored: ${ldap.bind_password_masked})` : ""}</label>
              <input type="password" placeholder="Leave blank to keep existing" onChange={(e) => setLdap({ ...ldap, bind_password: e.target.value })} />
            </div>
            <div className="form-field full-width"><label>Base DN</label><input value={ldap.base_dn || ""} onChange={(e) => setLdap({ ...ldap, base_dn: e.target.value })} /></div>
            <div className="form-field full-width"><label>User search filter</label><input value={ldap.user_search_filter || ""} onChange={(e) => setLdap({ ...ldap, user_search_filter: e.target.value })} /></div>
            <div className="form-field full-width"><label>Group search filter</label><input value={ldap.group_search_filter || ""} onChange={(e) => setLdap({ ...ldap, group_search_filter: e.target.value })} /></div>
            <div className="form-field"><label>Email attribute</label><input value={ldap.email_attribute || "mail"} onChange={(e) => setLdap({ ...ldap, email_attribute: e.target.value })} /></div>
            <div className="form-field"><label>Display name attribute</label><input value={ldap.display_name_attribute || ""} onChange={(e) => setLdap({ ...ldap, display_name_attribute: e.target.value })} /></div>
            <div className="form-field"><label>Department attribute</label><input value={ldap.department_attribute || ""} onChange={(e) => setLdap({ ...ldap, department_attribute: e.target.value })} /></div>
            <div className="form-field"><label>Connection timeout (s)</label><input type="number" value={ldap.connection_timeout_seconds || 10} onChange={(e) => setLdap({ ...ldap, connection_timeout_seconds: +e.target.value })} /></div>
            <div className="form-field">
              <label><input type="checkbox" checked={ldap.certificate_validation_enabled} onChange={(e) => setLdap({ ...ldap, certificate_validation_enabled: e.target.checked })} /> Certificate validation</label>
            </div>
            {ldap.directory_type === "LDAP" && !ldap.use_ssl && (
              <div className="form-field full-width">
                <label><input type="checkbox" checked={ldap.plain_ldap_warning_acknowledged} onChange={(e) => setLdap({ ...ldap, plain_ldap_warning_acknowledged: e.target.checked })} /> Acknowledge plain LDAP warning (non-production)</label>
              </div>
            )}
          </div>
          <div className="form-field" style={{ marginTop: "1rem" }}>
            <label>Test user lookup</label>
            <input value={ldapTestUser} onChange={(e) => setLdapTestUser(e.target.value)} placeholder="username" />
          </div>
          </fieldset>
          {(can("ldap.update") || can("ldap.test")) && (
            <div className="form-actions">
              {can("ldap.update") && (
                <button className="btn-primary" onClick={async () => {
                  const r = await settingsApi.ldap.put(ldap);
                  if (r.warning) setErr(r.warning);
                  else { setMsg("LDAP settings saved"); await loadTab("ldap"); }
                }}>Save Settings</button>
              )}
              {can("ldap.test") && (
                <>
                  <button className="btn-secondary" onClick={async () => {
                    const r = await settingsApi.ldap.testConnection();
                    setMsg(r.message + (r.warnings?.length ? ` ? ${r.warnings.join(" ")}` : ""));
                  }}>Test Connection</button>
                  <button className="btn-secondary" disabled={!ldapTestUser} onClick={async () => {
                    const r = await settingsApi.ldap.testUser(ldapTestUser);
                    setLdapLookup(r as Record<string, unknown>);
                    setMsg(r.found ? "User found in directory" : "User not found");
                  }}>Test User Lookup</button>
                </>
              )}
            </div>
          )}
          {ldapLookup && ldapLookup.found === true && (
            <div className="card" style={{ marginTop: "1rem", background: "var(--bg-elevated)" }}>
              <h3>Lookup result</h3>
              <p><strong>Username:</strong> {String(ldapLookup.username)}</p>
              <p><strong>Email:</strong> {String(ldapLookup.email || "-")}</p>
              <p><strong>Display name:</strong> {String(ldapLookup.display_name || "-")}</p>
              <p><strong>Department:</strong> {String(ldapLookup.department || "-")}</p>
              <p><strong>Groups:</strong> {(ldapLookup.groups as string[] | undefined)?.join(", ") || "-"}</p>
            </div>
          )}
          {can("ldap.update") && (
            <div style={{ marginTop: "1.5rem" }}>
              <h3>Group ? role mapping</h3>
              {groupMappings.map((m, i) => (
                <div key={i} className="form-grid" style={{ marginBottom: "0.5rem" }}>
                  <div className="form-field"><input placeholder="CN=Group,OU=..." value={m.directory_group_dn} onChange={(e) => {
                    const next = [...groupMappings]; next[i] = { ...m, directory_group_dn: e.target.value }; setGroupMappings(next);
                  }} /></div>
                  <div className="form-field">
                    <select value={m.role_id} onChange={(e) => {
                      const next = [...groupMappings]; next[i] = { ...m, role_id: e.target.value }; setGroupMappings(next);
                    }}>
                      <option value="">Select role</option>
                      {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                  </div>
                </div>
              ))}
              <button type="button" className="btn-secondary" onClick={() => setGroupMappings([...groupMappings, { directory_group_dn: "", role_id: "" }])}>Add mapping</button>
              <button type="button" className="btn-primary" style={{ marginLeft: "0.5rem" }} onClick={async () => {
                await settingsApi.ldap.groupMappings.save(groupMappings.filter((m) => m.directory_group_dn && m.role_id));
                setMsg("Group mappings saved");
              }}>Save mappings</button>
            </div>
          )}
          {can("ldap.sync") && (
            <div style={{ marginTop: "1.5rem" }}>
              <h3>Directory sync</h3>
              <label><input type="checkbox" checked={!!ldap.overwrite_local_on_sync} onChange={(e) => setLdap({ ...ldap, overwrite_local_on_sync: e.target.checked })} /> Overwrite local users on sync</label>
              <div className="form-actions" style={{ marginTop: "0.5rem" }}>
                <button className="btn-secondary" onClick={async () => {
                  setSyncPreview(await settingsApi.ldap.syncPreview());
                  setMsg("Sync preview ready");
                }}>Preview Sync</button>
                <button className="btn-primary" onClick={async () => {
                  if (!confirm("Apply directory sync?")) return;
                  const r = await settingsApi.ldap.syncApply();
                  setMsg(`Applied: ${JSON.stringify(r.counts)}`);
                }}>Apply Sync</button>
              </div>
              {syncPreview && <pre style={{ marginTop: "1rem", fontSize: "0.8rem" }}>{JSON.stringify(syncPreview, null, 2)}</pre>}
            </div>
          )}
        </div>
      )}

      {tab === "mfa" && (
        <div className="card">
          {roMfa && <ReadOnlyNotice />}
          <fieldset disabled={roMfa} style={{ border: 0, margin: 0, padding: 0 }}>
          <div className="form-grid">
            <div className="form-field"><label><input type="checkbox" checked={mfa.enable_mfa} onChange={(e) => setMfa({ ...mfa, enable_mfa: e.target.checked })} /> Enable MFA</label></div>
            <div className="form-field"><label><input type="checkbox" checked={mfa.require_mfa_for_admins} onChange={(e) => setMfa({ ...mfa, require_mfa_for_admins: e.target.checked })} /> Require MFA for admins</label></div>
            <div className="form-field"><label>OTP expiry (minutes)</label><input type="number" value={mfa.otp_expiry_minutes} onChange={(e) => setMfa({ ...mfa, otp_expiry_minutes: +e.target.value })} /></div>
            <div className="form-field"><label>OTP retry limit</label><input type="number" value={mfa.otp_retry_limit} onChange={(e) => setMfa({ ...mfa, otp_retry_limit: +e.target.value })} /></div>
            <div className="form-field"><label>Resend cooldown (seconds)</label><input type="number" value={mfa.resend_cooldown_seconds} onChange={(e) => setMfa({ ...mfa, resend_cooldown_seconds: +e.target.value })} /></div>
            <div className="form-field"><label>SMTP host</label><input value={mfa.smtp_host || ""} onChange={(e) => setMfa({ ...mfa, smtp_host: e.target.value })} /></div>
            <div className="form-field"><label>SMTP port</label><input type="number" value={mfa.smtp_port} onChange={(e) => setMfa({ ...mfa, smtp_port: +e.target.value })} /></div>
            <div className="form-field"><label><input type="checkbox" checked={mfa.smtp_use_tls} onChange={(e) => setMfa({ ...mfa, smtp_use_tls: e.target.checked })} /> SMTP TLS</label></div>
            <div className="form-field"><label>SMTP username</label><input value={mfa.smtp_username || ""} onChange={(e) => setMfa({ ...mfa, smtp_username: e.target.value })} /></div>
            <div className="form-field">
              <label>SMTP password {mfa.has_smtp_password && mfa.smtp_password_masked ? `(${mfa.smtp_password_masked})` : ""}</label>
              <input type="password" placeholder="Leave blank to keep" onChange={(e) => setMfa({ ...mfa, smtp_password: e.target.value })} />
            </div>
            <div className="form-field"><label>From email</label><input value={mfa.from_email || ""} onChange={(e) => setMfa({ ...mfa, from_email: e.target.value })} /></div>
          </div>
          </fieldset>
          {!roMfa && (
            <div className="form-actions">
              <button className="btn-primary" onClick={async () => {
                await settingsApi.mfa.put(mfa);
                setMsg("MFA settings saved");
                await loadTab("mfa");
              }}>Save Settings</button>
            </div>
          )}
          {can("smtp.test") && !roMfa && (
            <div style={{ marginTop: "1.5rem" }}>
              <h3>Test SMTP</h3>
              <div className="form-field">
                <label>Send test email to</label>
                <input type="email" value={smtpTestTo} onChange={(e) => setSmtpTestTo(e.target.value)} placeholder="you@company.com" />
              </div>
              <button className="btn-secondary" onClick={async () => {
                const r = await settingsApi.mfa.testSmtp(smtpTestTo);
                setMsg(r.message);
              }}>Send test email</button>
            </div>
          )}
        </div>
      )}

      {tab === "ai" && (
        <div className="card">
          {roAi && <ReadOnlyNotice />}
          <table className="data-table">
            <thead><tr><th>Provider</th><th>Type</th><th>External</th><th>Enabled</th></tr></thead>
            <tbody>
              {aiProviders.map((p) => (
                <tr key={p.provider_code}>
                  <td>{p.display_name}</td>
                  <td>{p.provider_code}</td>
                  <td>{p.is_external ? "Yes" : "No"}</td>
                  <td>
                    <input type="checkbox" checked={p.is_enabled} disabled={!can("ai_providers.update")} title={can("ai_providers.update") ? undefined : "Requires ai_providers.update"} onChange={async (e) => {
                      await settingsApi.aiProviders.patch(p.provider_code, e.target.checked);
                      setAiProviders(await settingsApi.aiProviders.list());
                    }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "redaction" && (
        <div className="card">
          {roRedaction && <ReadOnlyNotice />}
          <table className="data-table">
            <thead><tr><th>Name</th><th>Pattern</th><th>Active</th></tr></thead>
            <tbody>
              {redaction.map((r) => (
                <tr key={r.id}><td>{r.pattern_name}</td><td><code>{r.pattern_regex}</code></td><td>{r.is_active ? "Yes" : "No"}</td></tr>
              ))}
            </tbody>
          </table>
          {!roRedaction && (
          <>
          <h3 style={{ marginTop: "1rem", fontSize: "0.95rem" }}>Add rule</h3>
          <div className="form-grid">
            <div className="form-field"><label>Name</label><input value={newRule.pattern_name} onChange={(e) => setNewRule({ ...newRule, pattern_name: e.target.value })} /></div>
            <div className="form-field"><label>Regex</label><input value={newRule.pattern_regex} onChange={(e) => setNewRule({ ...newRule, pattern_regex: e.target.value })} /></div>
          </div>
          <button className="btn-primary" style={{ marginTop: "0.5rem" }} onClick={async () => {
            await settingsApi.redaction.create(newRule);
            setRedaction(await settingsApi.redaction.list());
            setNewRule({ pattern_name: "", pattern_regex: "" });
            setMsg("Redaction rule added");
          }}>Add rule</button>
          </>
          )}
        </div>
      )}
    </>
  );
}


