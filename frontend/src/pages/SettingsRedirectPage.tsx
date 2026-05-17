import { useLocation } from "react-router-dom";
import SettingsPage from "./SettingsPage";

export default function SettingsRedirectPage() {
  const loc = useLocation();
  const initialTab = loc.pathname.includes("mfa") ? "mfa" : "ldap";
  return <SettingsPage initialTab={initialTab} />;
}
