import { Navigate, Route, Routes } from "react-router-dom";
import { SetupGate } from "./components/AppGate";
import Layout from "./components/Layout";
import SetupPage from "./pages/SetupPage";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import SettingsPage from "./pages/SettingsPage";
import SettingsRedirectPage from "./pages/SettingsRedirectPage";
import UsersPage from "./pages/UsersPage";
import RolesPage from "./pages/RolesPage";
import ModulesPage from "./pages/ModulesPage";
import OrganizationsPage from "./pages/OrganizationsPage";
import RFICenterPage from "./pages/RFICenterPage";
import EvidencePage from "./pages/EvidencePage";
import LogsPage from "./pages/LogsPage";
import FoundationListPage from "./pages/FoundationListPage";
import SolaceMemoryPage from "./pages/SolaceMemoryPage";
import SolacePersonasPage from "./pages/SolacePersonasPage";
import SolaceRemPage from "./pages/SolaceRemPage";
import AiProvidersPage from "./pages/AiProvidersPage";
import RedactionPage from "./pages/RedactionPage";
import SecurityOperationsPage from "./pages/SecurityOperationsPage";
import ProtectedRoute from "./components/ProtectedRoute";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("access_token");
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <SetupGate>
      <Routes>
        <Route path="/setup" element={<SetupPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route element={<ProtectedRoute />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/platform/users" element={<UsersPage />} />
          <Route path="/platform/roles" element={<RolesPage />} />
          <Route path="/platform/organizations" element={<OrganizationsPage />} />
          <Route path="/platform/modules" element={<ModulesPage />} />
          <Route path="/platform/settings" element={<SettingsPage />} />
          <Route path="/security/ldap" element={<SettingsRedirectPage />} />
          <Route path="/security/mfa" element={<SettingsRedirectPage />} />
          <Route path="/security/sessions" element={<SecurityOperationsPage defaultTab="sessions" />} />
          <Route path="/security/login-attempts" element={<SecurityOperationsPage defaultTab="attempts" />} />
          <Route path="/solace/ai-providers" element={<AiProvidersPage />} />
          <Route path="/solace/memory" element={<SolaceMemoryPage />} />
          <Route path="/solace/personas" element={<SolacePersonasPage />} />
          <Route path="/solace/rem" element={<SolaceRemPage />} />
          <Route path="/solace/llm-calls" element={<LogsPage defaultTab="llm" />} />
          <Route path="/compliance/rfi" element={<RFICenterPage />} />
          <Route path="/compliance/controls" element={<FoundationListPage title="Control Map" endpoint="/compliance/controls" />} />
          <Route path="/compliance/evidence" element={<EvidencePage />} />
          <Route path="/compliance/access-reviews" element={<FoundationListPage title="Access Reviews" endpoint="/compliance/access-reviews" />} />
          <Route path="/compliance/incidents" element={<FoundationListPage title="Incidents" endpoint="/compliance/incidents" />} />
          <Route path="/compliance/changes" element={<FoundationListPage title="Change Management" endpoint="/compliance/change-requests" />} />
          <Route path="/compliance/infra" element={<FoundationListPage title="Infrastructure Evidence" endpoint="/evidence/infra/applications" note="Sample: applications. Additional infra tables available via API." />} />
          <Route path="/compliance/appsec" element={<FoundationListPage title="AppSec Evidence" endpoint="/evidence/appsec/vulnerabilities" />} />
          <Route path="/compliance/redaction" element={<RedactionPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/logs/audit-trail" element={<LogsPage defaultTab="audit" />} />
          <Route path="/logs/login-events" element={<LogsPage defaultTab="login" />} />
          <Route path="/logs/admin-actions" element={<LogsPage defaultTab="admin" />} />
          <Route path="/logs/config-changes" element={<LogsPage defaultTab="config" />} />
          <Route path="/logs/permission-changes" element={<LogsPage defaultTab="permissions" />} />
          <Route path="/logs/llm-calls" element={<LogsPage defaultTab="llm" />} />
          <Route path="/logs/posture-violations" element={<LogsPage defaultTab="posture" />} />
          <Route path="/logs/system-errors" element={<LogsPage defaultTab="errors" />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </SetupGate>
  );
}
