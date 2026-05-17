import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi, setupApi } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mfaOtp, setMfaOtp] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setupApi.status().then((s) => {
      if (s.needs_setup) navigate("/setup");
    }).catch(() => navigate("/setup"));
  }, [navigate]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const r = await authApi.login({
        username,
        password,
        mfa_otp: mfaOtp || undefined,
      });
      if (r.mfa_required) {
        setMfaRequired(true);
        return;
      }
      localStorage.setItem("access_token", r.access_token);
      await refresh();
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <div className="setup-page">
      <form className="setup-card card" onSubmit={submit}>
        <h1>Sign in</h1>
        <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label>
        {mfaRequired && (
          <label>MFA code<input value={mfaOtp} onChange={(e) => setMfaOtp(e.target.value)} placeholder="6-digit OTP" /></label>
        )}
        {error && <p className="setup-msg" style={{ color: "var(--danger)" }}>{error}</p>}
        <button type="submit" className="btn-primary" style={{ marginTop: "1rem", width: "100%" }}>Sign in</button>
        <p style={{ marginTop: "1rem", fontSize: "0.85rem" }}>
          <Link to="/setup">First-run setup</Link>
        </p>
      </form>
    </div>
  );
}

