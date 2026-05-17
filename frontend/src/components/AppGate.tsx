import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

type Health = {
  setup_complete: boolean;
  database_configured: boolean;
};

export function useHealth() {
  const [health, setHealth] = useState<Health | null>(null);
  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ setup_complete: false, database_configured: false }));
  }, []);
  return health;
}

export function SetupGate({ children }: { children: React.ReactNode }) {
  const health = useHealth();
  const loc = useLocation();
  if (health === null) {
    return (
      <div className="setup-page">
        <p className="subtitle">Loading...</p>
      </div>
    );
  }
  if (!health.setup_complete && loc.pathname !== "/setup") {
    return <Navigate to="/setup" replace />;
  }
  if (health.setup_complete && loc.pathname === "/setup") {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
