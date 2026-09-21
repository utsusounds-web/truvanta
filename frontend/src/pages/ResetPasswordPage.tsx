import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import Field from "../components/Field";
import { confirmPasswordReset } from "../api/resources";
import { extractErrorMessage } from "../lib/format";
import "./AuthPage.css";

export default function ResetPasswordPage() {
  const { uid, token } = useParams<{ uid: string; token: string }>();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    if (!uid || !token) {
      setError("This reset link looks incomplete.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await confirmPasswordReset(uid, token, password);
      setDone(true);
      setTimeout(() => navigate("/auth"), 2000);
    } catch (err: any) {
      setError(extractErrorMessage(err, "That reset link is invalid or has expired."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-mark">TRUVANTA</div>
        <h1 className="display">Set a new password</h1>

        {done ? (
          <p style={{ fontSize: 16, color: "var(--green-600)" }}>
            Password updated — taking you to sign in…
          </p>
        ) : (
          <form onSubmit={handleSubmit}>
            <Field label="New password" hint="At least 8 characters">
              <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoFocus />
            </Field>
            <Field label="Confirm new password">
              <input className="input" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required minLength={8} />
            </Field>
            {error && <p className="onboarding-error">{error}</p>}
            <button type="submit" className="btn btn-primary" style={{ width: "100%" }} disabled={submitting}>
              {submitting ? "Saving…" : "Set new password"}
            </button>
          </form>
        )}

        <Link to="/auth" className="auth-switch" style={{ display: "inline-block", marginTop: 18 }}>
          Back to sign in
        </Link>
      </div>
    </div>
  );
}
