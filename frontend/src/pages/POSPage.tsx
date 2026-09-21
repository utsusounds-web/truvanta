import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import CameraBarcodeScanner from "../components/CameraBarcodeScanner";
import { useBusiness } from "../context/BusinessContext";
import { getProducts, getCustomers, getShifts, createSale, fetchReceiptPdfUrl, fetchInvoicePdfUrl, getLatestExchangeRates, createCustomer, getPaymentMethods } from "../api/resources";
import { getBusiness } from "../api/tenants";
import { queueSale } from "../offline/db";
import { generateClientReference, getCachedProducts, getCachedCustomers, isOnline } from "../offline/sync";
import type { Product, Customer, Shift, PaymentInput, ExchangeRate, PaymentMethod } from "../api/types";
import { formatMoney, extractErrorMessage } from "../lib/format";
import "./POSPage.css";

interface CartLine {
  product: Product;
  quantity: number;
  unitPrice: number;
  discount: number;
}

export default function POSPage() {
  const { activeBranchId } = useBusiness();
  const [products, setProducts] = useState<Product[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [openShift, setOpenShift] = useState<Shift | null>(null);
  const [taxRatePercent, setTaxRatePercent] = useState<number>(0);
  const [search, setSearch] = useState("");
  const [cart, setCart] = useState<CartLine[]>([]);
  const [saleType, setSaleType] = useState<"cash" | "credit">("cash");
  const [customerId, setCustomerId] = useState<string>("");
  const [showAddCustomer, setShowAddCustomer] = useState(false);
  const [newCustomerName, setNewCustomerName] = useState("");
  const [newCustomerPhone, setNewCustomerPhone] = useState("");
  const [addCustomerError, setAddCustomerError] = useState<string | null>(null);
  const [addingCustomer, setAddingCustomer] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<PaymentInput["method"]>("cash");
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [amountTendered, setAmountTendered] = useState<string>("");
  const [businessCurrency, setBusinessCurrency] = useState("NGN");
  const [exchangeRates, setExchangeRates] = useState<ExchangeRate[]>([]);
  const [isForeignPayment, setIsForeignPayment] = useState(false);
  const [foreignCurrencyCode, setForeignCurrencyCode] = useState("");
  const [foreignAmount, setForeignAmount] = useState("");
  const [exchangeRateInput, setExchangeRateInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completedSaleId, setCompletedSaleId] = useState<string | null>(null);
  const [completedSaleNumber, setCompletedSaleNumber] = useState<string | null>(null);
  const [receiptUrl, setReceiptUrl] = useState<string | null>(null);
  const [receiptLoading, setReceiptLoading] = useState(false);
  const [queuedOffline, setQueuedOffline] = useState(false);

  useEffect(() => {
    getProducts({ is_active: "true" }).then(setProducts).catch((err) => {
      console.error("Failed to load products (live):", err);
      getCachedProducts().then((p) => {
        if (p && p.length > 0) {
          setProducts(p);
        } else {
          setError("Couldn't load products — check your connection, or that this device has been online at least once before to cache them for offline use.");
        }
      });
    });
    getCustomers({ is_active: "true" }).then(setCustomers).catch(() => {
      getCachedCustomers().then((c) => { if (c) setCustomers(c); });
    });
    const businessId = localStorage.getItem("sbos_business_id");
    if (businessId) {
      getBusiness(businessId).then((b) => {
        setTaxRatePercent(b.default_tax_rate_percent ? parseFloat(b.default_tax_rate_percent) : 0);
        setBusinessCurrency(b.currency_code || "NGN");
      }).catch((err) => {
        console.error("Failed to load business tax rate/currency — defaulting to 0% tax:", err);
        setError("Couldn't load your business's tax rate — sales right now will use 0% tax. Reload this page before taking payment if that's not correct.");
      });
    }
    getLatestExchangeRates().then(setExchangeRates).catch((err) => console.error("Failed to load exchange rates:", err));
    getPaymentMethods().then((methods) => {
      const active = methods.filter((m) => m.is_active);
      setPaymentMethods(active);
      // If "cash" somehow isn't first/active (shouldn't happen — it's
      // protected server-side), fall back to whatever the business
      // actually has configured as the default selection.
      if (!active.some((m) => m.code === "cash") && active.length > 0) {
        setPaymentMethod(active[0].code);
      }
    }).catch((err) => console.error("Failed to load payment methods:", err));
  }, []);

  useEffect(() => {
    if (!activeBranchId) return;
    getShifts({ branch: activeBranchId, status: "open" })
      .then((shifts) => setOpenShift(shifts[0] || null))
      .catch((err) => {
        console.error("Failed to check for an open shift:", err);
        setError("Couldn't check whether a shift is open — sales made right now may not attach to the correct shift for cash reconciliation. Reload this page before selling if possible.");
      });
  }, [activeBranchId]);

  const filteredProducts = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return products.slice(0, 12);
    return products.filter(
      (p) => p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q) || p.barcode.includes(q)
    ).slice(0, 12);
  }, [products, search]);

  function addToCart(product: Product) {
    setCart((c) => {
      const existing = c.find((l) => l.product.id === product.id);
      if (existing) {
        return c.map((l) => l.product.id === product.id ? { ...l, quantity: l.quantity + 1 } : l);
      }
      return [...c, { product, quantity: 1, unitPrice: parseFloat(product.selling_price), discount: 0 }];
    });
  }

  // A barcode scanner acts like a fast typist that ends with Enter — so an
  // exact SKU/barcode match on Enter adds instantly and clears the box for
  // the next scan, instead of making the cashier tap the tile every time.
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [showCameraScanner, setShowCameraScanner] = useState(false);

  const handleCameraDetect = useCallback((code: string) => {
    const q = code.trim().toLowerCase();
    const exact = products.find((p) => p.barcode.toLowerCase() === q || p.sku.toLowerCase() === q);
    setShowCameraScanner(false);
    if (exact) {
      addToCart(exact);
    } else {
      // No exact match — drop it in the search box instead of
      // silently discarding the scan, so the cashier can see what was
      // read and search manually if the barcode isn't in the catalog.
      setSearch(code);
      searchInputRef.current?.focus();
    }
  }, [products]);
  function handleSearchKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key !== "Enter") return;
    const q = search.trim().toLowerCase();
    if (!q) return;
    const exact = products.find((p) => p.barcode.toLowerCase() === q || p.sku.toLowerCase() === q);
    if (exact) {
      addToCart(exact);
      setSearch("");
      searchInputRef.current?.focus();
    } else if (filteredProducts.length === 1) {
      addToCart(filteredProducts[0]);
      setSearch("");
      searchInputRef.current?.focus();
    }
  }

  function updateLine(productId: string, patch: Partial<CartLine>) {
    setCart((c) => c.map((l) => l.product.id === productId ? { ...l, ...patch } : l));
  }

  function removeLine(productId: string) {
    setCart((c) => c.filter((l) => l.product.id !== productId));
  }

  const subtotal = cart.reduce((sum, l) => sum + l.quantity * l.unitPrice, 0);
  const discountTotal = cart.reduce((sum, l) => sum + l.discount, 0);
  const taxTotal = Math.max(subtotal - discountTotal, 0) * (taxRatePercent / 100);
  const grandTotal = subtotal - discountTotal + taxTotal;
  const tendered = parseFloat(amountTendered || "0");
  const changeDue = paymentMethod === "cash" && tendered > grandTotal ? tendered - grandTotal : 0;
  const foreignConvertedAmount = (parseFloat(foreignAmount || "0") * parseFloat(exchangeRateInput || "0")) || 0;

  function handleForeignCurrencyChange(code: string) {
    setForeignCurrencyCode(code);
    const match = exchangeRates.find((r) => r.currency_code === code);
    setExchangeRateInput(match ? match.rate_to_business_currency : "");
  }

  async function handleAddCustomer() {
    if (!newCustomerName.trim()) {
      setAddCustomerError("Enter a name.");
      return;
    }
    setAddingCustomer(true);
    setAddCustomerError(null);
    try {
      const customer = await createCustomer({ name: newCustomerName.trim(), phone_number: newCustomerPhone.trim() });
      setCustomers((prev) => [customer, ...prev]);
      setCustomerId(customer.id);
      setShowAddCustomer(false);
      setNewCustomerName("");
      setNewCustomerPhone("");
    } catch (err: any) {
      setAddCustomerError(extractErrorMessage(err, "Couldn't add that customer."));
    } finally {
      setAddingCustomer(false);
    }
  }

  async function handleCheckout() {
    if (!activeBranchId || cart.length === 0) return;
    setSubmitting(true);
    setError(null);
    const clientReference = generateClientReference();
    const payload = {
      branch: activeBranchId,
      customer: customerId || null,
      sale_type: saleType,
      shift: openShift?.id || null,
      tax_total: taxTotal,
      items: cart.map((l) => ({
        product: l.product.id, unit: l.product.base_unit, quantity: l.quantity,
        unit_price: l.unitPrice, discount_amount: l.discount,
      })),
      payments: saleType === "cash"
        ? [
            isForeignPayment
              ? {
                  method: paymentMethod,
                  foreign_currency_code: foreignCurrencyCode,
                  foreign_amount: parseFloat(foreignAmount || "0"),
                  exchange_rate: parseFloat(exchangeRateInput || "0"),
                }
              : { method: paymentMethod, amount: Math.min(tendered || grandTotal, grandTotal) || grandTotal },
          ]
        : [],
      client_reference: clientReference,
    };

    if (!isOnline()) {
      await queueSale({ clientReference, payload, queuedAt: new Date().toISOString() });
      setQueuedOffline(true);
      setCompletedSaleId(clientReference);
      setCart([]);
      setAmountTendered("");
      setIsForeignPayment(false);
      setForeignCurrencyCode("");
      setForeignAmount("");
      setExchangeRateInput("");
      setCustomerId("");
      setSubmitting(false);
      return;
    }

    try {
      const sale = await createSale(payload);
      setQueuedOffline(false);
      setCompletedSaleId(sale.id);
      setCompletedSaleNumber(sale.transaction_number);
      setCart([]);
      setAmountTendered("");
      setIsForeignPayment(false);
      setForeignCurrencyCode("");
      setForeignAmount("");
      setExchangeRateInput("");
      setCustomerId("");
      setReceiptLoading(true);
      fetchReceiptPdfUrl(sale.id).then(setReceiptUrl).finally(() => setReceiptLoading(false));
    } catch (err: any) {
      if (err?.code === "ERR_NETWORK") {
        // Request never reached the server — treat exactly like being offline.
        await queueSale({ clientReference, payload, queuedAt: new Date().toISOString() });
        setQueuedOffline(true);
        setCompletedSaleId(clientReference);
        setCart([]);
        setAmountTendered("");
      setIsForeignPayment(false);
      setForeignCurrencyCode("");
      setForeignAmount("");
      setExchangeRateInput("");
        setCustomerId("");
      } else {
        setError(extractErrorMessage(err, "Couldn't complete the sale. Check stock and try again."));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <PageHeader title="Point of Sale" subtitle="Search or scan a product, build the cart, take payment." />

      {!openShift && (
        <div className="inline-error" style={{ background: "#FBF1DD", color: "var(--gold-600)" }}>
          No open shift on this branch. You can still sell, but sales won't be tied to a cash reconciliation — open a shift first from the Shifts page for accurate cash control.
        </div>
      )}

      <div className="pos-shell">
        <div className="pos-catalog card">
          <div style={{ display: "flex", gap: 8 }}>
            <input
              className="input"
              placeholder="Search by name, SKU, or barcode…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              ref={searchInputRef}
              autoFocus
              style={{ flex: 1 }}
            />
            <button type="button" className="btn btn-ghost" onClick={() => setShowCameraScanner(true)} title="Scan with camera">
              📷 Scan
            </button>
          </div>
          <div className="pos-product-grid">
            {filteredProducts.length === 0 ? (
              <EmptyState title="No products found" subtitle="Add products from the Products page first." />
            ) : filteredProducts.map((p) => (
              <button key={p.id} className="pos-product-tile" onClick={() => addToCart(p)}>
                {p.image && <img src={p.image} alt="" className="pos-product-image" />}
                <span className="pos-product-name">{p.name}</span>
                <span className="pos-product-price">{formatMoney(p.selling_price)}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="pos-cart card">
          <h2 className="section-title">Cart</h2>
          {cart.length === 0 ? (
            <EmptyState title="Cart is empty" subtitle="Tap a product to add it." />
          ) : (
            <div className="pos-cart-lines">
              {cart.map((line) => (
                <div key={line.product.id} className="pos-cart-line">
                  <div className="pos-cart-line-main">
                    <span className="pos-cart-line-name">{line.product.name}</span>
                    <button className="pos-cart-line-remove" onClick={() => removeLine(line.product.id)}>✕</button>
                  </div>
                  <div className="pos-cart-line-controls">
                    <input
                      type="number" min={0.001} step={0.001} className="input pos-qty-input"
                      value={line.quantity}
                      onChange={(e) => updateLine(line.product.id, { quantity: parseFloat(e.target.value) || 0 })}
                    />
                    <span className="pos-line-total">{formatMoney(line.quantity * line.unitPrice - line.discount)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="pos-summary">
            <div className="pos-summary-row"><span>Subtotal</span><span>{formatMoney(subtotal)}</span></div>
            <div className="pos-summary-row"><span>Discount</span><span>-{formatMoney(discountTotal)}</span></div>
            {taxRatePercent > 0 && <div className="pos-summary-row"><span>Tax ({taxRatePercent}%)</span><span>{formatMoney(taxTotal)}</span></div>}
            <div className="pos-summary-row pos-summary-total"><span>Total</span><span>{formatMoney(grandTotal)}</span></div>
          </div>

          <Field label="Sale type">
            <select className="input" value={saleType} onChange={(e) => setSaleType(e.target.value as "cash" | "credit")}>
              <option value="cash">Cash / Immediate payment</option>
              <option value="credit">Credit sale</option>
            </select>
          </Field>

          {saleType === "credit" && (
            <Field label="Customer" hint="Required for credit sales — someone to owe the balance">
              <select
                className="input"
                value={customerId}
                onChange={(e) => {
                  if (e.target.value === "__new__") { setShowAddCustomer(true); return; }
                  setCustomerId(e.target.value);
                }}
              >
                <option value="">Select a customer…</option>
                {customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                <option value="__new__">+ New customer…</option>
              </select>
            </Field>
          )}

          {saleType === "cash" && (
            <>
              <Field label="Payment method">
                <select className="input" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
                  {paymentMethods.length === 0
                    ? <option value="cash">Cash</option>
                    : paymentMethods.map((m) => <option key={m.id} value={m.code}>{m.name}</option>)}
                </select>
              </Field>
              <Field label="Amount tendered" hint={changeDue > 0 ? `Change due: ${formatMoney(changeDue)}` : undefined}>
                <input
                  className="input" type="number" min={0} value={amountTendered}
                  onChange={(e) => setAmountTendered(e.target.value)}
                  placeholder={grandTotal.toFixed(2)}
                  disabled={isForeignPayment}
                />
              </Field>

              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 15, margin: "8px 0" }}>
                <input type="checkbox" checked={isForeignPayment} onChange={(e) => setIsForeignPayment(e.target.checked)} />
                Customer paid in a foreign currency
              </label>

              {isForeignPayment && (
                <div className="pos-summary" style={{ marginBottom: 12 }}>
                  <Field label="Currency">
                    <select className="input" value={foreignCurrencyCode} onChange={(e) => handleForeignCurrencyChange(e.target.value)}>
                      <option value="">Select…</option>
                      {exchangeRates.map((r) => <option key={r.currency_code} value={r.currency_code}>{r.currency_code}</option>)}
                    </select>
                  </Field>
                  <Field label="Amount received">
                    <input className="input" type="number" min={0} value={foreignAmount} onChange={(e) => setForeignAmount(e.target.value)} />
                  </Field>
                  <Field label={`Rate to ${businessCurrency}`} hint="Pre-filled from Settings — edit if today's street rate differs">
                    <input className="input" type="number" min={0} value={exchangeRateInput} onChange={(e) => setExchangeRateInput(e.target.value)} />
                  </Field>
                  {foreignCurrencyCode && foreignAmount && exchangeRateInput && (
                    <div className="pos-summary-row">
                      <span>≈ {businessCurrency}</span>
                      <span>{formatMoney(foreignConvertedAmount)}</span>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {error && <p className="inline-error">{error}</p>}

          <button
            className="btn btn-primary"
            style={{ width: "100%" }}
            disabled={
              cart.length === 0 || submitting || (saleType === "credit" && !customerId) ||
              (isForeignPayment && (!foreignCurrencyCode || !foreignAmount || !exchangeRateInput))
            }
            onClick={handleCheckout}
          >
            {submitting ? "Completing sale…" : `Complete Sale — ${formatMoney(grandTotal)}`}
          </button>
        </div>
      </div>

      {showCameraScanner && (
        <CameraBarcodeScanner onDetect={handleCameraDetect} onClose={() => setShowCameraScanner(false)} />
      )}

      {showAddCustomer && (
        <Modal
          title="New customer"
          onClose={() => { setShowAddCustomer(false); setAddCustomerError(null); setNewCustomerName(""); setNewCustomerPhone(""); }}
        >
          <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
            Just enough to extend credit to them — you can fill in the rest of their details later
            from the Customers page. Your cart stays exactly as it is.
          </p>
          <Field label="Name" required>
            <input className="input" autoFocus value={newCustomerName} onChange={(e) => setNewCustomerName(e.target.value)} />
          </Field>
          <Field label="Phone number">
            <input className="input" value={newCustomerPhone} onChange={(e) => setNewCustomerPhone(e.target.value)} />
          </Field>
          {addCustomerError && <p className="inline-error">{addCustomerError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleAddCustomer} disabled={addingCustomer}>
            {addingCustomer ? "Adding…" : "Add & select customer"}
          </button>
        </Modal>
      )}

      {completedSaleId && (
        <Modal title={queuedOffline ? "Sale saved offline" : "Sale completed"} onClose={() => { setCompletedSaleId(null); setCompletedSaleNumber(null); if (receiptUrl) URL.revokeObjectURL(receiptUrl); setReceiptUrl(null); setQueuedOffline(false); }}>
          {queuedOffline ? (
            <>
              <p style={{ color: "var(--ink-600)", fontSize: 16, marginBottom: 20 }}>
                You're offline — this sale is saved on this device and inventory will update once you're back online.
                It'll sync automatically; you won't need to re-enter it.
              </p>
              <button
                className="btn btn-primary"
                onClick={() => { setCompletedSaleId(null); setCompletedSaleNumber(null); setQueuedOffline(false); }}
              >
                Done
              </button>
            </>
          ) : (
            <>
              {completedSaleNumber && (
                <div
                  style={{
                    background: "var(--paper-100)", borderRadius: 10, padding: "14px 16px",
                    marginBottom: 16, textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: 13.5, color: "var(--ink-300)", textTransform: "uppercase", letterSpacing: 0.4 }}>
                    Receipt code
                  </div>
                  <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "monospace", letterSpacing: 0.5 }}>
                    {completedSaleNumber}
                  </div>
                  <div style={{ fontSize: 13.5, color: "var(--ink-300)", marginTop: 2 }}>
                    No customer on file? This code alone is enough to look up this sale later — for a return, a reprint, or a dispute.
                  </div>
                </div>
              )}
              <p style={{ color: "var(--ink-600)", fontSize: 16, marginBottom: 20 }}>
                The sale was posted and inventory updated. You can print or download the receipt now.
              </p>
              {receiptLoading && <p style={{ fontSize: 15, color: "var(--ink-300)" }}>Preparing receipt…</p>}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
                {receiptUrl && (
                  <a
                    className="btn btn-primary"
                    style={{ display: "inline-block", textDecoration: "none" }}
                    href={receiptUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    View / Print Receipt
                  </a>
                )}
                {completedSaleId && (
                  <button
                    className="btn btn-ghost"
                    onClick={async () => window.open(await fetchInvoicePdfUrl(completedSaleId), "_blank")}
                  >
                    Download Invoice
                  </button>
                )}
              </div>
              {/* The clear, explicit way to close this screen and get back
                  to selling — not just the small ✕ in the modal header,
                  which is easy to miss for someone standing at a till. */}
              <button
                className="btn btn-primary"
                style={{ marginTop: 20, width: "100%" }}
                onClick={() => { setCompletedSaleId(null); setCompletedSaleNumber(null); if (receiptUrl) URL.revokeObjectURL(receiptUrl); setReceiptUrl(null); }}
              >
                Done — Start Next Sale
              </button>
            </>
          )}
        </Modal>
      )}
    </div>
  );
}
