import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { useBusiness } from "../context/BusinessContext";
import { useAuth } from "../context/AuthContext";
import { getSaleReturns, getSales, createSaleReturn, approveSaleReturn } from "../api/resources";
import type { SaleReturn, Sale } from "../api/types";
import { formatMoney, formatDate, extractErrorMessage } from "../lib/format";

export default function ReturnsPage() {
  const { hasPermission } = useAuth();
  const canApproveReturns = hasPermission("approve_returns");
  const { activeBranchId } = useBusiness();
  const [returns, setReturns] = useState<SaleReturn[]>([]);
  const [recentSales, setRecentSales] = useState<Sale[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [receiptSearch, setReceiptSearch] = useState("");
  const [receiptSearchResults, setReceiptSearchResults] = useState<Sale[] | null>(null);
  const [receiptSearching, setReceiptSearching] = useState(false);
  const [selectedSaleId, setSelectedSaleId] = useState("");
  const [selectedItemId, setSelectedItemId] = useState("");
  const [returnType, setReturnType] = useState("return");
  const [quantity, setQuantity] = useState("");
  const [refundAmount, setRefundAmount] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  function refresh() {
    if (!activeBranchId) return;
    setLoading(true);
    Promise.allSettled([getSaleReturns(), getSales({ branch: activeBranchId, status: "completed" })]).then(([r, s]) => {
      if (r.status === "fulfilled") setReturns(r.value); else console.error("Failed to load returns:", r.reason);
      if (s.status === "fulfilled") setRecentSales(s.value.slice(0, 25)); else console.error("Failed to load recent sales:", s.reason);
    }).finally(() => setLoading(false));
  }
  useEffect(refresh, [activeBranchId]);

  const saleOptions = receiptSearchResults ?? recentSales;
  const selectedSale = saleOptions.find((s) => s.id === selectedSaleId);

  async function handleReceiptSearch() {
    const code = receiptSearch.trim();
    if (!code) { setReceiptSearchResults(null); return; }
    setReceiptSearching(true);
    try {
      const results = await getSales({ search: code });
      setReceiptSearchResults(results);
    } catch (err) {
      console.error("Receipt search failed:", err);
      setReceiptSearchResults([]);
    } finally {
      setReceiptSearching(false);
    }
  }

  async function handleAdd() {
    if (!selectedSaleId || !selectedItemId || !quantity || !reason) {
      setError("Sale, item, quantity, and reason are all required.");
      return;
    }
    setSubmitting(true); setError(null);
    try {
      await createSaleReturn({
        sale: selectedSaleId, sale_item: selectedItemId, return_type: returnType,
        quantity: parseFloat(quantity), refund_amount: refundAmount ? parseFloat(refundAmount) : 0,
        restock: returnType !== "damaged" && returnType !== "expired", reason,
      });
      setShowAdd(false);
      setSelectedSaleId(""); setSelectedItemId(""); setQuantity(""); setRefundAmount(""); setReason("");
      setReceiptSearch(""); setReceiptSearchResults(null);
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't record the return."));
    } finally { setSubmitting(false); }
  }

  async function handleApprove(id: string) { await approveSaleReturn(id); refresh(); }

  return (
    <div>
      <PageHeader
        title="Returns & Refunds"
        subtitle="Corrections to completed sales — never a silent edit to the original."
        actions={<button className="btn btn-primary" onClick={() => setShowAdd(true)}>Record return</button>}
      />

      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : returns.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No returns recorded yet" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Date</th><th>Type</th><th className="num">Qty</th><th className="num">Refund</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {returns.map((r) => (
                <tr key={r.id}>
                  <td>{formatDate(r.created_at)}</td>
                  <td style={{ textTransform: "capitalize" }}>{r.return_type}</td>
                  <td className="num">{r.quantity}</td>
                  <td className="num">{formatMoney(r.refund_amount)}</td>
                  <td><span className={`badge badge--${r.status}`}>{r.status.replace(/_/g, " ")}</span></td>
                  <td>{r.status === "pending_approval" && canApproveReturns && <button className="btn btn-ghost" onClick={() => handleApprove(r.id)}>Approve</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showAdd && (
        <Modal title="Record return" onClose={() => { setShowAdd(false); setReceiptSearch(""); setReceiptSearchResults(null); }}>
          <Field
            label="Find by receipt code"
            hint="For a walk-in customer with no name on file — every sale gets a receipt code automatically, so this is the only lookup you need. Leave blank to pick from recent sales instead."
          >
            <div style={{ display: "flex", gap: 8 }}>
              <input
                className="input"
                placeholder="e.g. SL-7F2A91C0B3"
                value={receiptSearch}
                onChange={(e) => setReceiptSearch(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleReceiptSearch(); } }}
              />
              <button type="button" className="btn btn-ghost" onClick={handleReceiptSearch} disabled={receiptSearching}>
                {receiptSearching ? "Searching…" : "Search"}
              </button>
            </div>
            {receiptSearchResults !== null && (
              <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginTop: 4 }}>
                {receiptSearchResults.length === 0
                  ? "No sale matches that receipt code."
                  : `${receiptSearchResults.length} match${receiptSearchResults.length === 1 ? "" : "es"} found.`}
              </p>
            )}
          </Field>
          <Field label="Sale" required>
            <select className="input" value={selectedSaleId} onChange={(e) => { setSelectedSaleId(e.target.value); setSelectedItemId(""); }}>
              <option value="">{receiptSearchResults ? "Select a matching sale…" : "Select a recent sale…"}</option>
              {saleOptions.map((s) => <option key={s.id} value={s.id}>{s.transaction_number} — {formatMoney(s.grand_total)}</option>)}
            </select>
          </Field>
          {selectedSale && (
            <Field label="Item" required>
              <select className="input" value={selectedItemId} onChange={(e) => setSelectedItemId(e.target.value)}>
                <option value="">Select item…</option>
                {selectedSale.items.map((i) => <option key={i.id} value={i.id}>{i.product_name} (x{i.quantity})</option>)}
              </select>
            </Field>
          )}
          <Field label="Return type">
            <select className="input" value={returnType} onChange={(e) => setReturnType(e.target.value)}>
              <option value="return">Return (restock)</option>
              <option value="refund">Refund</option>
              <option value="exchange">Exchange</option>
              <option value="damaged">Damaged goods</option>
              <option value="expired">Expired product</option>
            </select>
          </Field>
          <Field label="Quantity" required><input className="input" type="number" min={0} step="0.001" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></Field>
          {returnType === "refund" && (
            <Field label="Refund amount"><input className="input" type="number" min={0} value={refundAmount} onChange={(e) => setRefundAmount(e.target.value)} /></Field>
          )}
          <Field label="Reason" required><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleAdd} disabled={submitting}>{submitting ? "Saving…" : "Submit for approval"}</button>
        </Modal>
      )}
    </div>
  );
}
