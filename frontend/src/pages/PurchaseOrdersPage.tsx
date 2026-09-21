import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { useBusiness } from "../context/BusinessContext";
import { useAuth } from "../context/AuthContext";
import {
  getPurchaseOrders, createPurchaseOrder, addPurchaseOrderItem, receivePurchaseOrder,
  getSuppliers, getProducts, fetchPurchaseOrderPdfUrl, fetchGoodsReceiptPdfUrl,
  getUnits, createProduct,
} from "../api/resources";
import type { PurchaseOrder, Supplier, Product, UnitOfMeasure } from "../api/types";
import { extractErrorMessage } from "../lib/format";

interface DraftLine { product: string; unit: string; quantity: string; unitCost: string; }

export default function PurchaseOrdersPage() {
  const { activeBranchId } = useBusiness();
  const { hasPermission } = useAuth();
  const canManageSuppliers = hasPermission("manage_suppliers");
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [units, setUnits] = useState<UnitOfMeasure[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [supplierId, setSupplierId] = useState("");
  const [refNumber, setRefNumber] = useState(`PO-${Date.now().toString(36).toUpperCase()}`);
  const [notes, setNotes] = useState("");
  const [expectedDeliveryDate, setExpectedDeliveryDate] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([{ product: "", unit: "", quantity: "", unitCost: "" }]);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSubmitting, setCreateSubmitting] = useState(false);

  // Quick-add: a supplier can easily deliver something never catalogued
  // before — this lets that be created right here instead of forcing a
  // trip to the Products page and back before the delivery can even be
  // recorded against a purchase order.
  const [quickAddForLine, setQuickAddForLine] = useState<number | null>(null);
  const [quickAddName, setQuickAddName] = useState("");
  const [quickAddUnit, setQuickAddUnit] = useState("");
  const [quickAddPrice, setQuickAddPrice] = useState("");
  const [quickAddSubmitting, setQuickAddSubmitting] = useState(false);
  const [quickAddError, setQuickAddError] = useState<string | null>(null);

  const [receivingPO, setReceivingPO] = useState<PurchaseOrder | null>(null);
  const [receiveQtys, setReceiveQtys] = useState<Record<string, string>>({});
  const [receiveBatchNumbers, setReceiveBatchNumbers] = useState<Record<string, string>>({});
  const [receiveExpiryDates, setReceiveExpiryDates] = useState<Record<string, string>>({});
  const [receiveError, setReceiveError] = useState<string | null>(null);
  const [receiveSubmitting, setReceiveSubmitting] = useState(false);

  function refresh() {
    if (!activeBranchId) return;
    setLoading(true);
    setError(null);
    Promise.allSettled([
      getPurchaseOrders({ branch: activeBranchId }),
      getSuppliers(),
      getProducts({ is_active: "true" }),
      getUnits(),
    ]).then(([o, s, p, u]) => {
      if (o.status === "fulfilled") setOrders(o.value); else console.error("Failed to load purchase orders:", o.reason);
      if (s.status === "fulfilled") setSuppliers(s.value); else console.error("Failed to load suppliers:", s.reason);
      if (p.status === "fulfilled") setProducts(p.value); else console.error("Failed to load products:", p.reason);
      if (u.status === "fulfilled") setUnits(u.value); else console.error("Failed to load units:", u.reason);
      const failed = [o, s, p, u].some((r) => r.status === "rejected");
      if (failed) setError("Some data didn't load — check your connection and reload this page.");
    }).finally(() => setLoading(false));
  }
  useEffect(refresh, [activeBranchId]);

  function updateLine(i: number, patch: Partial<DraftLine>) {
    setLines((ls) => ls.map((l, idx) => idx === i ? { ...l, ...patch } : l));
  }
  function addLine() { setLines((ls) => [...ls, { product: "", unit: "", quantity: "", unitCost: "" }]); }
  function removeLine(i: number) { setLines((ls) => ls.filter((_, idx) => idx !== i)); }

  function openQuickAdd(lineIndex: number) {
    setQuickAddForLine(lineIndex);
    setQuickAddName("");
    setQuickAddUnit(units[0]?.id || "");
    setQuickAddPrice("");
    setQuickAddError(null);
  }

  async function handleQuickAddProduct() {
    if (quickAddForLine === null) return;
    if (!quickAddName.trim() || !quickAddUnit || !quickAddPrice) {
      setQuickAddError("Name, unit, and a selling price are required.");
      return;
    }
    setQuickAddSubmitting(true);
    setQuickAddError(null);
    try {
      const fd = new FormData();
      fd.append("name", quickAddName.trim());
      fd.append("sku", "");
      fd.append("barcode", "");
      fd.append("cost_price", "0");
      fd.append("selling_price", quickAddPrice);
      fd.append("reorder_level", "0");
      fd.append("minimum_stock_level", "0");
      fd.append("base_unit", quickAddUnit);
      const created = await createProduct(fd);
      setProducts((prev) => [...prev, created]);
      updateLine(quickAddForLine, { product: created.id });
      setQuickAddForLine(null);
    } catch (err: any) {
      setQuickAddError(extractErrorMessage(err, "Couldn't save that product."));
    } finally {
      setQuickAddSubmitting(false);
    }
  }

  async function handleCreate() {
    if (!activeBranchId || !supplierId || !refNumber) { setCreateError("Supplier and reference number are required."); return; }
    const validLines = lines.filter((l) => l.product && l.quantity && l.unitCost);
    if (validLines.length === 0) { setCreateError("Add at least one item."); return; }

    setCreateSubmitting(true); setCreateError(null);
    try {
      const po = await createPurchaseOrder({
        supplier: supplierId, branch: activeBranchId, reference_number: refNumber, notes,
        expected_delivery_date: expectedDeliveryDate || undefined,
      });
      for (const line of validLines) {
        const product = products.find((p) => p.id === line.product);
        await addPurchaseOrderItem({
          purchase_order: po.id, product: line.product, unit: product?.base_unit || "",
          quantity_ordered: parseFloat(line.quantity), unit_cost: parseFloat(line.unitCost),
        });
      }
      setShowCreate(false);
      setSupplierId(""); setRefNumber(`PO-${Date.now().toString(36).toUpperCase()}`); setNotes(""); setExpectedDeliveryDate("");
      setLines([{ product: "", unit: "", quantity: "", unitCost: "" }]);
      refresh();
    } catch (err: any) {
      setCreateError(extractErrorMessage(err, "Couldn't create the purchase order."));
    } finally { setCreateSubmitting(false); }
  }

  function openReceive(po: PurchaseOrder) {
    setReceivingPO(po);
    const initial: Record<string, string> = {};
    po.items.forEach((i) => { initial[i.id] = i.quantity_ordered; });
    setReceiveQtys(initial);
    setReceiveBatchNumbers({});
    setReceiveExpiryDates({});
    setReceiveError(null);
  }

  const [lastGoodsReceiptId, setLastGoodsReceiptId] = useState<string | null>(null);

  async function handleReceive() {
    if (!receivingPO) return;
    setReceiveSubmitting(true); setReceiveError(null);
    try {
      const receipt = await receivePurchaseOrder(receivingPO.id, receivingPO.items.map((i) => ({
        purchase_order_item: i.id, quantity_received: parseFloat(receiveQtys[i.id] || "0"),
        batch_number: receiveBatchNumbers[i.id] || undefined,
        expiry_date: receiveExpiryDates[i.id] || undefined,
      })));
      setReceivingPO(null);
      setLastGoodsReceiptId(receipt.id);
      refresh();
    } catch (err: any) {
      setReceiveError(extractErrorMessage(err, "Couldn't record the goods receipt."));
    } finally { setReceiveSubmitting(false); }
  }

  return (
    <div>
      <PageHeader
        title="Purchase Orders"
        subtitle="Order → Receive → compare ordered vs. received, with discrepancies flagged."
        actions={canManageSuppliers ? <button className="btn btn-primary" onClick={() => setShowCreate(true)}>New purchase order</button> : undefined}
      />

      {lastGoodsReceiptId && (
        <div className="card" style={{ padding: "12px 16px", marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 15.5 }}>Goods receipt recorded.</span>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-ghost" onClick={async () => window.open(await fetchGoodsReceiptPdfUrl(lastGoodsReceiptId), "_blank")}>Download report</button>
            <button className="btn btn-ghost" onClick={() => setLastGoodsReceiptId(null)}>Dismiss</button>
          </div>
        </div>
      )}

      {error && <p className="inline-error">{error}</p>}

      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : orders.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No purchase orders yet" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Reference</th><th>Supplier</th><th className="num">Items</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {orders.map((po) => {
                const supplier = suppliers.find((s) => s.id === po.supplier);
                return (
                  <tr key={po.id}>
                    <td>{po.reference_number}</td>
                    <td>{supplier?.name || "—"}</td>
                    <td className="num">{po.items.length}</td>
                    <td><span className={`badge badge--${po.status === "received" ? "good" : po.status === "cancelled" ? "critical" : "attention"}`}>{po.status.replace(/_/g, " ")}</span></td>
                    <td>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {po.status !== "received" && po.status !== "cancelled" && <button className="btn btn-ghost" onClick={() => openReceive(po)}>Receive goods</button>}
                        <button className="btn btn-ghost" onClick={async () => window.open(await fetchPurchaseOrderPdfUrl(po.id), "_blank")}>PDF</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <Modal title="New purchase order" width={640} onClose={() => setShowCreate(false)}>
          <div className="form-grid">
            <div className="field--half"><Field label="Supplier" required>
              <select className="input" value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
                <option value="">Select…</option>
                {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </Field></div>
            <div className="field--half"><Field label="Reference number" required>
              <input className="input" value={refNumber} onChange={(e) => setRefNumber(e.target.value)} />
            </Field></div>
          </div>
          <Field label="Notes"><input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
          <Field label="Expected delivery date" hint="Optional — powers the on-time % in the Supplier Reliability Scorecard">
            <input className="input" type="date" value={expectedDeliveryDate} onChange={(e) => setExpectedDeliveryDate(e.target.value)} />
          </Field>

          <p className="section-title" style={{ fontSize: 15, marginTop: 8 }}>Items</p>
          {lines.map((line, i) => (
            <div key={i} style={{ display: "flex", gap: 8, marginBottom: 10, alignItems: "flex-end" }}>
              <select className="input" value={line.product} onChange={(e) => updateLine(i, { product: e.target.value })} style={{ flex: 2 }}>
                <option value="">Product…</option>
                {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <button type="button" className="btn btn-ghost" onClick={() => openQuickAdd(i)} title="Never bought this before? Add it now.">+ New</button>
              <input className="input" type="number" placeholder="Qty" value={line.quantity} onChange={(e) => updateLine(i, { quantity: e.target.value })} style={{ flex: 1 }} />
              <input className="input" type="number" placeholder="Unit cost" value={line.unitCost} onChange={(e) => updateLine(i, { unitCost: e.target.value })} style={{ flex: 1 }} />
              <button type="button" className="btn btn-ghost" onClick={() => removeLine(i)}>✕</button>
            </div>
          ))}
          <button type="button" className="btn btn-ghost" onClick={addLine} style={{ marginBottom: 18 }}>+ Add item</button>

          {createError && <p className="inline-error">{createError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleCreate} disabled={createSubmitting}>
            {createSubmitting ? "Creating…" : "Create purchase order"}
          </button>
        </Modal>
      )}

      {quickAddForLine !== null && (
        <Modal title="Add a new product" onClose={() => setQuickAddForLine(null)}>
          <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
            For something your supplier is bringing that isn't in your catalogue yet. You can fill in
            more detail (photo, SKU, reorder alert…) from the Products page anytime.
          </p>
          <Field label="Product name" required>
            <input className="input" value={quickAddName} onChange={(e) => setQuickAddName(e.target.value)} autoFocus />
          </Field>
          <Field label="Unit of measure" required>
            <select className="input" value={quickAddUnit} onChange={(e) => setQuickAddUnit(e.target.value)}>
              <option value="">Choose…</option>
              {units.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
          </Field>
          <Field label="Selling price" required hint="What you'll charge customers for it">
            <input className="input" type="number" value={quickAddPrice} onChange={(e) => setQuickAddPrice(e.target.value)} />
          </Field>
          {quickAddError && <p className="inline-error">{quickAddError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleQuickAddProduct} disabled={quickAddSubmitting}>
            {quickAddSubmitting ? "Saving…" : "Add product & use it here"}
          </button>
        </Modal>
      )}

      {receivingPO && (
        <Modal title={`Receive goods — ${receivingPO.reference_number}`} onClose={() => setReceivingPO(null)}>
          <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
            Enter what actually arrived for each item. A mismatch with what was ordered is flagged, not hidden.
          </p>
          {receivingPO.items.map((item) => {
            const product = products.find((p) => p.id === item.product);
            return (
              <div key={item.id} style={{ marginBottom: 12 }}>
                <Field label={`${product?.name || "Item"} (ordered ${item.quantity_ordered})`}>
                  <input
                    className="input" type="number" min={0} step="0.001"
                    value={receiveQtys[item.id] || ""}
                    onChange={(e) => setReceiveQtys((q) => ({ ...q, [item.id]: e.target.value }))}
                  />
                </Field>
                {product?.track_batches && (
                  <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                    <input
                      className="input" placeholder="Batch number"
                      value={receiveBatchNumbers[item.id] || ""}
                      onChange={(e) => setReceiveBatchNumbers((b) => ({ ...b, [item.id]: e.target.value }))}
                    />
                    {product?.track_expiry && (
                      <input
                        className="input" type="date" placeholder="Expiry date"
                        value={receiveExpiryDates[item.id] || ""}
                        onChange={(e) => setReceiveExpiryDates((d) => ({ ...d, [item.id]: e.target.value }))}
                      />
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {receiveError && <p className="inline-error">{receiveError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleReceive} disabled={receiveSubmitting}>
            {receiveSubmitting ? "Recording…" : "Confirm receipt"}
          </button>
        </Modal>
      )}
    </div>
  );
}
