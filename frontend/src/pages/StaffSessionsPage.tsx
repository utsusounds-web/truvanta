import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import { useAuth } from "../context/AuthContext";
import { getBusinessStaffSessions, revokeBusinessStaffSession, type StaffSession } from "../api/sessions";
import { formatDate, extractErrorMessage } from "../lib/format";

export default function StaffSessionsPage() {
  const { isOwnerOrAdmin } = useAuth();
  const allowed = isOwnerOrAdmin();
  const [sessions, setSessions] = useState<StaffSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  function refresh() {
    if (!allowed) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    getBusinessStaffSessions()
      .then(setSessions)
      .catch((err) => setError(extractErrorMessage(err, "Couldn't load staff sessions.")))
      .finally(() => setLoading(false));
  }
  useEffect(refresh, [allowed]);

  async function handleRevoke(id: string) {
    setRevokingId(id);
    try {
      await revokeBusinessStaffSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't sign that device out."));
    } finally {
      setRevokingId(null);
    }
  }

  if (!allowed) {
    return (
      <div>
        <PageHeader title="Staff Sessions" subtitle="Where every staff member is currently signed in." />
        <EmptyState
          title="Owner/admin only"
          subtitle="Seeing where staff are logged in, and from what device, is restricted to owners and admins."
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Staff Sessions"
        subtitle="Every device your staff are currently signed in on, which branch they belong to, and when they were last active. Sign a device out immediately if something looks wrong."
      />

      {error && <p className="inline-error">{error}</p>}

      <div className="card">
        {loading ? (
          <div className="loading-row">Loading…</div>
        ) : sessions.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No one is currently signed in" /></div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Staff</th><th>Role</th><th>Branch</th><th>Device</th><th>IP address</th>
                <th>Last active</th><th></th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.id}>
                  <td>
                    {s.user_name}
                    <div style={{ fontSize: 14, color: "var(--ink-300)" }}>{s.user_email}</div>
                  </td>
                  <td>{s.role}</td>
                  <td>{s.branches.join(", ")}</td>
                  <td>{s.device_label || "Unknown device"}</td>
                  <td>{s.ip_address || "—"}</td>
                  <td>{formatDate(s.last_seen_at)}</td>
                  <td>
                    <button className="btn btn-ghost" disabled={revokingId === s.id} onClick={() => handleRevoke(s.id)}>
                      {revokingId === s.id ? "Signing out…" : "Sign out"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
