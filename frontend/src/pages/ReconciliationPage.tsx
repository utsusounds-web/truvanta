import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import { getPaymentReconciliation, setPaymentReconciliationStatus } from "../api/resources";
import type { PaymentReconciliationEntry } from "../api/types";
import { formatMoney } from "../lib/format";

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: "Confirmed" },
  { value: "reconciled", label: "Reconciled" },
  { value: "unmatched", label: "Unmatched" },
  { value: "disputed", label: "Disputed" },
];

export default function ReconciliationPage() {
  const [payments, setPayments] = useState<PaymentReconciliationEntry[]>([]);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    getPaymentReconciliation(statusFilter ? { reconciliation_status: statusFilter } : undefined)
      .then(setPayments)
      .finally(() => setLoading(false));
  }
  useEffect(refresh, [statusFilter]);

  async function handleSetStatus(payment: PaymentReconciliationEntry, status: string) {
    setUpdatingId(payment.id);
    try {
      let note: string | undefined;
      if (status === "disputed") {
        note = window.prompt("Reason for disputing this payment:") || undefined;
        if (!note) { setUpdatingId(null); return; }
      }
      await setPaymentReconciliationStatus(payment.id, status, note);
      refresh();
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Payment Reconciliation"
        subtitle="Bank transfer, card, and other non-cash payments — match them against your bank or processor statement. Cash is confirmed automatically at the till."
        vaultAccent
      />

      <div className="toolbar">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            className={`btn ${statusFilter === f.value ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setStatusFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : payments.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="Nothing here" subtitle="No payments match this filter." /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Receipt #</th><th>Branch</th><th>Method</th><th>Reference</th><th className="num">Amount</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.id}>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: 14.5 }}>{p.transaction_number}</td>
                  <td>{p.branch_name}</td>
                  <td style={{ textTransform: "capitalize" }}>{p.method.replace(/_/g, " ")}</td>
                  <td>{p.reference || "—"}</td>
                  <td className="num">{formatMoney(p.amount)}</td>
                  <td>
                    <span className={`badge badge--${p.reconciliation_status === "disputed" || p.reconciliation_status === "unmatched" ? "critical" : p.reconciliation_status === "pending" ? "attention" : "good"}`}>
                      {p.reconciliation_status}
                    </span>
                    {p.reconciliation_note && <div style={{ fontSize: 13, color: "var(--ink-300)", marginTop: 4 }}>{p.reconciliation_note}</div>}
                  </td>
                  <td>
                    {p.reconciliation_status === "pending" && (
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="btn btn-ghost" disabled={updatingId === p.id} onClick={() => handleSetStatus(p, "reconciled")}>Reconciled</button>
                        <button className="btn btn-ghost" disabled={updatingId === p.id} onClick={() => handleSetStatus(p, "unmatched")}>Unmatched</button>
                        <button className="btn btn-ghost" disabled={updatingId === p.id} onClick={() => handleSetStatus(p, "disputed")}>Dispute</button>
                      </div>
                    )}
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
