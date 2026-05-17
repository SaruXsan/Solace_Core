import { useState } from "react";
import { authApi } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function ConsolidationSelector() {
  const { activeConsolidationScope, availableConsolidationScopes, refresh, can } = useAuth();
  const [busy, setBusy] = useState(false);

  if (!can("consolidation.view") || availableConsolidationScopes.length === 0) {
    return null;
  }

  async function onChange(scopeId: string) {
    setBusy(true);
    try {
      await authApi.switchConsolidationScope(scopeId || null);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  const current = activeConsolidationScope?.id ?? "";

  return (
    <div className="consolidation-selector" title="Executive consolidation scope (reporting authority)">
      <label className="scope-label consolidation-label">Consolidation</label>
      <select
        className="scope-select consolidation-select"
        disabled={busy}
        value={current}
        onChange={(e) => onChange(e.target.value)}
        aria-label="Active consolidation scope"
      >
        <option value="">None (operational only)</option>
        {availableConsolidationScopes.map((s) => (
          <option key={s.id} value={s.id}>
            {s.label || s.name || s.scope_level}
          </option>
        ))}
      </select>
    </div>
  );
}
