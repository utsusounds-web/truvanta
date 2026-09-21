import { useEffect, useState } from "react";
import { getAdminPinStatus, unlockAdminPin } from "../api/tenants";

const SESSION_KEY = "truvanta_admin_pin_unlocked";

export default function AdminPinGate({ children }: { children: React.ReactNode }) {
  const [checking, setChecking] = useState(true);
  const [unlocked, setUnlocked] = useState(() => sessionStorage.getItem(SESSION_KEY) === "1");
  const [pinIsSet, setPinIsSet] = useState<boolean | null>(null);
  const [pin, setPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (unlocked) { setChecking(false); return; }
    getAdminPinStatus()
      .then((res) => setPinIsSet(res.pin_is_set))
      .catch(() => setPinIsSet(false))
      .finally(() => setChecking(false));
  }, [unlocked]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (pinIsSet === false && pin !== confirmPin) {
      setError("PINs don't match.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await unlockAdminPin(pin);
      if (res.status === "unlocked" || res.status === "set") {
        sessionStorage.setItem(SESSION_KEY, "1");
        setUnlocked(true);
      } else {
        setError(res.detail || "Wrong PIN.");
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Wrong PIN.");
    } finally {
      setSubmitting(false);
    }
  }

  if (checking) {
    return <div className="admin-pin-gate"><p>Loading…</p></div>;
  }

  if (unlocked) {
    return <>{children}</>;
  }

  return (
    <div className="admin-pin-gate">
      <form className="admin-pin-card" onSubmit={handleSubmit}>
        <div className="admin-mark-badge" style={{ marginBottom: 14 }}>ADMIN</div>
        <h2>{pinIsSet ? "Enter admin PIN" : "Set up an admin PIN"}</h2>
        <p className="admin-pin-hint">
          {pinIsSet
            ? "Quick-access unlock for this admin console."
            : "No PIN exists yet — whatever you set here becomes the admin console's access PIN. You can change it anytime from here once you're in."}
        </p>
        <input
          className="input"
          type="password"
          inputMode="numeric"
          placeholder="4-8 digit PIN"
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
          autoFocus
        />
        {pinIsSet === false && (
          <input
            className="input"
            type="password"
            inputMode="numeric"
            placeholder="Confirm PIN"
            value={confirmPin}
            onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, ""))}
            style={{ marginTop: 10 }}
          />
        )}
        {error && <p className="inline-error" style={{ marginTop: 10 }}>{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={submitting || pin.length < 4} style={{ marginTop: 16, width: "100%" }}>
          {submitting ? "Checking…" : pinIsSet ? "Unlock" : "Set PIN"}
        </button>
      </form>
    </div>
  );
}
