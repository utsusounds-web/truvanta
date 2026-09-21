import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import Field from "../components/Field";
import Modal from "../components/Modal";
import { useBusiness } from "../context/BusinessContext";
import {
  getQuotations, createQuotation, addQuotationItem, removeQuotationItem,
  markQuotationSent, voidQuotation, convertQuotationToSale, fetchQuotationPdfUrl,
  getCustomers, getProducts, getUnits,
} from "../api/resources";
import type { Quotation, Customer, Product, UnitOfMeasure } from "../api/types";
import { formatMoney, formatDate, extractErrorMessage } from "../lib/format";

const STATUS_TONE: Record<string, string> = {
  draft: "neutral", sent: "attention", accepted: "good",
  expired: "critical", converted: "good", void: "critical",
};

function downloadOrOpen(url: string) {
  window.open(url, "_blank");
}

export default function QuotationsPage() {
  const { activeBranchId } = useBusiness();
  const [quotations, setQuotations] = useState<Quotation[]>([]);
  const [loading, setLoading] = useState(true);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [units, setUnits] = useState<UnitOfMeasure[]>([]);

  const [showCreate, setShowCreate] = useState(false);
  const [docType, setDocType] = useState<"quotation" | "proforma_invoice">("quotation");
  const [customerId, setCustomerId] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const [notes, setNotes] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [detail, setDetail] = useState<Quotation | null>(null);
  const [itemProduct, setItemProduct] = useState("");
  const [itemUnit, setItemUnit] = useState("");
  const [itemQty, setItemQty] = useState("1");
  const [itemPrice, setItemPrice] = useState("");
  const [itemError, setItemError] = useState<string | null>(null);
  const [itemSubmitting, setItemSubmitting] = useState(false);

  const [converting, setConverting] = useState(false);
  const [convertError, setConvertError] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    getQuotations().then(setQuotations).finally(() => setLoading(false));
  }
  useEffect(refresh, []);
  useEffect(() => {
    getCustomers().then(setCustomers).catch(() => {});
    getProducts({ is_active: "true" }).then(setProducts).catch(() => {});
    getUnits().then(setUnits).catch(() => {});
  }, []);

  async function handleCreate() {
    if (!activeBranchId) return;
    setCreating(true);
    setError(null);
    try {
      const q = await createQuotation({
        document_type: docType, branch: activeBranchId,
        customer: customerId || undefined, valid_until: validUntil || undefined, notes: notes || undefined,
      });
      setShowCreate(false);
      setCustomerId(""); setValidUntil(""); setNotes(""); setDocType("quotation");
      refresh();
      setDetail(q);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't create that."));
    } finally {
      setCreating(false);
    }
  }

  async function refreshDetail(id: string) {
    const updated = (await getQuotations()).find((q) => q.id === id);
    if (updated) setDetail(updated);
  }

  async function handleAddItem() {
    if (!detail || !itemProduct || !itemUnit) return;
    setItemSubmitting(true);
    setItemError(null);
    try {
      await addQuotationItem({
        quotation: detail.id, product: itemProduct, unit: itemUnit,
        quantity: parseFloat(itemQty) || 1, unit_price: parseFloat(itemPrice) || 0,
      });
      setItemProduct(""); setItemUnit(""); setItemQty("1"); setItemPrice("");
      await refreshDetail(detail.id);
      refresh();
    } catch (err: any) {
      setItemError(extractErrorMessage(err, "Couldn't add that item."));
    } finally {
      setItemSubmitting(false);
    }
  }

  async function handleRemoveItem(itemId: string) {
    if (!detail) return;
    await removeQuotationItem(itemId);
    await refreshDetail(detail.id);
    refresh();
  }

  async function handleConvert() {
    if (!detail) return;
    setConverting(true);
    setConvertError(null);
    try {
      await convertQuotationToSale(detail.id, { sale_type: "cash", payments: [{ method: "cash", amount: parseFloat(detail.subtotal) }] });
      await refreshDetail(detail.id);
      refresh();
    } catch (err: any) {
      setConvertError(extractErrorMessage(err, "Couldn't convert this to a sale — it may need at least one payment recorded, or check stock."));
    } finally {
      setConverting(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Quotations & Proforma Invoices"
        subtitle="Give a customer a price before anything is sold — nothing here touches stock or money until it's converted."
        actions={<button className="btn btn-primary" onClick={() => setShowCreate(true)}>New</button>}
      />

      <div className="card">
        {loading ? (
          <div className="loading-row">Loading…</div>
        ) : quotations.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No quotations yet" subtitle="Create one to send a customer a price before they commit." /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Reference</th><th>Type</th><th>Customer</th><th className="num">Total</th><th>Status</th><th>Date</th><th></th></tr></thead>
            <tbody>
              {quotations.map((q) => (
                <tr key={q.id}>
                  <td>{q.reference_number}</td>
                  <td>{q.document_type === "proforma_invoice" ? "Proforma" : "Quotation"}</td>
                  <td>{q.customer_name || "—"}</td>
                  <td className="num">{formatMoney(q.subtotal)}</td>
                  <td><span className={`badge badge--${STATUS_TONE[q.status]}`}>{q.status}</span></td>
                  <td>{formatDate(q.created_at)}</td>
                  <td><button className="btn btn-ghost" onClick={() => setDetail(q)}>Open</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <Modal title="New quotation" onClose={() => setShowCreate(false)}>
          <Field label="Type">
            <select className="input" value={docType} onChange={(e) => setDocType(e.target.value as any)}>
              <option value="quotation">Quotation</option>
              <option value="proforma_invoice">Proforma Invoice</option>
            </select>
          </Field>
          <Field label="Customer" hint="Optional">
            <select className="input" value={customerId} onChange={(e) => setCustomerId(e.target.value)}>
              <option value="">No customer on file</option>
              {customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Valid until" hint="Optional — after this date it auto-marks as expired">
            <input className="input" type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} />
          </Field>
          <Field label="Notes">
            <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleCreate} disabled={creating}>
            {creating ? "Creating…" : "Create"}
          </button>
        </Modal>
      )}

      {detail && (
        <Modal title={`${detail.document_type === "proforma_invoice" ? "Proforma" : "Quotation"} ${detail.reference_number}`} onClose={() => setDetail(null)} width={620}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
            <span className={`badge badge--${STATUS_TONE[detail.status]}`}>{detail.status}</span>
            <button className="btn btn-ghost" onClick={async () => downloadOrOpen(await fetchQuotationPdfUrl(detail.id))}>Download PDF</button>
          </div>

          {detail.items.length === 0 ? (
            <p style={{ fontSize: 15, color: "var(--ink-300)", marginBottom: 12 }}>No items yet.</p>
          ) : (
            <table className="data-table" style={{ marginBottom: 12 }}>
              <thead><tr><th>Item</th><th className="num">Qty</th><th className="num">Price</th><th className="num">Total</th><th></th></tr></thead>
              <tbody>
                {detail.items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.product_name}</td>
                    <td className="num">{item.quantity}</td>
                    <td className="num">{formatMoney(item.unit_price)}</td>
                    <td className="num">{formatMoney(item.line_total)}</td>
                    <td>{detail.status === "draft" && <button className="btn btn-ghost" onClick={() => handleRemoveItem(item.id)}>Remove</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p style={{ textAlign: "right", fontWeight: 700, marginBottom: 16 }}>Total: {formatMoney(detail.subtotal)}</p>

          {detail.status === "draft" && (
            <>
              <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 8 }}>
                <Field label="Product">
                  <select className="input" value={itemProduct} onChange={(e) => {
                    const p = products.find((pr) => pr.id === e.target.value);
                    setItemProduct(e.target.value);
                    if (p) { setItemUnit(p.base_unit); setItemPrice(p.selling_price); }
                  }}>
                    <option value="">Select…</option>
                    {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </Field>
                <Field label="Qty"><input className="input" style={{ width: 70 }} value={itemQty} onChange={(e) => setItemQty(e.target.value)} /></Field>
                <Field label="Price"><input className="input" style={{ width: 100 }} value={itemPrice} onChange={(e) => setItemPrice(e.target.value)} /></Field>
                <button className="btn btn-primary" onClick={handleAddItem} disabled={itemSubmitting || !itemProduct}>Add</button>
              </div>
              {itemError && <p className="inline-error">{itemError}</p>}
              <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                <button className="btn btn-ghost" onClick={async () => { await markQuotationSent(detail.id); await refreshDetail(detail.id); refresh(); }}>Mark as sent</button>
                <button className="btn btn-ghost" onClick={async () => { await voidQuotation(detail.id); await refreshDetail(detail.id); refresh(); }}>Void</button>
              </div>
            </>
          )}

          {(detail.status === "sent" || detail.status === "accepted") && (
            <div style={{ marginTop: 16, borderTop: "1px solid var(--line)", paddingTop: 16 }}>
              <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 10 }}>
                Ready to turn this into a real sale? This deducts stock and records payment now — assumes full cash payment.
              </p>
              <button className="btn btn-primary" onClick={handleConvert} disabled={converting}>
                {converting ? "Converting…" : "Convert to sale"}
              </button>
              <button className="btn btn-ghost" style={{ marginLeft: 8 }} onClick={async () => { await voidQuotation(detail.id); await refreshDetail(detail.id); refresh(); }}>Void</button>
              {convertError && <p className="inline-error">{convertError}</p>}
            </div>
          )}

          {detail.status === "converted" && (
            <p style={{ fontSize: 15, color: "var(--green-600)" }}>✓ Converted to a sale.</p>
          )}
        </Modal>
      )}
    </div>
  );
}
