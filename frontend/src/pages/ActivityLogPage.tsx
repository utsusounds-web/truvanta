import { Fragment, useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import Field from "../components/Field";
import { useAuth } from "../context/AuthContext";
import { getAuditLogs } from "../api/resources";
import type { AuditLog } from "../api/types";
import { formatDate, extractErrorMessage } from "../lib/format";

const ACTION_LABELS: Record<string, string> = {
  create: "Create", update: "Update", price_change: "Price Change", discount: "Discount Applied",
  refund: "Refund", return: "Return", cancellation: "Cancellation", stock_adjustment: "Stock Adjustment",
  expense_change: "Expense Change", credit_change: "Credit Change", permission_change: "Permission Change",
  login: "Login", login_failed: "Failed Login", receipt_reprint: "Receipt Reprint",
  shift_event: "Shift Event", other: "Platform Notice", 
};

const ACTION_SEVERITY: Record<string, "critical" | "attention" | "neutral"> = {
  login_failed: "critical", cancellation: "critical", permission_change: "critical",
  refund: "attention", return: "attention", discount: "attention", price_change: "attention",
  credit_change: "attention", stock_adjustment: "attention", expense_change: "attention",
  other: "attention",
};

function summarize(log: AuditLog): string {
  const who = log.actor_name || "System";
  const what = ACTION_LABELS[log.action] || log.action;
  const where = log.branch_name ? ` at ${log.branch_name}` : "";
  return `${who} — ${what}${where}`;
}

export default function ActivityLogPage() {
  const { isOwnerOrAdmin } = useAuth();
  const allowed = isOwnerOrAdmin();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [actionFilter, setActionFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  function refresh() {
    if (!allowed) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    const params: Record<string, string> = {};
    if (actionFilter) params.action = actionFilter;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    getAuditLogs(params)
      .then(setLogs)
      .catch((err) => setError(extractErrorMessage(err, "Couldn't load the activity log.")))
      .finally(() => setLoading(false));
  }
  useEffect(refresh, [allowed, actionFilter, dateFrom, dateTo]);

  if (!allowed) {
    return (
      <div>
        <PageHeader title="Activity Log" subtitle="A record of sensitive actions taken across the business." />
        <EmptyState
          title="Owner/admin only"
          subtitle="The activity log includes login and permission-change history, so it's restricted to owners and admins."
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Activity Log"
        subtitle="Every price change, discount, refund, cancellation, stock adjustment, permission change, login, and reprint — an immutable record, never edited or deleted."
      />

      <div className="card" style={{ padding: 16, marginBottom: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Field label="Action type">
          <select className="input" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}>
            <option value="">All actions</option>
            {Object.entries(ACTION_LABELS).map(([code, label]) => (
              <option key={code} value={code}>{label}</option>
            ))}
          </select>
        </Field>
        <Field label="From">
          <input className="input" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </Field>
        <Field label="To">
          <input className="input" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </Field>
      </div>

      {error && <p className="inline-error">{error}</p>}

      <div className="card">
        {loading ? (
          <div className="loading-row">Loading…</div>
        ) : logs.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No activity recorded for this filter" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>When</th><th>Action</th><th>Reason / note</th><th></th></tr></thead>
            <tbody>
              {logs.map((l) => {
                const severity = ACTION_SEVERITY[l.action] || "neutral";
                const isExpanded = expanded === l.id;
                return (
                  <Fragment key={l.id}>
                    <tr>
                      <td>{formatDate(l.created_at)}</td>
                      <td>
                        <span className={`badge badge--${severity}`}>{ACTION_LABELS[l.action] || l.action}</span>
                        <div style={{ fontSize: 14.5, color: "var(--ink-300)", marginTop: 2 }}>{summarize(l)}</div>
                      </td>
                      <td>{l.reason || <span style={{ color: "var(--ink-300)" }}>—</span>}</td>
                      <td>
                        {(l.previous_value || l.new_value) && (
                          <button className="btn btn-ghost" onClick={() => setExpanded(isExpanded ? null : l.id)}>
                            {isExpanded ? "Hide" : "Details"}
                          </button>
                        )}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr>
                        <td colSpan={4} style={{ background: "var(--paper-100)", fontSize: 14.5 }}>
                          <div style={{ display: "flex", gap: 24, padding: "8px 4px" }}>
                            {l.previous_value && (
                              <div>
                                <strong>Before</strong>
                                <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{JSON.stringify(l.previous_value, null, 2)}</pre>
                              </div>
                            )}
                            {l.new_value && (
                              <div>
                                <strong>After</strong>
                                <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{JSON.stringify(l.new_value, null, 2)}</pre>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
