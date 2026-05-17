import { Outlet, useLocation } from "react-router-dom";
import { routeRequiresPermission } from "../auth/routePermissions";
import { hasAnyPermission, hasPermission } from "../auth/permissions";
import { useAuth } from "../context/AuthContext";
import AccessDeniedPage from "../pages/AccessDeniedPage";

export default function ProtectedRoute() {
  const { permissions, loaded } = useAuth();
  const { pathname } = useLocation();
  const rule = routeRequiresPermission(pathname);

  if (!loaded) {
    return <p className="status-msg" style={{ padding: "2rem" }}>Loading…</p>;
  }

  if (rule) {
    const allowed = Array.isArray(rule)
      ? hasAnyPermission(permissions, rule)
      : hasPermission(permissions, rule);
    if (!allowed) {
      return <AccessDeniedPage />;
    }
  }

  return <Outlet />;
}
