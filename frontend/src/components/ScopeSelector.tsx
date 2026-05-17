import { useState } from "react";
import { authApi } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function ScopeSelector() {
  const { activeScope, availableScopes, refresh } = useAuth();
  const [busy, setBusy] = useState(false);

  if (!availableScopes.length) return null;

  async function onChange(scopeKey: string) {
    const scope = availableScopes.find(
      (s) =>
        `${s.scope_type}|${s.organization_id || ""}|${s.branch_id || ""}|${s.department_id || ""}` ===
        scopeKey
    );
    if (!scope) return;
    setBusy(true);
    try {
      const res = await authApi.switchScope({
        scope_type: scope.scope_type,
        country_id: scope.country_id || undefined,
        organization_id: scope.organization_id || undefined,
        branch_id: scope.branch_id || undefined,
        department_id: scope.department_id || undefined,
      });
      localStorage.setItem("access_token", res.access_token);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  const currentKey = activeScope
    ? `${activeScope.scope_type}|${activeScope.organization_id || ""}|${activeScope.branch_id || ""}|${activeScope.department_id || ""}`
    : "";

  return (
    <div className="scope-selector" title="Active enterprise scope">
      <label className="scope-label">Scope</label>
      <select
        className="scope-select"
        disabled={busy || availableScopes.length <= 1}
        value={currentKey}
        onChange={(e) => onChange(e.target.value)}
        aria-label="Active enterprise scope"
      >
        {availableScopes.map((s) => {
          const key = `${s.scope_type}|${s.organization_id || ""}|${s.branch_id || ""}|${s.department_id || ""}`;
          return (
            <option key={key} value={key}>
              {s.label || s.scope_type}
            </option>
          );
        })}
      </select>
    </div>
  );
}

