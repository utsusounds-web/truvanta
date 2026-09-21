import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import { useBusiness } from "../context/BusinessContext";
import { getNotifications, checkOverdueDebts, checkLowStock, sendDailySummary, markAllNotificationsRead } from "../api/resources";
import type { AppNotification } from "../api/types";
import { formatDate } from "../lib/format";

export default function NotificationsPage() {
  const navigate = useNavigate();
  const { activeBranchId } = useBusiness();
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [checkMessage, setCheckMessage] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    getNotifications().then(setNotifications).finally(() => setLoading(false));
  }
  useEffect(refresh, []);
  useEffect(() => {
    // Marking read on visit (not per-item) — this is a notice feed a
    // trader glances down, not an inbox they triage message by
    // message. Fire-and-forget: the badge clearing a beat late is
    // harmless, unlike blocking the page on it.
    markAllNotificationsRead().catch(() => {});
  }, []);

  async function handleCheckOverdue() {
    setChecking(true);
    setCheckMessage(null);
    try {
      const result = await checkOverdueDebts(activeBranchId || undefined);
      setCheckMessage(result.detail || "Alert sent — check the list below.");
      refresh();
    } finally {
      setChecking(false);
    }
  }

  async function handleCheckLowStock() {
    setChecking(true);
    setCheckMessage(null);
    try {
      const result = await checkLowStock(activeBranchId || undefined);
      setCheckMessage(result.detail || "Alert sent — check the list below.");
      refresh();
    } finally {
      setChecking(false);
    }
  }

  async function handleSendSummary() {
    if (!activeBranchId) return;
    setChecking(true);
    setCheckMessage(null);
    try {
      await sendDailySummary(activeBranchId);
      setCheckMessage("Today's summary sent.");
      refresh();
    } finally {
      setChecking(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Notifications"
        subtitle="Critical and important alerts — delivered to WhatsApp and email when configured in Settings, and always kept here."
        actions={
          <>
            <button className="btn btn-ghost" onClick={handleCheckOverdue} disabled={checking}>Check overdue debts</button>
            <button className="btn btn-ghost" onClick={handleCheckLowStock} disabled={checking}>Check low stock</button>
            <button className="btn btn-ghost" onClick={handleSendSummary} disabled={checking}>Send today's summary</button>
          </>
        }
      />

      {checkMessage && <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>{checkMessage}</p>}

      {loading ? <div className="loading-row">Loading…</div> : notifications.length === 0 ? (
        <div className="card"><div style={{ padding: 24 }}><EmptyState title="No notifications yet" subtitle="Low stock, shift variances, and other alerts will show up here." /></div></div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {notifications.map((n) => (
            <div
              key={n.id}
              className="card"
              style={{ padding: 16, cursor: n.link_path ? "pointer" : "default" }}
              onClick={() => n.link_path && navigate(n.link_path)}
              role={n.link_path ? "button" : undefined}
              tabIndex={n.link_path ? 0 : undefined}
              onKeyDown={(e) => { if (n.link_path && (e.key === "Enter" || e.key === " ")) navigate(n.link_path); }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                <div>
                  <span className={`badge badge--${n.level === "critical" ? "critical" : n.level === "important" ? "attention" : "neutral"}`} style={{ marginRight: 8 }}>
                    {n.level}
                  </span>
                  <strong style={{ fontSize: 16 }}>{n.title}</strong>
                  <p style={{ fontSize: 15, color: "var(--ink-600)", margin: "6px 0 0", whiteSpace: "pre-line" }}>{n.message}</p>
                  {n.link_path && (
                    <span style={{ fontSize: 14, color: "var(--gold-600)", display: "inline-block", marginTop: 8 }}>
                      Go to the issue →
                    </span>
                  )}
                </div>
                <span style={{ fontSize: 14, color: "var(--ink-300)", whiteSpace: "nowrap" }}>{formatDate(n.created_at)}</span>
              </div>
              <div style={{ display: "flex", gap: 14, marginTop: 10, fontSize: 13.5, color: "var(--ink-300)" }}>
                <span>WhatsApp: {n.whatsapp_attempted ? (n.whatsapp_delivered ? "✓ delivered" : `✕ ${n.whatsapp_error || "failed"}`) : "not sent"}</span>
                <span>Email: {n.email_attempted ? (n.email_delivered ? "✓ delivered" : `✕ ${n.email_error || "failed"}`) : "not sent"}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
