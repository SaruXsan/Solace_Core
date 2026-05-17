import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authApi, type ActiveScope } from "../api/client";
import { hasAllPermissions, hasAnyPermission, hasPermission } from "../auth/permissions";

type AuthState = {
  permissions: string[];
  isAdmin: boolean;
  displayName: string;
  loaded: boolean;
  activeScope: ActiveScope | null;
  availableScopes: ActiveScope[];
  refresh: () => Promise<void>;
  can: (permission: string) => boolean;
  canAny: (permissions: string[]) => boolean;
  canAll: (permissions: string[]) => boolean;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [permissions, setPermissions] = useState<string[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [activeScope, setActiveScope] = useState<ActiveScope | null>(null);
  const [availableScopes, setAvailableScopes] = useState<ActiveScope[]>([]);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setPermissions([]);
      setIsAdmin(false);
      setActiveScope(null);
      setAvailableScopes([]);
      setLoaded(true);
      return;
    }
    try {
      const me = await authApi.me();
      const perms = me.permissions?.length ? me.permissions : me.is_admin ? ["*"] : [];
      setPermissions(perms);
      setIsAdmin(me.is_admin);
      setDisplayName(me.display_name);
      setActiveScope(me.active_scope ?? null);
      setAvailableScopes(me.available_scopes ?? []);
      localStorage.setItem("display_name", me.display_name);
    } catch {
      setPermissions([]);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo<AuthState>(
    () => ({
      permissions,
      isAdmin,
      displayName,
      loaded,
      activeScope,
      availableScopes,
      refresh,
      can: (p) => hasPermission(permissions, p),
      canAny: (ps) => hasAnyPermission(permissions, ps),
      canAll: (ps) => hasAllPermissions(permissions, ps),
    }),
    [permissions, isAdmin, displayName, loaded, activeScope, availableScopes, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
