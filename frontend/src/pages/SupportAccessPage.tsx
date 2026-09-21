import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { getBusiness, grantSupportAccess, revokeSupportAccess } from "../api/tenants";
import { formatDate, extractErrorMessage } from "../lib/format";

const DURATION_OPTIONS = [
  { label: "24 hours", hours: 24 },
  { label: "3 days", hours: 72 },
  { label: "7 days", hours: 168 },
];

export default function SupportAccessPage() {
  const { isOwnerOrAdmin } = useAuth();
  const allowed = isOwnerOrAdmin();
  const businessId = localStorage.getItem("sbos_business_id") || "";
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [hours, setHours] = useState(24);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    if (!businessId) { setLoading(false); return; }
    getBusiness(businessId)
      .then((b) => setExpiresAt(b.support_access_expires_at))
      .finally(() => setLoading(false));
  }
  useEffect(refresh, [businessId]);

  const isActive = !!expiresAt && new Date(expiresAt).getTime() > Date.now();

  async function handleGrant() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await grantSupportAccess(hours);
      setExpiresAt(res.support_access_expires_at);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't grant access."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRevoke() {
    if (!window.confirm("Revoke platform support access now? This immediately ends any support session in progress.")) return;
    setSubmitting(true);
    setError(null);
    try {
      await revokeSupportAccess();
      setExpiresAt(null);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't revoke access."));
    } finally {
      setSubmitting(false);
    }
  }

  if (!allowed) {
    return (
      <div>
        <PageHeader title="Platform Support Access" subtitle="Owner/admin only." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Platform Support Access"
        subtitle="Nothing here happens without your say-so. Truvanta staff can only log into your business to help with support during a window you explicitly open below — and you can end it instantly, any time."
      />

      <div className="card" style={{ padding: 24, maxWidth: 520 }}>
        {loading ? (
          <div className="loading-row">Loading…</div>
        ) : isActive ? (
          <>
            <p style={{ fontSize: 15, marginBottom: 16 }}>
              <span className="badge badge--good">Access open</span> until <strong>{formatDate(expiresAt!)}</strong>.
              Any support login during this window shows up in your{" "}
              <Link to="/activity-log">Activity Log</Link> like any other action.
            </p>
            <button className="btn btn-primary" onClick={handleRevoke} disabled={submitting}>
              {submitting ? "Revoking…" : "Revoke access now"}
            </button>
          </>
        ) : (
          <>
            <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
              No support access is currently open. Grant a short window only if you've asked Truvanta
              support for help and they've asked you to do this.
            </p>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 16 }}>
              <select className="input" value={hours} onChange={(e) => setHours(Number(e.target.value))} style={{ maxWidth: 160 }}>
                {DURATION_OPTIONS.map((o) => (
                  <option key={o.hours} value={o.hours}>{o.label}</option>
                ))}
              </select>
              <button className="btn btn-primary" onClick={handleGrant} disabled={submitting}>
                {submitting ? "Granting…" : "Grant access"}
              </button>
            </div>
          </>
        )}
        {error && <p className="inline-error">{error}</p>}
      </div>
    </div>
  );
}
