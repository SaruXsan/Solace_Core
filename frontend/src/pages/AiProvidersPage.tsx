import { useEffect, useState } from "react";
import { settingsApi, type AiProvider } from "../api/platform";
import { useAuth } from "../context/AuthContext";
import "../components/forms.css";

export default function AiProvidersPage() {
  const { can } = useAuth();
  const [providers, setProviders] = useState<AiProvider[]>([]);
  const [msg, setMsg] = useState("");

  async function load() {
    setProviders(await settingsApi.aiProviders.list());
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <h1 className="page-title">AI Providers</h1>
      <p className="status-msg">Foundation registry â€?OpenAI and Ollama. Advanced Solace chat not built.</p>
      {can("ai_providers.read") && !can("ai_providers.update") && (
        <p className="status-msg">You have read-only access.</p>
      )}
      {msg && <p className="status-msg ok">{msg}</p>}
      <div className="card">
        <table className="data-table">
          <thead><tr><th>Provider</th><th>Type</th><th>External</th><th>Enabled</th><th></th></tr></thead>
          <tbody>
            {providers.map((p) => (
              <tr key={p.provider_code}>
                <td>{p.display_name}</td>
                <td>{p.provider_type}</td>
                <td>{p.is_external ? "Yes" : "No"}</td>
                <td>{p.is_enabled ? "Yes" : "No"}</td>
                <td>
                  <button
                    className="btn-secondary"
                    disabled={!can("ai_providers.update")}
                    title={can("ai_providers.update") ? undefined : "Requires ai_providers.update"}
                    onClick={async () => {
                      await settingsApi.aiProviders.patch(p.provider_code, !p.is_enabled);
                      setMsg("Provider updated");
                      load();
                    }}
                  >
                    {p.is_enabled ? "Disable" : "Enable"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
