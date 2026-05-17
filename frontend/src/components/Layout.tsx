import { Link, Outlet, useNavigate } from "react-router-dom";
import { authApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import "./Layout.css";

type NavItem = {
  label: string;
  path: string;
  permission?: string;
  anyOf?: string[];
};

type NavGroup = {
  section: string;
  items: NavItem[];
};

const NAV: NavGroup[] = [
  { section: "Dashboard", items: [{ label: "Overview", path: "/", permission: "dashboard.read" }] },
  {
    section: "Platform",
    items: [
      { label: "Users", path: "/platform/users", permission: "users.read" },
      { label: "Roles & Permissions", path: "/platform/roles", permission: "roles.read" },
      { label: "Organizations / Branches", path: "/platform/organizations", anyOf: ["organizations.read", "branches.read"] },
      { label: "Modules", path: "/platform/modules", permission: "modules.read" },
      { label: "Settings", path: "/platform/settings", permission: "settings.read" },
    ],
  },
  {
    section: "Security",
    items: [
      { label: "LDAP / LDAPS", path: "/security/ldap", permission: "ldap.read" },
      { label: "MFA / Email OTP", path: "/security/mfa", permission: "mfa.read" },
      { label: "Sessions", path: "/security/sessions", permission: "sessions.read" },
      { label: "Login Attempts", path: "/security/login-attempts", permission: "login_attempts.read" },
    ],
  },
  {
    section: "Solace",
    items: [
      { label: "AI Providers", path: "/solace/ai-providers", permission: "ai_providers.read" },
      { label: "Memory", path: "/solace/memory", permission: "memory.read" },
      { label: "Personas", path: "/solace/personas", permission: "personas.read" },
      { label: "REM", path: "/solace/rem", permission: "rem.read" },
      { label: "LLM Calls", path: "/solace/llm-calls", permission: "logs.read" },
    ],
  },
  {
    section: "Compliance",
    items: [
      { label: "RFI Center", path: "/compliance/rfi", permission: "compliance.read" },
      { label: "Control Map", path: "/compliance/controls", permission: "compliance.read" },
      { label: "Evidence Library", path: "/compliance/evidence", permission: "evidence.read" },
      { label: "Access Reviews", path: "/compliance/access-reviews", permission: "compliance.read" },
      { label: "Incidents", path: "/compliance/incidents", permission: "compliance.read" },
      { label: "Change Management", path: "/compliance/changes", permission: "compliance.read" },
      { label: "Infrastructure Evidence", path: "/compliance/infra", permission: "compliance.read" },
      { label: "AppSec Evidence", path: "/compliance/appsec", permission: "compliance.read" },
      { label: "Redaction Rules", path: "/compliance/redaction", permission: "redaction.read" },
    ],
  },
  {
    section: "Logs",
    items: [
      { label: "Audit Trail", path: "/logs/audit-trail", anyOf: ["audit.read", "logs.read"] },
      { label: "Login Events", path: "/logs/login-events", permission: "logs.read" },
      { label: "Admin Actions", path: "/logs/admin-actions", permission: "logs.read" },
      { label: "Config Changes", path: "/logs/config-changes", permission: "logs.read" },
      { label: "Permission Changes", path: "/logs/permission-changes", permission: "logs.read" },
      { label: "System Errors", path: "/logs/system-errors", permission: "logs.read" },
    ],
  },
];

function visibleItem(can: (p: string) => boolean, canAny: (ps: string[]) => boolean, item: NavItem) {
  if (item.permission) return can(item.permission);
  if (item.anyOf) return canAny(item.anyOf);
  return true;
}

export default function Layout() {
  const navigate = useNavigate();
  const { displayName, can, canAny } = useAuth();

  async function signOut() {
    try {
      await authApi.logout();
    } catch {
      /* ignore */
    }
    localStorage.clear();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="brand-mark">◆</span>
          <span>Solace Enterprise Core</span>
          <span className="env-badge">FOUNDATION</span>
        </div>
        <div className="topbar-right">
          <span className="status-dot" title="System online" />
          <span className="user-label">{displayName || "User"}</span>
          <button className="btn-secondary" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>
      <div className="body-row">
        <aside className="sidebar">
          {NAV.map((g) => {
            const items = g.items.filter((item) => visibleItem(can, canAny, item));
            if (items.length === 0) return null;
            return (
              <div key={g.section} className="nav-group">
                <div className="nav-section">{g.section}</div>
                {items.map((item) => (
                  <Link key={item.path} to={item.path} className="nav-link">
                    {item.label}
                  </Link>
                ))}
              </div>
            );
          })}
        </aside>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}