import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { useBusiness } from "../context/BusinessContext";
import { useAuth } from "../context/AuthContext";
import { getStockLevels, getStockMovements, getProducts, createStockMovement } from "../api/resources";
import { queueStockMovementOffline, isOnline } from "../offline/sync";
import type { StockLevel, StockMovement, Product } from "../api/types";
import { extractErrorMessage, formatDate } from "../lib/format";

const ADJUSTMENT_REASONS = [
  { value: "opening_stock", label: "Opening Stock" },
  { value: "purchase", label: "Stock Purchase (restock)" },
  { value: "customer_return", label: "Customer Return" },
  { value: "supplier_return", label: "Supplier Return" },
  { value: "adjustment", label: "Stock Adjustment" },
  { value: "damage", label: "Damage" },
  { value: "expiry", label: "Expiry" },
  { value: "promotional_sample", label: "Promotional Sample" },
  { value: "personal_use", label: "Personal Use" },
  { value: "other", label: "Other" },
];

export default function InventoryPage() {
  const { hasPermission } = useAuth();
  const canManageInventory = hasPermission("manage_inventory");
  const { activeBranchId } = useBusiness();
  const [levels, setLevels] = useState<StockLevel[]>([]);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [tab, setTab] = useState<"levels" | "movements">("levels");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ product: "", reason: "opening_stock", quantity: "", note: "" });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  function refresh() {
    getProducts({ is_active: "true" }).then(setProducts).catch((err) => {
      console.error("Failed to load products for stock movement:", err);
      setError("Couldn't load your product list — check your connection and reload this page.");
    });
    if (!activeBranchId) return;
    setLoading(true);
    Promise.all([
      getStockLevels({ branch: activeBranchId }),
      getStockMovements({ branch: activeBranchId }),
    ]).then(([l, m]) => { setLevels(l); setMovements(m); }).finally(() => setLoading(false));
  }

  useEffect(refresh, [activeBranchId]);

  const [queuedOfflineMsg, setQueuedOfflineMsg] = useState(false);

  async function handleSubmit() {
    if (!activeBranchId || !form.product || !form.quantity) {
      setError("Product and quantity are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    const qty = parseFloat(form.quantity);
    const DECREASE_REASONS = ["damage", "expiry", "personal_use", "supplier_return", "promotional_sample"];
    const signedQty = DECREASE_REASONS.includes(form.reason) ? -Math.abs(qty) : Math.abs(qty);
    const payload = {
      product: form.product, branch: activeBranchId, quantity_delta: signedQty,
      reason: form.reason, reference_note: form.note,
    };

    if (!isOnline()) {
      await queueStockMovementOffline(payload);
      setQueuedOfflineMsg(true);
      setShowModal(false);
      setForm({ product: "", reason: "opening_stock", quantity: "", note: "" });
      setSubmitting(false);
      return;
    }

    try {
      await createStockMovement(payload);
      setShowModal(false);
      setForm({ product: "", reason: "opening_stock", quantity: "", note: "" });
      refresh();
    } catch (err: any) {
      if (err?.code === "ERR_NETWORK") {
        await queueStockMovementOffline(payload);
        setQueuedOfflineMsg(true);
        setShowModal(false);
        setForm({ product: "", reason: "opening_stock", quantity: "", note: "" });
      } else {
        setError(extractErrorMessage(err, "Couldn't record that stock movement."));
      }
    } finally {
      setSubmitting(false);
    }
  }

  const lowStock = levels.filter((l) => {
    const p = products.find((pr) => pr.id === l.product);
    return p && parseFloat(p.reorder_level) > 0 && parseFloat(l.quantity) <= parseFloat(p.reorder_level);
  });

  return (
    <div>
      <PageHeader
        title="Inventory"
        subtitle="Current stock, and every movement that got it there."
        actions={canManageInventory ? <button className="btn btn-primary" onClick={() => setShowModal(true)}>Record stock movement</button> : undefined}
      />

      {lowStock.length > 0 && (
        <div className="inline-error" style={{ background: "#FBF1DD", color: "var(--gold-600)" }}>
          {lowStock.length} product{lowStock.length > 1 ? "s are" : " is"} at or below reorder level.
        </div>
      )}

      {queuedOfflineMsg && (
        <div className="inline-error" style={{ background: "#E4F3EA", color: "var(--green-600)" }}>
          You're offline — this stock movement is saved on this device and will sync automatically once you're back online.
        </div>
      )}

      <div className="toolbar">
        <button className={`btn ${tab === "levels" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("levels")}>Stock levels</button>
        <button className={`btn ${tab === "movements" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("movements")}>Movement history</button>
      </div>

      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : tab === "levels" ? (
          levels.length === 0 ? <div style={{ padding: 24 }}><EmptyState title="No stock recorded yet" /></div> : (
            <table className="data-table">
              <thead><tr><th>Product</th><th className="num">Quantity on hand</th></tr></thead>
              <tbody>
                {levels.map((l) => (
                  <tr key={l.id}>
                    <td>{l.product_name}</td>
                    <td className="num">{parseFloat(l.quantity).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        ) : (
          movements.length === 0 ? <div style={{ padding: 24 }}><EmptyState title="No movements recorded yet" /></div> : (
            <table className="data-table">
              <thead><tr><th>When</th><th>Product</th><th>Reason</th><th className="num">Change</th></tr></thead>
              <tbody>
                {movements.map((m) => (
                  <tr key={m.id}>
                    <td>{formatDate(m.created_at)}</td>
                    <td>{m.product_name}</td>
                    <td style={{ textTransform: "capitalize" }}>{m.reason.replace(/_/g, " ")}</td>
                    <td className="num" style={{ color: parseFloat(m.quantity_delta) >= 0 ? "var(--green-600)" : "var(--red-600)" }}>
                      {parseFloat(m.quantity_delta) >= 0 ? "+" : ""}{m.quantity_delta}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
      </div>

      {showModal && (
        <Modal title="Record stock movement" onClose={() => setShowModal(false)}>
          <Field label="Product" required>
            <select className="input" value={form.product} onChange={(e) => setForm({ ...form, product: e.target.value })}>
              <option value="">Select…</option>
              {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>
          <Field label="Reason">
            <select className="input" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })}>
              {ADJUSTMENT_REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </Field>
          <Field label="Quantity" required hint="Enter a positive number — direction is handled by the reason chosen">
            <input className="input" type="number" min={0} step="0.001" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
          </Field>
          <Field label="Note">
            <input className="input" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
          </Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Saving…" : "Record movement"}
          </button>
        </Modal>
      )}
    </div>
  );
}
