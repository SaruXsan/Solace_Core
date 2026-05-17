import { Link } from "react-router-dom";

export default function AccessDeniedPage() {
  return (
    <div className="card" style={{ maxWidth: "32rem" }}>
      <h1 className="page-title">Access denied</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>
        You do not have permission to view this page. Contact your administrator if you need access.
      </p>
      <Link to="/" className="btn-primary" style={{ display: "inline-block", textDecoration: "none" }}>
        Return to dashboard
      </Link>
    </div>
  );
}
