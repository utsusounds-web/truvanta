import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { getSuppliers, createSupplier, fetchSupplierStatementPdfUrl, getSupplierReliabilityScorecard } from "../api/resources";
import type { Supplier, SupplierScorecardRow } from "../api/types";
import { formatMoney, extractErrorMessage } from "../lib/format";
import { useAuth } from "../context/AuthContext";

export default function SuppliersPage() {
  const { hasPermission } = useAuth();
  const canManageSuppliers = hasPermission("manage_suppliers");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", phone_number: "", address: "" });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"suppliers" | "scorecard">("suppliers");
  const [scorecard, setScorecard] = useState<SupplierScorecardRow[]>([]);
  const [scorecardLoading, setScorecardLoading] = useState(false);

  function refresh() {
    setLoading(true);
    getSuppliers().then(setSuppliers).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  useEffect(() => {
    if (view !== "scorecard" || !canManageSuppliers) return;
    setScorecardLoading(true);
    getSupplierReliabilityScorecard().then(setScorecard).finally(() => setScorecardLoading(false));
  }, [view, canManageSuppliers]);

  async function handleAdd() {
    if (!form.name) { setError("Name is required."); return; }
    setSubmitting(true); setError(null);
    try {
      await createSupplier(form);
      setShowAdd(false);
      setForm({ name: "", phone_number: "", address: "" });
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't add supplier."));
    } finally { setSubmitting(false); }
  }

  return (
    <div>
      <PageHeader
        title="Suppliers"
        subtitle="Who you buy stock from, and what you owe them."
        actions={canManageSuppliers ? <button className="btn btn-primary" onClick={() => setShowAdd(true)}>Add supplier</button> : undefined}
      />

      {canManageSuppliers && (
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button className={`btn ${view === "suppliers" ? "btn-primary" : "btn-ghost"}`} onClick={() => setView("suppliers")}>Suppliers</button>
          <button className={`btn ${view === "scorecard" ? "btn-primary" : "btn-ghost"}`} onClick={() => setView("scorecard")}>Reliability Scorecard</button>
        </div>
      )}

      {view === "scorecard" ? (
        <div className="card" style={{ padding: 24 }}>
          <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginBottom: 16 }}>
            Built from your own purchase order and goods-received history — real leverage for your next
            negotiation, not a guess. "—" means not enough history yet for that metric.
          </p>
          {scorecardLoading ? (
            <div className="loading-row">Loading…</div>
          ) : scorecard.length === 0 ? (
            <EmptyState title="No supplier activity yet" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Supplier</th><th className="num">Purchase orders</th>
                  <th className="num">On-time delivery</th><th className="num">Discrepancy rate</th>
                  <th className="num">Price change rate</th>
                </tr>
              </thead>
              <tbody>
                {scorecard.map((s) => (
                  <tr key={s.supplier_id}>
                    <td>{s.supplier_name}</td>
                    <td className="num">{s.purchase_orders_count}</td>
                    <td className="num">{s.on_time_delivery_percent != null ? `${s.on_time_delivery_percent}% (${s.on_time_sample_size})` : "—"}</td>
                    <td className="num" style={{ color: (s.discrepancy_rate_percent ?? 0) > 5 ? "var(--red-600)" : undefined }}>
                      {s.discrepancy_rate_percent != null ? `${s.discrepancy_rate_percent}%` : "—"}
                    </td>
                    <td className="num">{s.price_change_rate_percent != null ? `${s.price_change_rate_percent}% (${s.price_stability_sample_size})` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ) : (
      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : suppliers.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No suppliers yet" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Name</th><th>Phone</th><th className="num">Outstanding balance</th><th></th></tr></thead>
            <tbody>
              {suppliers.map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td>{s.phone_number || "—"}</td>
                  <td className="num">{formatMoney(s.outstanding_balance)}</td>
                  <td><button className="btn btn-ghost" onClick={async () => window.open(await fetchSupplierStatementPdfUrl(s.id), "_blank")}>Statement PDF</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      )}

      <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginTop: 16 }}>
        Manage purchase orders and goods-receiving from the Purchase Orders page.
      </p>

      {showAdd && (
        <Modal title="Add supplier" onClose={() => setShowAdd(false)}>
          <Field label="Name" required><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Phone number"><input className="input" value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} /></Field>
          <Field label="Address"><input className="input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleAdd} disabled={submitting}>{submitting ? "Saving…" : "Save supplier"}</button>
        </Modal>
      )}
    </div>
  );
}
