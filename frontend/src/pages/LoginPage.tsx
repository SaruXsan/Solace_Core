import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi, setupApi } from "../api/client";
import { useAuth } from "../context/AuthContext";

type MfaState = {
  challengeId: string;
  destinationMasked: string;
  expiresAt: string;
};

export default function LoginPage() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mfaOtp, setMfaOtp] = useState("");
  const [mfa, setMfa] = useState<MfaState | null>(null);
  const [cooldown, setCooldown] = useState(0);
  const [attemptsHint, setAttemptsHint] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setupApi.status().then((s) => {
      if (s.needs_setup) navigate("/setup");
    }).catch(() => navigate("/setup"));
  }, [navigate]);

  useEffect(() => {
    if (!mfa?.challengeId) return;
    const poll = () => {
      authApi.mfaStatus(mfa.challengeId).then((s) => {
        setCooldown(s.cooldown_seconds_remaining);
        if (s.expired) setError("OTP expired. Request a new code.");
      }).catch(() => {});
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => clearInterval(id);
  }, [mfa?.challengeId]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => Math.max(0, c - 1)), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  async function submitPassword(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const r = await authApi.login({ username, password });
      if (r.mfa_required && r.challenge_id) {
        setMfa({
          challengeId: r.challenge_id,
          destinationMasked: r.destination_masked || "your email",
          expiresAt: r.expires_at || "",
        });
        setMfaOtp("");
        return;
      }
      localStorage.setItem("access_token", r.access_token);
      await refresh();
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  async function submitOtp(e: React.FormEvent) {
    e.preventDefault();
    if (!mfa) return;
    setError("");
    setAttemptsHint("");
    setLoading(true);
    try {
      const r = await authApi.mfaVerify({ challenge_id: mfa.challengeId, otp: mfaOtp });
      localStorage.setItem("access_token", r.access_token);
      await refresh();
      navigate("/");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Verification failed";
      setError(msg);
      const match = msg.match(/(\d+) attempts remaining/);
      if (match) setAttemptsHint(`${match[1]} attempts remaining`);
    } finally {
      setLoading(false);
    }
  }

  async function resendOtp() {
    if (!mfa || cooldown > 0) return;
    setError("");
    try {
      const s = await authApi.mfaResend({ challenge_id: mfa.challengeId });
      setCooldown(s.cooldown_seconds_remaining);
      setMfaOtp("");
      setAttemptsHint("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resend failed");
    }
  }

  if (mfa) {
    return (
      <div className="setup-page">
        <form className="setup-card card" onSubmit={submitOtp}>
          <h1>Verify identity</h1>
          <p className="status-msg">
            A verification code was sent to {mfa.destinationMasked}.
          </p>
          <label>
            6-digit code
            <input
              value={mfaOtp}
              onChange={(e) => setMfaOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
              inputMode="numeric"
              autoComplete="one-time-code"
              autoFocus
            />
          </label>
          {attemptsHint && <p className="status-msg warn">{attemptsHint}</p>}
          {error && <p className="setup-msg" style={{ color: "var(--danger)" }}>{error}</p>}
          <button type="submit" className="btn-primary" style={{ marginTop: "1rem", width: "100%" }} disabled={loading || mfaOtp.length < 6}>
            Verify
          </button>
          <button
            type="button"
            className="btn-secondary"
            style={{ marginTop: "0.5rem", width: "100%" }}
            disabled={cooldown > 0}
            onClick={resendOtp}
          >
            {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
          </button>
          <button
            type="button"
            className="btn-secondary"
            style={{ marginTop: "0.5rem", width: "100%" }}
            onClick={() => { setMfa(null); setMfaOtp(""); setError(""); }}
          >
            Back to sign in
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="setup-page">
      <form className="setup-card card" onSubmit={submitPassword}>
        <h1>Sign in</h1>
        <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label>
        {error && <p className="setup-msg" style={{ color: "var(--danger)" }}>{error}</p>}
        <button type="submit" className="btn-primary" style={{ marginTop: "1rem", width: "100%" }} disabled={loading}>
          Sign in
        </button>
        <p style={{ marginTop: "1rem", fontSize: "0.85rem" }}>
          <Link to="/setup">First-run setup</Link>
        </p>
      </form>
    </div>
  );
}
