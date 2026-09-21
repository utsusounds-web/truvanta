import { useState } from "react";
import { Link } from "react-router-dom";
import Field from "../components/Field";
import { requestPasswordReset } from "../api/resources";
import { extractErrorMessage } from "../lib/format";
import "./AuthPage.css";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await requestPasswordReset(email);
      setSubmitted(true);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Something went wrong. Try again."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-mark">TRUVANTA</div>
        <h1 className="display">Reset your password</h1>
        <p className="auth-subhead">Enter the email on your account and we'll send a reset link.</p>

        {submitted ? (
          <p style={{ fontSize: 16, color: "var(--ink-600)" }}>
            If that email has an account, a reset link is on its way — check your inbox
            (and spam folder). The link works once and expires after a while, so use it soon.
          </p>
        ) : (
          <form onSubmit={handleSubmit}>
            <Field label="Email">
              <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
            </Field>
            {error && <p className="onboarding-error">{error}</p>}
            <button type="submit" className="btn btn-primary" style={{ width: "100%" }} disabled={submitting}>
              {submitting ? "Sending…" : "Send reset link"}
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
