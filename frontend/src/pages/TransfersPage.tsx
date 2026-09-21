import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { useBusiness } from "../context/BusinessContext";
import { useAuth } from "../context/AuthContext";
import { getStockTransfers, sendStockTransfer, receiveStockTransfer, getProducts } from "../api/resources";
import type { StockTransfer, Product } from "../api/types";
import { extractErrorMessage } from "../lib/format";

export default function TransfersPage() {
  const { hasPermission } = useAuth();
  const canManageInventory = hasPermission("manage_inventory");
  const { branches } = useBusiness();
  const [transfers, setTransfers] = useState<StockTransfer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showSend, setShowSend] = useState(false);
  const [productId, setProductId] = useState("");
  const [fromBranch, setFromBranch] = useState("");
  const [toBranch, setToBranch] = useState("");
  const [quantity, setQuantity] = useState("");
  const [sendError, setSendError] = useState<string | null>(null);
  const [sendSubmitting, setSendSubmitting] = useState(false);

  const [receiving, setReceiving] = useState<StockTransfer | null>(null);
  const [receivedQty, setReceivedQty] = useState("");
  const [receiveError, setReceiveError] = useState<string | null>(null);
  const [receiveSubmitting, setReceiveSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    setError(null);
    Promise.allSettled([getStockTransfers(), getProducts({ is_active: "true" })]).then(([t, p]) => {
      if (t.status === "fulfilled") setTransfers(t.value); else console.error("Failed to load transfers:", t.reason);
      if (p.status === "fulfilled") setProducts(p.value); else console.error("Failed to load products:", p.reason);
      if (t.status === "rejected" || p.status === "rejected") {
        setError("Some data didn't load — check your connection and reload this page.");
      }
    }).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  async function handleSend() {
    if (!productId || !fromBranch || !toBranch || !quantity) { setSendError("All fields are required."); return; }
    if (fromBranch === toBranch) { setSendError("Sending and receiving branch must be different."); return; }
    setSendSubmitting(true); setSendError(null);
    try {
      await sendStockTransfer({ product: productId, from_branch: fromBranch, to_branch: toBranch, quantity_sent: parseFloat(quantity) });
      setShowSend(false);
      setProductId(""); setFromBranch(""); setToBranch(""); setQuantity("");
      refresh();
    } catch (err: any) {
      setSendError(extractErrorMessage(err, "Couldn't send the transfer."));
    } finally { setSendSubmitting(false); }
  }

  async function handleReceive() {
    if (!receiving || !receivedQty) return;
    setReceiveSubmitting(true); setReceiveError(null);
    try {
      await receiveStockTransfer(receiving.id, parseFloat(receivedQty));
      setReceiving(null);
      setReceivedQty("");
      refresh();
    } catch (err: any) {
      setReceiveError(extractErrorMessage(err, "Couldn't confirm receipt."));
    } finally { setReceiveSubmitting(false); }
  }

  return (
    <div>
      <PageHeader
        title="Branch Transfers"
        subtitle="Stock leaves the sending branch the moment it's sent. It only counts as received once the receiving branch confirms what actually arrived."
        actions={canManageInventory ? <button className="btn btn-primary" onClick={() => setShowSend(true)}>Send stock</button> : undefined}
      />

      {error && <p className="inline-error">{error}</p>}

      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : transfers.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No transfers yet" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Product</th><th>From</th><th>To</th><th className="num">Sent</th><th className="num">Received</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {transfers.map((t) => (
                <tr key={t.id}>
                  <td>{t.product_name}</td>
                  <td>{t.from_branch_name}</td>
                  <td>{t.to_branch_name}</td>
                  <td className="num">{t.quantity_sent}</td>
                  <td className="num">{t.quantity_received ?? "—"}</td>
                  <td>
                    <span className={`badge badge--${t.status === "pending" ? "attention" : t.status === "received" ? "good" : "critical"}`}>
                      {t.status.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td>{t.status === "pending" && canManageInventory && <button className="btn btn-ghost" onClick={() => { setReceiving(t); setReceivedQty(t.quantity_sent); setReceiveError(null); }}>Confirm receipt</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showSend && (
        <Modal title="Send stock to another branch" onClose={() => setShowSend(false)}>
          <Field label="Product" required>
            <select className="input" value={productId} onChange={(e) => setProductId(e.target.value)}>
              <option value="">Select…</option>
              {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>
          <Field label="From branch" required>
            <select className="input" value={fromBranch} onChange={(e) => setFromBranch(e.target.value)}>
              <option value="">Select…</option>
              {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </Field>
          <Field label="To branch" required>
            <select className="input" value={toBranch} onChange={(e) => setToBranch(e.target.value)}>
              <option value="">Select…</option>
              {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </Field>
          <Field label="Quantity" required>
            <input className="input" type="number" min={0} step="0.001" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </Field>
          {sendError && <p className="inline-error">{sendError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleSend} disabled={sendSubmitting}>
            {sendSubmitting ? "Sending…" : "Send"}
          </button>
        </Modal>
      )}

      {receiving && (
        <Modal title={`Confirm receipt — ${receiving.product_name}`} onClose={() => setReceiving(null)}>
          <p style={{ fontSize: 15.5, color: "var(--ink-600)", marginBottom: 16 }}>
            {receiving.quantity_sent} was sent from {receiving.from_branch_name}. Enter what actually arrived —
            if it doesn't match, that's recorded as a discrepancy, not silently adjusted.
          </p>
          <Field label="Quantity received" required>
            <input className="input" type="number" min={0} step="0.001" value={receivedQty} onChange={(e) => setReceivedQty(e.target.value)} />
          </Field>
          {receiveError && <p className="inline-error">{receiveError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleReceive} disabled={receiveSubmitting}>
            {receiveSubmitting ? "Confirming…" : "Confirm receipt"}
          </button>
        </Modal>
      )}
    </div>
  );
}
