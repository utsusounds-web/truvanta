import { useEffect, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Field from "../components/Field";
import GoogleSignInButton from "../components/GoogleSignInButton";
import { getPlatformBranding } from "../api/tenants";
import { applyAccentColor } from "../lib/accentColor";
import { extractErrorMessage } from "../lib/format";
import { useBackendHealth } from "../lib/useBackendHealth";
import { API_BASE_URL } from "../api/client";
import "./AuthPage.css";

export default function AuthPage() {
  const { login, loginWithGoogle, register, verifyTwoFactorLogin } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // A branch signup-code join link (Branches page → "Copy join link")
  // lands here first since the person doesn't have an account yet —
  // carry the code through registration/login into Onboarding so they
  // never have to re-type it.
  const joinCode = searchParams.get("code");
  const onboardingPath = joinCode ? `/onboarding?code=${encodeURIComponent(joinCode)}` : "/onboarding";
  const health = useBackendHealth();
  const [mode, setMode] = useState<"login" | "register">("register");
  const [form, setForm] = useState({
    firstName: "", lastName: "", username: "", email: "", password: "", confirmPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [googleClientId, setGoogleClientId] = useState<string | null>(null);

  useEffect(() => {
    getPlatformBranding().then((b) => {
      if (b.universal_color) applyAccentColor(b.universal_color);
      setGoogleClientId(b.google_oauth_client_id || null);
    }).catch(() => {});
  }, []);

  async function handleGoogleToken(idToken: string) {
    setError(null);
    setSubmitting(true);
    try {
      const result = await loginWithGoogle(idToken);
      if (result.requires2FA) {
        setPendingPreAuthToken(result.preAuthToken);
      } else if (result.isStaff) {
        navigate("/admin");
      } else {
        navigate(result.memberships.length > 0 ? "/dashboard" : onboardingPath);
      }
    } catch (err: any) {
      setError(extractErrorMessage(err, "Google sign-in didn't work. Try again, or use email below."));
    } finally {
      setSubmitting(false);
    }
  }

  const [pendingPreAuthToken, setPendingPreAuthToken] = useState<string | null>(null);
  const [twoFactorCode, setTwoFactorCode] = useState("");

  function update(field: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
    if (fieldErrors[field]) setFieldErrors((fe) => ({ ...fe, [field]: "" }));
  }

  function validate(): boolean {
    const errors: Record<string, string> = {};
    if (mode === "register") {
      if (!form.firstName.trim()) errors.firstName = "Required.";
      if (!form.lastName.trim()) errors.lastName = "Required.";
      if (!form.username.trim()) errors.username = "Required.";
      if (form.password.length < 8) errors.password = "At least 8 characters.";
      if (form.confirmPassword !== form.password) errors.confirmPassword = "Passwords don't match.";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "register") {
        await register({
          email: form.email, username: form.username, password: form.password,
          first_name: form.firstName, last_name: form.lastName,
        });
        navigate(onboardingPath);
      } else {
        const result = await login(form.email, form.password);
        if (result.requires2FA) {
          setPendingPreAuthToken(result.preAuthToken);
        } else if (result.isStaff) {
          // Platform staff never see the business app at all — sent
          // straight to the admin panel, never mixed into a business
          // owner's dashboard/nav even if this account also happens to
          // hold a business membership.
          navigate("/admin");
        } else {
          // Only a genuinely new account (registered but never finished
          // setting up a business) goes to onboarding. Everyone else goes
          // straight back to their existing data.
          navigate(result.memberships.length > 0 ? "/dashboard" : onboardingPath);
        }
      }
    } catch (err: any) {
      setError(extractErrorMessage(err, "Something went wrong. Check your details and try again."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTwoFactorSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!pendingPreAuthToken || twoFactorCode.length < 6) return;
    setSubmitting(true);
    setError(null);
    try {
      const { memberships, isStaff } = await verifyTwoFactorLogin(pendingPreAuthToken, twoFactorCode);
      navigate(isStaff ? "/admin" : memberships.length > 0 ? "/dashboard" : onboardingPath);
    } catch (err: any) {
      setError(extractErrorMessage(err, "That code didn't work — check your authenticator app and try again."));
      setTwoFactorCode("");
    } finally {
      setSubmitting(false);
    }
  }

  if (pendingPreAuthToken) {
    return (
      <div className="auth-shell">
        <div className="auth-card">
          <div className="auth-mark">TRUVANTA</div>
          <h1 className="display">Enter your code</h1>
          <p className="auth-subhead">
            Open your authenticator app and enter the 6-digit code for this account.
          </p>
          <form onSubmit={handleTwoFactorSubmit}>
            <Field label="Authentication code">
              <input
                className="input" inputMode="numeric" autoComplete="one-time-code" autoFocus
                maxLength={6} value={twoFactorCode}
                onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, ""))}
              />
            </Field>
            {error && <p className="onboarding-error">{error}</p>}
            <button className="btn btn-primary" type="submit" style={{ width: "100%" }} disabled={submitting || twoFactorCode.length < 6}>
              {submitting ? "Verifying…" : "Verify & sign in"}
            </button>
          </form>
          <button
            className="btn btn-ghost" style={{ width: "100%", marginTop: 10 }}
            onClick={() => { setPendingPreAuthToken(null); setTwoFactorCode(""); setError(null); }}
          >
            Back to sign in
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        {health === "unreachable" && (
          <div className="auth-health-banner">
            <strong>Can't reach the backend</strong>
            <p>
              Nothing will work until this is fixed. The app is trying to reach{" "}
              <code>{API_BASE_URL}</code> and getting no response. Confirm the backend
              is running, then see <code>RUNNING.md → Troubleshooting</code> for the
              most common causes (dependencies not installed, wrong port, or opening
              this page from a phone/second device — <code>localhost</code> won't work
              there).
            </p>
          </div>
        )}

        <div className="auth-mark">TRUVANTA</div>
        <h1 className="display">{mode === "register" ? "Create your account" : "Welcome back"}</h1>
        <p className="auth-subhead">
          {mode === "register" ? "Set up your account, then your business." : "Sign in to continue."}
        </p>

        {googleClientId && (
          <>
            <div style={{ margin: "16px 0" }}>
              <GoogleSignInButton clientId={googleClientId} onToken={handleGoogleToken} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "18px 0", color: "var(--ink-300)", fontSize: 14.5 }}>
              <div style={{ flex: 1, height: 1, background: "var(--line)" }} />
              or continue with email
              <div style={{ flex: 1, height: 1, background: "var(--line)" }} />
            </div>
          </>
        )}

        <form onSubmit={handleSubmit} noValidate>
          {mode === "register" && (
            <div className="auth-name-row">
              <Field label="First name" error={fieldErrors.firstName}>
                <input className="input" value={form.firstName} onChange={(e) => update("firstName", e.target.value)} autoComplete="given-name" />
              </Field>
              <Field label="Last name" error={fieldErrors.lastName}>
                <input className="input" value={form.lastName} onChange={(e) => update("lastName", e.target.value)} autoComplete="family-name" />
              </Field>
            </div>
          )}
          {mode === "register" && (
            <Field label="Username" error={fieldErrors.username} hint="Just for signing in — pick anything, like your shop name.">
              <input className="input" value={form.username} onChange={(e) => update("username", e.target.value)} autoComplete="username" />
            </Field>
          )}
          <Field label="Email" required hint="You'll use this to sign in and to reset your password if you forget it.">
            <input className="input" type="email" value={form.email} onChange={(e) => update("email", e.target.value)} required autoComplete="email" />
          </Field>
          <Field label="Password" error={fieldErrors.password} required hint="At least 8 characters.">
            <div className="auth-password-row">
              <input
                className="input" type={showPassword ? "text" : "password"} value={form.password}
                onChange={(e) => update("password", e.target.value)} required minLength={8}
                autoComplete={mode === "register" ? "new-password" : "current-password"}
              />
              <button type="button" className="auth-password-toggle" onClick={() => setShowPassword((s) => !s)} tabIndex={-1}>
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </Field>
          {mode === "register" && (
            <Field label="Verify password" error={fieldErrors.confirmPassword}>
              <input
                className="input" type={showPassword ? "text" : "password"} value={form.confirmPassword}
                onChange={(e) => update("confirmPassword", e.target.value)} required minLength={8} autoComplete="new-password"
              />
            </Field>
          )}
          {mode === "login" && (
            <Link to="/forgot-password" className="auth-forgot-link">
              Forgot password?
            </Link>
          )}

          {error && <p className="onboarding-error">{error}</p>}

          <button type="submit" className="btn btn-primary" style={{ width: "100%" }} disabled={submitting}>
            {submitting ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"}
          </button>
        </form>

        <button
          type="button"
          className="auth-switch"
          onClick={() => { setMode(mode === "register" ? "login" : "register"); setFieldErrors({}); setError(null); }}
        >
          {mode === "register" ? "Already have an account? Sign in" : "New here? Create an account"}
        </button>

        {mode === "login" && (
          <p style={{ fontSize: 14, color: "var(--ink-300)", textAlign: "center", marginTop: 16 }}>
            Truvanta platform staff sign in here too — you'll be taken straight to the admin panel.
          </p>
        )}
      </div>
    </div>
  );
}
