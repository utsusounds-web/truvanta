import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import LogoDropzone from "../components/LogoDropzone";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage, formatDate } from "../lib/format";
import { getSessions, revokeSession, revokeOtherSessions } from "../api/sessions";
import type { UserSession } from "../api/sessions";
import { setupTwoFactor, confirmTwoFactor, disableTwoFactor } from "../api/twoFactor";
import { getDuressPasswordStatus, setDuressPassword, removeDuressPassword } from "../api/duress";

export default function ProfilePage() {
  const { user, updateProfile } = useAuth();
  const [firstName, setFirstName] = useState(user?.first_name || "");
  const [lastName, setLastName] = useState(user?.last_name || "");
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(user?.profile_photo || null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const currentSessionId = localStorage.getItem("sbos_session_id");

  function refreshSessions() {
    setSessionsLoading(true);
    getSessions().then(setSessions).finally(() => setSessionsLoading(false));
  }
  useEffect(refreshSessions, []);

  async function handleRevoke(id: string) {
    setRevokingId(id);
    try {
      await revokeSession(id);
      refreshSessions();
    } finally {
      setRevokingId(null);
    }
  }

  async function handleRevokeOthers() {
    if (!window.confirm("Sign out every other device? This one stays signed in.")) return;
    await revokeOtherSessions(currentSessionId);
    refreshSessions();
  }

  function handlePhotoSelect(file: File) {
    setPhotoFile(file);
    setPhotoPreview(URL.createObjectURL(file));
  }

  async function handleSave() {
    setSubmitting(true);
    setError(null);
    setSaved(false);
    try {
      const fd = new FormData();
      fd.append("first_name", firstName);
      fd.append("last_name", lastName);
      if (photoFile) fd.append("profile_photo", photoFile);
      await updateProfile(fd);
      setSaved(true);
      setPhotoFile(null);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save your profile."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <PageHeader title="My Profile" subtitle="Your name and photo, shown wherever your account appears in the app." />

      <div className="card" style={{ padding: 24, maxWidth: 480 }}>
        <Field label="Photo">
          <LogoDropzone
            previewUrl={photoPreview}
            onSelect={handlePhotoSelect}
            onClear={() => { setPhotoFile(null); setPhotoPreview(null); }}
          />
        </Field>
        <Field label="First name">
          <input className="input" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
        </Field>
        <Field label="Last name">
          <input className="input" value={lastName} onChange={(e) => setLastName(e.target.value)} />
        </Field>
        <Field label="Email" hint="Contact support to change your email">
          <input className="input" value={user?.email || ""} disabled />
        </Field>

        {error && <p className="inline-error">{error}</p>}
        {saved && !error && <p style={{ color: "var(--green-600)", fontSize: 15, marginBottom: 14 }}>Saved.</p>}
        <button className="btn btn-primary" onClick={handleSave} disabled={submitting}>
          {submitting ? "Saving…" : "Save profile"}
        </button>
      </div>

      <div className="card" style={{ padding: 24, maxWidth: 480, marginTop: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div className="section-title">Active sessions</div>
          {sessions.length > 1 && (
            <button className="btn btn-ghost" onClick={handleRevokeOthers}>Sign out other devices</button>
          )}
        </div>
        {sessionsLoading ? (
          <div className="loading-row">Loading…</div>
        ) : sessions.length === 0 ? (
          <p style={{ fontSize: 14.5, color: "var(--ink-300)" }}>No active sessions found.</p>
        ) : (
          <div>
            {sessions.map((s) => (
              <div key={s.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--paper-100)" }}>
                <div>
                  <div style={{ fontSize: 15.5, fontWeight: 600 }}>
                    {s.device_label}
                    {s.id === currentSessionId && <span className="badge badge--good" style={{ marginLeft: 8 }}>this device</span>}
                  </div>
                  <div style={{ fontSize: 14, color: "var(--ink-300)" }}>
                    {s.ip_address ? `${s.ip_address} · ` : ""}Last active {formatDate(s.last_seen_at)}
                  </div>
                </div>
                {s.id !== currentSessionId && (
                  <button className="btn btn-ghost" onClick={() => handleRevoke(s.id)} disabled={revokingId === s.id}>
                    {revokingId === s.id ? "Revoking…" : "Sign out"}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <TwoFactorCard enabled={!!user?.two_factor_enabled} />
      <DuressPasswordCard />
    </div>
  );
}

function TwoFactorCard({ enabled: initiallyEnabled }: { enabled: boolean }) {
  const { loadMe } = useAuth();
  const [enabled, setEnabled] = useState(initiallyEnabled);
  const [step, setStep] = useState<"idle" | "setup" | "disable">("idle");
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [secret, setSecret] = useState("");
  const [pendingToken, setPendingToken] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function startSetup() {
    setError(null);
    const res = await setupTwoFactor();
    setQrCode(res.qr_code);
    setSecret(res.secret);
    setPendingToken(res.pending_token);
    setStep("setup");
  }

  async function handleConfirm() {
    setSubmitting(true);
    setError(null);
    try {
      await confirmTwoFactor(pendingToken, code);
      setEnabled(true);
      setStep("idle");
      setCode("");
      await loadMe();
    } catch (err: any) {
      setError(extractErrorMessage(err, "That code didn't work. Check the time on your phone and try again."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDisable() {
    setSubmitting(true);
    setError(null);
    try {
      await disableTwoFactor(password);
      setEnabled(false);
      setStep("idle");
      setPassword("");
      await loadMe();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't turn off two-factor authentication."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ padding: 24, maxWidth: 480, marginTop: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div className="section-title">Two-factor authentication</div>
        <span className={`badge ${enabled ? "badge--good" : "badge--neutral"}`}>{enabled ? "on" : "off"}</span>
      </div>
      <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginBottom: 14 }}>
        Adds a second step to signing in — a 6-digit code from an authenticator app
        (Google Authenticator, Authy, etc.) — so a stolen password alone isn't enough
        to get into your account.
      </p>

      {step === "idle" && !enabled && (
        <button className="btn btn-primary" onClick={startSetup}>Turn on</button>
      )}
      {step === "idle" && enabled && (
        <button className="btn btn-ghost" onClick={() => setStep("disable")}>Turn off</button>
      )}

      {step === "setup" && (
        <div>
          <p style={{ fontSize: 15, marginBottom: 10 }}>
            Scan this with your authenticator app, then enter the 6-digit code it shows.
          </p>
          {qrCode && <img src={qrCode} alt="2FA QR code" style={{ width: 180, height: 180, marginBottom: 10 }} />}
          <p style={{ fontSize: 13.5, color: "var(--ink-300)", marginBottom: 10 }}>
            Can't scan? Enter this code manually: <code>{secret}</code>
          </p>
          <Field label="6-digit code">
            <input className="input" inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
          </Field>
          {error && <p className="inline-error">{error}</p>}
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-primary" onClick={handleConfirm} disabled={submitting || code.length < 6}>
              {submitting ? "Confirming…" : "Confirm & turn on"}
            </button>
            <button className="btn btn-ghost" onClick={() => { setStep("idle"); setError(null); }}>Cancel</button>
          </div>
        </div>
      )}

      {step === "disable" && (
        <div>
          <Field label="Confirm your password">
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          {error && <p className="inline-error">{error}</p>}
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-primary" onClick={handleDisable} disabled={submitting || !password}>
              {submitting ? "Turning off…" : "Turn off 2FA"}
            </button>
            <button className="btn btn-ghost" onClick={() => { setStep("idle"); setError(null); }}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

function DuressPasswordCard() {
  const [isSetUp, setIsSetUp] = useState<boolean | null>(null);
  const [mode, setMode] = useState<"idle" | "setup" | "remove">("idle");
  const [currentPassword, setCurrentPassword] = useState("");
  const [duressPassword, setDuressPassword2] = useState("");
  const [duressPasswordConfirm, setDuressPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getDuressPasswordStatus().then((r) => setIsSetUp(r.is_set_up)).catch(() => setIsSetUp(false));
  }, []);

  function resetForm() {
    setMode("idle"); setCurrentPassword(""); setDuressPassword2(""); setDuressPasswordConfirm(""); setError(null);
  }

  async function handleSave() {
    if (duressPassword !== duressPasswordConfirm) {
      setError("The two entries don't match.");
      return;
    }
    setSubmitting(true); setError(null);
    try {
      await setDuressPassword(currentPassword, duressPassword);
      setIsSetUp(true);
      resetForm();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save that."));
    } finally { setSubmitting(false); }
  }

  async function handleRemove() {
    setSubmitting(true); setError(null);
    try {
      await removeDuressPassword(currentPassword);
      setIsSetUp(false);
      resetForm();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't remove it."));
    } finally { setSubmitting(false); }
  }

  return (
    <div className="card" style={{ padding: 24, maxWidth: 480, marginTop: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div className="section-title">Silent duress password</div>
        {isSetUp !== null && <span className={`badge ${isSetUp ? "badge--good" : "badge--neutral"}`}>{isSetUp ? "set up" : "not set up"}</span>}
      </div>
      <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginBottom: 14 }}>
        A second password you can use instead of your real one if you're ever forced to log in under
        threat. It logs you in completely normally — nothing on screen looks different — while quietly
        alerting the business's other owners/admins that something may be wrong.
      </p>
      <p style={{ fontSize: 13.5, color: "var(--ink-300)", marginBottom: 14, fontStyle: "italic" }}>
        Worth remembering: anyone who can see this screen can also read this explanation. Set it up
        somewhere private, and choose a password you can recall calmly under pressure.
      </p>

      {mode === "idle" && (
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-primary" onClick={() => setMode("setup")}>{isSetUp ? "Change it" : "Set it up"}</button>
          {isSetUp && <button className="btn btn-ghost" onClick={() => setMode("remove")}>Remove</button>}
        </div>
      )}

      {mode === "setup" && (
        <div>
          <Field label="Your current (real) password">
            <input className="input" type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
          </Field>
          <Field label="New duress password" hint="Must be different from your real password, at least 8 characters">
            <input className="input" type="password" value={duressPassword} onChange={(e) => setDuressPassword2(e.target.value)} />
          </Field>
          <Field label="Confirm duress password">
            <input className="input" type="password" value={duressPasswordConfirm} onChange={(e) => setDuressPasswordConfirm(e.target.value)} />
          </Field>
          {error && <p className="inline-error">{error}</p>}
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-primary" onClick={handleSave} disabled={submitting || !currentPassword || !duressPassword}>
              {submitting ? "Saving…" : "Save"}
            </button>
            <button className="btn btn-ghost" onClick={resetForm}>Cancel</button>
          </div>
        </div>
      )}

      {mode === "remove" && (
        <div>
          <Field label="Confirm your current password">
            <input className="input" type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
          </Field>
          {error && <p className="inline-error">{error}</p>}
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-primary" onClick={handleRemove} disabled={submitting || !currentPassword}>
              {submitting ? "Removing…" : "Remove it"}
            </button>
            <button className="btn btn-ghost" onClick={resetForm}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
