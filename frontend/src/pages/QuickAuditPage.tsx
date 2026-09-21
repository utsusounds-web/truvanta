import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { useBusiness } from "../context/BusinessContext";
import { getQuickAudits, triggerQuickAudit, recordAuditCounts } from "../api/resources";
import type { QuickAudit } from "../api/types";
import { formatMoney, formatDate, extractErrorMessage } from "../lib/format";

export default function QuickAuditPage() {
  const { activeBranchId } = useBusiness();
  const [audits, setAudits] = useState<QuickAudit[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);

  const [counting, setCounting] = useState<QuickAudit | null>(null);
  const [counts, setCounts] = useState<Record<string, string>>({});
  const [countError, setCountError] = useState<string | null>(null);
  const [countSubmitting, setCountSubmitting] = useState(false);

  function refresh() {
    if (!activeBranchId) return;
    setLoading(true);
    getQuickAudits({ branch: activeBranchId }).then(setAudits).finally(() => setLoading(false));
  }
  useEffect(refresh, [activeBranchId]);

  async function handleTrigger() {
    if (!activeBranchId) return;
    setTriggering(true); setTriggerError(null);
    try {
      await triggerQuickAudit(activeBranchId, 5);
      refresh();
    } catch (err: any) {
      setTriggerError(extractErrorMessage(err, "Couldn't start an audit."));
    } finally { setTriggering(false); }
  }

  function openCounting(audit: QuickAudit) {
    setCounting(audit);
    setCounts({});
    setCountError(null);
  }

  async function handleSubmitCounts() {
    if (!counting) return;
    setCountSubmitting(true); setCountError(null);
    try {
      const numericCounts: Record<string, number> = {};
      for (const [id, val] of Object.entries(counts)) {
        if (val !== "") numericCounts[id] = parseFloat(val);
      }
      await recordAuditCounts(counting.id, numericCounts);
      setCounting(null);
      refresh();
    } catch (err: any) {
      setCountError(extractErrorMessage(err, "Couldn't save counts."));
    } finally { setCountSubmitting(false); }
  }

  return (
    <div>
      <PageHeader
        title="Quick Stock Audit"
        subtitle="A random spot-check — the system picks products (weighted toward higher-value stock), you count what's physically there."
        actions={<button className="btn btn-primary" onClick={handleTrigger} disabled={triggering}>{triggering ? "Starting…" : "Start random audit"}</button>}
        vaultAccent
      />
      <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginTop: -14, marginBottom: 16 }}>
        Needs stock already recorded for this branch first — Inventory → Record movement → Stock Purchase,
        if you haven't done that yet.
      </p>
      {triggerError && <p className="inline-error">{triggerError}</p>}

      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : audits.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No audits yet" subtitle="Trigger one to spot-check your stock." /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Started</th><th className="num">Items</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {audits.map((a) => (
                <tr key={a.id}>
                  <td>{formatDate(a.created_at)}</td>
                  <td className="num">{a.lines.length}</td>
                  <td><span className={`badge badge--${a.status === "completed" ? "good" : "attention"}`}>{a.status}</span></td>
                  <td>{a.status === "pending" && <button className="btn btn-ghost" onClick={() => openCounting(a)}>Enter counts</button>}
                      {a.status === "completed" && <button className="btn btn-ghost" onClick={() => openCounting(a)}>View results</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {counting && (
        <Modal title="Quick audit" onClose={() => setCounting(null)}>
          {counting.status === "pending" ? (
            <>
              <p style={{ fontSize: 15.5, color: "var(--ink-600)", marginBottom: 16 }}>
                Please count the following products and enter the physical quantity found.
              </p>
              {counting.lines.map((line) => (
                <Field key={line.id} label={line.product_name}>
                  <input
                    className="input" type="number" min={0} step="0.001"
                    value={counts[line.id] || ""}
                    onChange={(e) => setCounts((c) => ({ ...c, [line.id]: e.target.value }))}
                  />
                </Field>
              ))}
              {countError && <p className="inline-error">{countError}</p>}
              <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleSubmitCounts} disabled={countSubmitting}>
                {countSubmitting ? "Saving…" : "Submit counts"}
              </button>
            </>
          ) : (
            <table className="data-table">
              <thead><tr><th>Product</th><th className="num">Expected</th><th className="num">Physical</th><th className="num">Difference</th><th className="num">Est. value</th></tr></thead>
              <tbody>
                {counting.lines.map((line) => (
                  <tr key={line.id}>
                    <td>{line.product_name}</td>
                    <td className="num">{line.expected_quantity}</td>
                    <td className="num">{line.physical_quantity ?? "—"}</td>
                    <td className="num" style={{ color: line.difference && parseFloat(line.difference) < 0 ? "var(--red-600)" : "var(--ink-800)" }}>
                      {line.difference ?? "—"}
                    </td>
                    <td className="num">{line.estimated_financial_value ? formatMoney(line.estimated_financial_value) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Modal>
      )}
    </div>
  );
}
