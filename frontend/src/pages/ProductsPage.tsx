import { useEffect, useState, Fragment } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import LogoDropzone from "../components/LogoDropzone";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { getProducts, getUnits, createUnit, createProduct, updateProduct, suggestPrice, updateCostPrice, getBundleItems, addBundleItem, removeBundleItem, getProductBatches, createStockMovement } from "../api/resources";
import type { Product, UnitOfMeasure, PriceSuggestion, ProductBundleItem, ProductBatch } from "../api/types";
import { formatMoney, formatDate, extractErrorMessage } from "../lib/format";

const emptyForm = {
  name: "", sku: "", barcode: "", cost_price: "", selling_price: "", reorder_level: "0", base_unit: "",
  track_batches: false, track_expiry: false, starting_quantity: "",
};

export default function ProductsPage() {
  const { hasPermission } = useAuth();
  const { activeBranchId } = useBusiness();
  const canManageProducts = hasPermission("manage_products");
  const canViewProfit = hasPermission("view_profit");
  const [products, setProducts] = useState<Product[]>([]);
  const [units, setUnits] = useState<UnitOfMeasure[]>([]);
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [showStockPrompt, setShowStockPrompt] = useState<"recorded" | "needed" | false>(false);
  const [form, setForm] = useState(emptyForm);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [newUnitName, setNewUnitName] = useState("");
  const [newUnitAbbr, setNewUnitAbbr] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [priceProduct, setPriceProduct] = useState<Product | null>(null);
  const [newCost, setNewCost] = useState("");

  // Variants: opening the "Add product" modal from a specific
  // product's "+ Variant" button pre-fills the parent link.
  const [variantParent, setVariantParent] = useState<Product | null>(null);
  const [variantAttrKey, setVariantAttrKey] = useState("");
  const [variantAttrValue, setVariantAttrValue] = useState("");

  // Bundles: a separate small modal for managing what's inside one.
  const [bundleProduct, setBundleProduct] = useState<Product | null>(null);
  const [bundleItems, setBundleItems] = useState<ProductBundleItem[]>([]);
  const [bundleComponentId, setBundleComponentId] = useState("");
  const [bundleQty, setBundleQty] = useState("1");
  const [bundleError, setBundleError] = useState<string | null>(null);
  const [bundleSubmitting, setBundleSubmitting] = useState(false);
  const [isBundleForm, setIsBundleForm] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [expandedVariants, setExpandedVariants] = useState<string | null>(null);
  const [batchProduct, setBatchProduct] = useState<Product | null>(null);
  const [batches, setBatches] = useState<ProductBatch[]>([]);
  const [batchesLoading, setBatchesLoading] = useState(false);

  async function openBatches(p: Product) {
    setBatchProduct(p);
    setBatchesLoading(true);
    try {
      setBatches(await getProductBatches(p.id));
    } finally {
      setBatchesLoading(false);
    }
  }
  const [suggestion, setSuggestion] = useState<PriceSuggestion | null>(null);
  const [chosenSellingPrice, setChosenSellingPrice] = useState("");
  const [priceError, setPriceError] = useState<string | null>(null);
  const [priceSubmitting, setPriceSubmitting] = useState(false);

  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [editImageFile, setEditImageFile] = useState<File | null>(null);
  const [editImagePreview, setEditImagePreview] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);

  const emptyBulkRow = () => ({ name: "", sku: "", cost_price: "", selling_price: "", base_unit: "", starting_quantity: "", error: "" });
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [bulkRows, setBulkRows] = useState<ReturnType<typeof emptyBulkRow>[]>([]);
  const [bulkSubmitting, setBulkSubmitting] = useState(false);
  const [bulkDoneCount, setBulkDoneCount] = useState(0);

  function refresh() {
    setLoading(true);
    Promise.allSettled([getProducts(), getUnits()]).then(([p, u]) => {
      if (p.status === "fulfilled") setProducts(p.value); else console.error("Failed to load products:", p.reason);
      if (u.status === "fulfilled") setUnits(u.value); else console.error("Failed to load units:", u.reason);
    }).finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  const filtered = products
    .filter((p) => !p.parent_product) // variants show nested under their parent, not as their own top-level row
    .filter((p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) || p.sku.toLowerCase().includes(search.toLowerCase())
    );

  async function handleAddUnit() {
    if (!newUnitName || !newUnitAbbr) return;
    const unit = await createUnit({ name: newUnitName, abbreviation: newUnitAbbr });
    setUnits((u) => [...u, unit]);
    setForm((f) => ({ ...f, base_unit: unit.id }));
    setNewUnitName(""); setNewUnitAbbr("");
  }

  function openBulkModal() {
    setBulkRows([emptyBulkRow(), emptyBulkRow(), emptyBulkRow()]);
    setBulkDoneCount(0);
    setShowBulkModal(true);
  }

  function updateBulkRow(index: number, field: keyof ReturnType<typeof emptyBulkRow>, value: string) {
    setBulkRows((rows) => rows.map((r, i) => (i === index ? { ...r, [field]: value, error: "" } : r)));
  }

  function addBulkRow() {
    setBulkRows((rows) => [...rows, emptyBulkRow()]);
  }

  function removeBulkRow(index: number) {
    setBulkRows((rows) => rows.filter((_, i) => i !== index));
  }

  async function handleBulkSubmit() {
    // Rows left completely blank are just unused extra slots — skip
    // them rather than forcing the person to delete each one.
    const candidates = bulkRows
      .map((row, index) => ({ row, index }))
      .filter(({ row }) => row.name.trim() || row.sku.trim() || row.selling_price.trim());

    if (candidates.length === 0) return;

    setBulkSubmitting(true);
    setBulkDoneCount(0);
    let anyFailed = false;
    let succeededCount = 0;
    let anyMissingStock = false;

    for (const { row, index } of candidates) {
      if (!row.name.trim() || !row.base_unit || !row.selling_price) {
        setBulkRows((rows) => rows.map((r, i) => (i === index ? { ...r, error: "Name, unit, and price are required." } : r)));
        anyFailed = true;
        continue;
      }
      try {
        const fd = new FormData();
        fd.append("name", row.name);
        fd.append("sku", row.sku);
        fd.append("barcode", "");
        fd.append("cost_price", row.cost_price || "0");
        fd.append("selling_price", row.selling_price);
        fd.append("reorder_level", "0");
        fd.append("minimum_stock_level", "0");
        fd.append("base_unit", row.base_unit);
        const created = await createProduct(fd);
        const startingQty = parseFloat(row.starting_quantity);
        if (startingQty > 0 && activeBranchId) {
          try {
            await createStockMovement({
              product: created.id, branch: activeBranchId, quantity_delta: startingQty, reason: "opening_stock",
              reference_note: "Starting stock recorded when the product was added.",
            });
          } catch {
            // Product itself saved fine — the reminder banner below
            // still gives a way to get stock counted if this fails.
            anyMissingStock = true;
          }
        } else {
          anyMissingStock = true;
        }
        setBulkDoneCount((n) => n + 1);
        succeededCount++;
      } catch (err: any) {
        setBulkRows((rows) => rows.map((r, i) => (i === index ? { ...r, error: extractErrorMessage(err, "Couldn't save.") } : r)));
        anyFailed = true;
      }
    }

    setBulkSubmitting(false);
    refresh();
    if (succeededCount > 0) setShowStockPrompt(anyMissingStock ? "needed" : "recorded");
    // Only the rows that actually failed stay on screen to fix and
    // retry — everything that saved successfully is gone, since it's
    // already in the product list below.
    if (!anyFailed) {
      setShowBulkModal(false);
    } else {
      setBulkRows((rows) => rows.filter((r) => r.error));
    }
  }

  async function handleSubmit() {
    if (!form.name || !form.base_unit || !form.selling_price) {
      setError("Name, unit, and selling price are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("name", form.name);
      fd.append("sku", form.sku);
      fd.append("barcode", form.barcode);
      fd.append("cost_price", form.cost_price || "0");
      fd.append("selling_price", form.selling_price);
      fd.append("reorder_level", form.reorder_level || "0");
      fd.append("minimum_stock_level", "0");
      fd.append("base_unit", form.base_unit);
      fd.append("track_batches", String(form.track_batches));
      fd.append("track_expiry", String(form.track_expiry));
      if (imageFile) fd.append("image", imageFile);
      if (variantParent) {
        fd.append("parent_product", variantParent.id);
        if (variantAttrKey.trim()) {
          fd.append("variant_attributes", JSON.stringify({ [variantAttrKey.trim()]: variantAttrValue.trim() }));
        }
      }
      if (isBundleForm) fd.append("is_bundle", "true");
      const created = await createProduct(fd);

      let recordedStartingStock = false;
      const startingQty = parseFloat(form.starting_quantity);
      if (!isBundleForm && startingQty > 0 && activeBranchId) {
        try {
          await createStockMovement({
            product: created.id, branch: activeBranchId, quantity_delta: startingQty, reason: "opening_stock",
            reference_note: "Starting stock recorded when the product was added.",
          });
          recordedStartingStock = true;
        } catch {
          // Product itself saved fine either way — if this one extra
          // call fails, the "record supplier & quantity" reminder
          // below still gives them a way to get stock counted.
        }
      }

      setShowModal(false);
      setShowStockPrompt(recordedStartingStock ? "recorded" : "needed");
      setForm(emptyForm);
      setImageFile(null);
      setImagePreviewUrl(null);
      setVariantParent(null);
      setVariantAttrKey("");
      setVariantAttrValue("");
      setIsBundleForm(false);
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save the product."));
    } finally {
      setSubmitting(false);
    }
  }

  function openVariantModal(parent: Product) {
    setVariantParent(parent);
    setForm({ ...emptyForm, base_unit: parent.base_unit, cost_price: parent.cost_price ?? "", selling_price: parent.selling_price });
    setShowModal(true);
  }

  async function openBundleModal(p: Product) {
    setBundleProduct(p);
    setBundleError(null);
    setBundleComponentId("");
    setBundleQty("1");
    try {
      setBundleItems(await getBundleItems(p.id));
    } catch (err) {
      console.error("Failed to load bundle items:", err);
    }
  }

  async function handleAddBundleItem() {
    if (!bundleProduct || !bundleComponentId) return;
    setBundleSubmitting(true);
    setBundleError(null);
    try {
      await addBundleItem({ bundle: bundleProduct.id, component: bundleComponentId, quantity: parseFloat(bundleQty) || 1 });
      setBundleItems(await getBundleItems(bundleProduct.id));
      setBundleComponentId("");
      setBundleQty("1");
    } catch (err: any) {
      setBundleError(extractErrorMessage(err, "Couldn't add that component."));
    } finally {
      setBundleSubmitting(false);
    }
  }

  async function handleRemoveBundleItem(itemId: string) {
    if (!bundleProduct) return;
    try {
      await removeBundleItem(itemId);
      setBundleItems(await getBundleItems(bundleProduct.id));
    } catch (err: any) {
      setBundleError(extractErrorMessage(err, "Couldn't remove that component."));
    }
  }

  function openPriceModal(p: Product) {
    setPriceProduct(p);
    setNewCost(p.cost_price ?? "0");
    setSuggestion(null);
    setChosenSellingPrice("");
    setPriceError(null);
  }

  function openEditModal(p: Product) {
    setEditingProduct(p);
    setEditImageFile(null);
    setEditImagePreview(p.image);
    setEditError(null);
  }

  async function handleSaveEdit() {
    if (!editingProduct) return;
    setEditSubmitting(true); setEditError(null);
    try {
      const fd = new FormData();
      if (editImageFile) fd.append("image", editImageFile);
      await updateProduct(editingProduct.id, fd);
      setEditingProduct(null);
      refresh();
    } catch (err: any) {
      setEditError(extractErrorMessage(err, "Couldn't update the product."));
    } finally {
      setEditSubmitting(false);
    }
  }

  async function handlePreview() {
    if (!priceProduct || !newCost) return;
    setPriceError(null);
    try {
      const s = await suggestPrice(priceProduct.id, parseFloat(newCost));
      setSuggestion(s);
      setChosenSellingPrice(s.suggested_selling_price);
    } catch (err: any) {
      setPriceError(extractErrorMessage(err, "Couldn't calculate a suggestion."));
    }
  }

  async function handleApplyPrice() {
    if (!priceProduct || !newCost) return;
    setPriceSubmitting(true);
    setPriceError(null);
    try {
      await updateCostPrice(priceProduct.id, {
        new_cost_price: parseFloat(newCost),
        new_selling_price: chosenSellingPrice ? parseFloat(chosenSellingPrice) : undefined,
        reason: "Cost price updated from Products screen",
      });
      setPriceProduct(null);
      refresh();
    } catch (err: any) {
      setPriceError(extractErrorMessage(err, "Couldn't update the price."));
    } finally {
      setPriceSubmitting(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Products"
        subtitle="What you sell — prices, units, reorder levels, and whether each one is making or losing you money."
        actions={
          canManageProducts ? (
            <div style={{ display: "flex", gap: 10 }}>
              <button className="btn btn-ghost" onClick={openBulkModal}>Bulk add</button>
              <button
                className="btn btn-primary"
                onClick={() => {
                  setVariantParent(null); setVariantAttrKey(""); setVariantAttrValue(""); setIsBundleForm(false); setShowAdvanced(false);
                  setForm({ ...emptyForm, base_unit: units[0]?.id || "" });
                  setShowModal(true);
                }}
              >
                Add product
              </button>
            </div>
          ) : undefined
        }
      />

      {showStockPrompt && (
        <div className="card" style={{ padding: "14px 18px", marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, background: "var(--vault-100)" }}>
          <span style={{ fontSize: 15.5 }}>
            {showStockPrompt === "recorded" ? (
              <>Product saved and starting stock recorded. Buying more from a supplier later? <strong>Record it against a purchase order</strong> to keep supplier and cost history accurate.</>
            ) : (
              <>Product saved. Don't forget to record <strong>who supplied it and how much you received</strong> —
              that's what actually adds it to your stock count and keeps your supplier history accurate.</>
            )}
          </span>
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            <Link to="/purchase-orders" className="btn btn-primary">Record supplier &amp; quantity</Link>
            <button className="btn btn-ghost" onClick={() => setShowStockPrompt(false)}>Later</button>
          </div>
        </div>
      )}

      <div className="toolbar">
        <input className="input" placeholder="Search products…" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <div className="card">
        {loading ? (
          <div className="loading-row">Loading products…</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No products yet" subtitle="Add your first product to start selling." /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th></th><th>Name</th><th>SKU</th>{canViewProfit && <><th className="num">Cost</th></>}<th className="num">Price</th>{canViewProfit && <><th className="num">Profit / unit</th><th className="num">Margin</th></>}<th></th></tr></thead>
            <tbody>
              {filtered.map((p) => (
                <Fragment key={p.id}>
                <tr>
                  <td>
                    {p.image ? (
                      <img src={p.image} alt={p.name} style={{ width: 56, height: 56, objectFit: "cover", borderRadius: 8, border: "1px solid var(--line)" }} />
                    ) : (
                      <div style={{ width: 56, height: 56, borderRadius: 8, background: "var(--paper-100)" }} />
                    )}
                  </td>
                  <td>
                    {p.name}
                    {p.is_bundle && <span className="badge badge--neutral" style={{ marginLeft: 6 }}>Bundle</span>}
                    {p.variants.length > 0 && (
                      <button
                        className="btn btn-ghost"
                        style={{ marginLeft: 6, padding: "2px 8px", fontSize: 13.5 }}
                        onClick={() => setExpandedVariants(expandedVariants === p.id ? null : p.id)}
                      >
                        {p.variants.length} variant{p.variants.length === 1 ? "" : "s"} {expandedVariants === p.id ? "▲" : "▼"}
                      </button>
                    )}
                  </td>
                  <td>{p.sku}</td>
                  {canViewProfit && <td className="num">{formatMoney(p.cost_price ?? "0")}</td>}
                  <td className="num">{formatMoney(p.selling_price)}</td>
                  {canViewProfit && (
                    <>
                      <td className="num" style={{ color: p.is_at_loss ? "var(--red-600)" : "var(--green-600)" }}>
                        {formatMoney(p.profit_amount ?? "0")}
                      </td>
                      <td className="num">
                        <span className={`badge badge--${p.is_at_loss ? "critical" : "good"}`}>
                          {p.is_at_loss ? "Losing" : "Gaining"} · {p.profit_margin_percent ?? "0"}%
                        </span>
                      </td>
                    </>
                  )}
                  <td>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {canManageProducts && <button className="btn btn-ghost" onClick={() => openEditModal(p)}>Edit photo</button>}
                      {canManageProducts && canViewProfit && <button className="btn btn-ghost" onClick={() => openPriceModal(p)}>Update cost</button>}
                      {canManageProducts && !p.is_bundle && <button className="btn btn-ghost" onClick={() => openVariantModal(p)}>+ Variant</button>}
                      {canManageProducts && p.is_bundle && <button className="btn btn-ghost" onClick={() => openBundleModal(p)}>Manage bundle</button>}
                      {p.track_batches && <button className="btn btn-ghost" onClick={() => openBatches(p)}>Batches</button>}
                    </div>
                  </td>
                </tr>
                {expandedVariants === p.id && p.variants.map((v) => (
                  <tr key={v.id} style={{ background: "var(--paper-100)" }}>
                    <td></td>
                    <td style={{ paddingLeft: 24, fontSize: 15 }}>
                      ↳ {v.name}
                      {Object.entries(v.variant_attributes || {}).map(([k, val]) => (
                        <span key={k} className="badge badge--neutral" style={{ marginLeft: 6 }}>{k}: {val}</span>
                      ))}
                      {!v.is_active && <span className="badge badge--critical" style={{ marginLeft: 6 }}>Inactive</span>}
                    </td>
                    <td style={{ fontSize: 15 }}>{v.sku}</td>
                    {canViewProfit && <td className="num" style={{ fontSize: 15 }}>{formatMoney(v.cost_price ?? "0")}</td>}
                    <td className="num" style={{ fontSize: 15 }}>{formatMoney(v.selling_price)}</td>
                    {canViewProfit && <><td></td><td></td></>}
                    <td></td>
                  </tr>
                ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <Modal title={variantParent ? `Add variant of ${variantParent.name}` : "Add product"} onClose={() => setShowModal(false)}>
          {variantParent && (
            <div style={{ background: "var(--paper-100)", borderRadius: 8, padding: "10px 14px", marginBottom: 16, fontSize: 15 }}>
              This will be a variant of <strong>{variantParent.name}</strong> — it gets its own price and stock,
              just grouped under the parent for browsing.
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <input className="input" placeholder="Attribute (e.g. Color)" value={variantAttrKey} onChange={(e) => setVariantAttrKey(e.target.value)} />
                <input className="input" placeholder="Value (e.g. Red)" value={variantAttrValue} onChange={(e) => setVariantAttrValue(e.target.value)} />
              </div>
            </div>
          )}
          {!variantParent && showAdvanced && (
            <Field label="" hint="A bundle sells as one item but deducts stock from multiple underlying products — e.g. a 'Combo Meal' that decrements burger, fries, and drink stock separately.">
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 15.5, cursor: "pointer" }}>
                <input type="checkbox" checked={isBundleForm} onChange={(e) => setIsBundleForm(e.target.checked)} />
                This is a bundle of other products
              </label>
            </Field>
          )}
          <Field label="Product photo" hint="Optional — helps staff spot the right item fast in the POS">
            <LogoDropzone
              previewUrl={imagePreviewUrl}
              onSelect={(file) => { setImageFile(file); setImagePreviewUrl(URL.createObjectURL(file)); }}
              onClear={() => { setImageFile(null); setImagePreviewUrl(null); }}
            />
          </Field>
          <div className="form-grid">
            <div className="field--half"><Field label="Product name" required>
              <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field></div>
            <div className="field--half"><Field label="Selling price" required hint="What you hope to sell it for">
              <input className="input" type="number" value={form.selling_price} onChange={(e) => setForm({ ...form, selling_price: e.target.value })} />
            </Field></div>
            <div className="field--half"><Field label="Cost price" hint="What you paid for it — optional">
              <input className="input" type="number" value={form.cost_price} onChange={(e) => setForm({ ...form, cost_price: e.target.value })} />
            </Field></div>
            {!isBundleForm && (
              <div className="field--half"><Field label="How many do you have right now?" hint="Optional — leave blank if you'll record this when the supplier delivers it instead">
                <input className="input" type="number" min="0" value={form.starting_quantity} onChange={(e) => setForm({ ...form, starting_quantity: e.target.value })} placeholder="0" />
              </Field></div>
            )}
          </div>

          {form.cost_price && form.selling_price && (
            <ProfitPreview cost={form.cost_price} price={form.selling_price} />
          )}

          <button
            type="button"
            className="btn btn-ghost"
            style={{ marginBottom: 16, padding: "4px 0" }}
            onClick={() => setShowAdvanced((v) => !v)}
          >
            {showAdvanced ? "▲ Hide advanced options" : "▼ More options (SKU, barcode, batches, reorder alerts…)"}
          </button>

          {showAdvanced && (
            <>
              <div className="form-grid">
                <div className="field--half"><Field label="SKU" hint="Leave blank to auto-fill">
                  <input className="input" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
                </Field></div>
                <div className="field--half"><Field label="Barcode">
                  <input className="input" value={form.barcode} onChange={(e) => setForm({ ...form, barcode: e.target.value })} />
                </Field></div>
                <div className="field--half"><Field label="Reorder level" hint="Alert when stock falls to this">
                  <input className="input" type="number" value={form.reorder_level} onChange={(e) => setForm({ ...form, reorder_level: e.target.value })} />
                </Field></div>
              </div>

              <div style={{ display: "flex", gap: 20, marginBottom: 16 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 15, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={form.track_batches}
                    onChange={(e) => setForm({ ...form, track_batches: e.target.checked, track_expiry: e.target.checked ? form.track_expiry : false })}
                  />
                  Track batches
                </label>
                {form.track_batches && (
                  <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 15, cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={form.track_expiry}
                      onChange={(e) => setForm({ ...form, track_expiry: e.target.checked })}
                    />
                    Track expiry dates
                  </label>
                )}
              </div>
              {form.track_batches && (
                <p style={{ fontSize: 14, color: "var(--ink-300)", marginTop: -12, marginBottom: 16 }}>
                  You'll enter the batch number{form.track_expiry ? " and expiry date" : ""} when you receive stock for this product.
                </p>
              )}

              <Field label="Unit of measure" required hint="Defaults to Piece — change it if this is sold by weight, volume, or a case">
                <select className="input" value={form.base_unit} onChange={(e) => setForm({ ...form, base_unit: e.target.value })}>
                  <option value="">Select…</option>
                  {units.map((u) => <option key={u.id} value={u.id}>{u.name} ({u.abbreviation})</option>)}
                </select>
              </Field>
              <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
                <input className="input" placeholder="New unit name" value={newUnitName} onChange={(e) => setNewUnitName(e.target.value)} />
                <input className="input" placeholder="Abbr." style={{ width: 80 }} value={newUnitAbbr} onChange={(e) => setNewUnitAbbr(e.target.value)} />
                <button type="button" className="btn btn-ghost" onClick={handleAddUnit}>Add unit</button>

          </div>
            </>
          )}

          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Saving…" : "Save product"}
          </button>
        </Modal>
      )}

      {priceProduct && (
        <Modal title={`Update cost price — ${priceProduct.name}`} onClose={() => setPriceProduct(null)}>
          <p style={{ fontSize: 15.5, color: "var(--ink-600)", marginBottom: 18 }}>
            Currently: cost {formatMoney(priceProduct.cost_price ?? "0")}, selling {formatMoney(priceProduct.selling_price)}.
            When your buying price changes, enter the new cost — the system suggests a selling price that keeps
            your usual margin, so old stock doesn't quietly turn into a loss.
          </p>
          <Field label="New cost price" required>
            <div style={{ display: "flex", gap: 8 }}>
              <input className="input" type="number" value={newCost} onChange={(e) => setNewCost(e.target.value)} />
              <button type="button" className="btn btn-ghost" onClick={handlePreview}>Calculate suggestion</button>
            </div>
          </Field>

          {suggestion && (
            <div className="card" style={{ padding: 16, marginBottom: 18, background: "var(--paper-100)" }}>
              {suggestion.would_sell_at_loss_if_price_unchanged && (
                <p style={{ color: "var(--red-600)", fontSize: 15, fontWeight: 600, marginBottom: 8 }}>
                  ⚠ At the current selling price, you'd now be selling this at a loss.
                </p>
              )}
              <p style={{ fontSize: 15, marginBottom: 4 }}>
                Suggested selling price to keep your margin: <strong>{formatMoney(suggestion.suggested_selling_price)}</strong>
              </p>
              <p style={{ fontSize: 14.5, color: "var(--ink-300)" }}>
                {suggestion.current_stock_on_hand} unit(s) currently on hand.
              </p>
            </div>
          )}

          <Field label="Selling price to apply" hint="Adjust if you want a different price than suggested">
            <input className="input" type="number" value={chosenSellingPrice} onChange={(e) => setChosenSellingPrice(e.target.value)} />
          </Field>

          {priceError && <p className="inline-error">{priceError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleApplyPrice} disabled={priceSubmitting}>
            {priceSubmitting ? "Applying…" : "Apply new price"}
          </button>
        </Modal>
      )}

      {showBulkModal && (
        <Modal title="Bulk add products" onClose={() => setShowBulkModal(false)} width={720}>
          <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 14 }}>
            Add several products in one go — fill in each row and save. Add photos individually
            afterward from the product list if you want them.
          </p>
          <div style={{ maxHeight: 380, overflowY: "auto", marginBottom: 12 }}>
            {bulkRows.map((row, i) => (
              <div key={i}>
                <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr 1fr auto", gap: 8, alignItems: "start", marginBottom: 6 }}>
                  <input className="input" placeholder="Product name" value={row.name} onChange={(e) => updateBulkRow(i, "name", e.target.value)} />
                  <input className="input" placeholder="SKU" value={row.sku} onChange={(e) => updateBulkRow(i, "sku", e.target.value)} />
                  <input className="input" type="number" placeholder="Cost" value={row.cost_price} onChange={(e) => updateBulkRow(i, "cost_price", e.target.value)} />
                  <input className="input" type="number" placeholder="Price" value={row.selling_price} onChange={(e) => updateBulkRow(i, "selling_price", e.target.value)} />
                  <select className="input" value={row.base_unit} onChange={(e) => updateBulkRow(i, "base_unit", e.target.value)}>
                    <option value="">Unit…</option>
                    {units.map((u) => <option key={u.id} value={u.id}>{u.abbreviation}</option>)}
                  </select>
                  <input className="input" type="number" min="0" placeholder="Qty on hand" value={row.starting_quantity} onChange={(e) => updateBulkRow(i, "starting_quantity", e.target.value)} />
                  <button className="btn btn-ghost" onClick={() => removeBulkRow(i)} aria-label="Remove row">✕</button>
                </div>
                {row.error && <p className="inline-error" style={{ marginTop: -2, marginBottom: 8 }}>{row.error}</p>}
              </div>
            ))}
          </div>
          <button className="btn btn-ghost" onClick={addBulkRow} style={{ marginBottom: 14 }}>+ Add row</button>
          {bulkSubmitting && <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginBottom: 8 }}>Saved {bulkDoneCount} so far…</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleBulkSubmit} disabled={bulkSubmitting}>
            {bulkSubmitting ? "Saving…" : `Save ${bulkRows.filter((r) => r.name.trim()).length || ""} products`}
          </button>
        </Modal>
      )}

      {editingProduct && (
        <Modal title={`Edit photo — ${editingProduct.name}`} onClose={() => setEditingProduct(null)}>
          <Field label="Product photo">
            <LogoDropzone
              previewUrl={editImagePreview}
              onSelect={(file) => { setEditImageFile(file); setEditImagePreview(URL.createObjectURL(file)); }}
              onClear={() => { setEditImageFile(null); setEditImagePreview(null); }}
            />
          </Field>
          {editError && <p className="inline-error">{editError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleSaveEdit} disabled={editSubmitting}>
            {editSubmitting ? "Saving…" : "Save photo"}
          </button>
        </Modal>
      )}

      {batchProduct && (
        <Modal title={`Batches — ${batchProduct.name}`} onClose={() => setBatchProduct(null)}>
          {batchesLoading ? (
            <div className="loading-row">Loading…</div>
          ) : batches.length === 0 ? (
            <p style={{ fontSize: 15, color: "var(--ink-300)" }}>
              No batches recorded yet — batches are added when you receive stock for this product from a
              Purchase Order.
            </p>
          ) : (
            <table className="data-table">
              <thead><tr><th>Batch number</th><th className="num">Quantity received</th><th>Expiry date</th></tr></thead>
              <tbody>
                {batches.map((b) => {
                  const expiringSoon = b.expiry_date && (new Date(b.expiry_date).getTime() - Date.now()) < 14 * 86400000;
                  return (
                    <tr key={b.id}>
                      <td>{b.batch_number}</td>
                      <td className="num">{b.quantity_received}</td>
                      <td>
                        {b.expiry_date ? formatDate(b.expiry_date) : "—"}
                        {expiringSoon && <span className="badge badge--attention" style={{ marginLeft: 6 }}>Expiring soon</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Modal>
      )}

      {bundleProduct && (
        <Modal title={`Manage bundle — ${bundleProduct.name}`} onClose={() => setBundleProduct(null)}>
          <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
            Selling one {bundleProduct.name} will deduct each of these from stock — never the bundle's own stock,
            since a bundle isn't stocked separately.
          </p>
          {bundleItems.length === 0 ? (
            <p style={{ fontSize: 15, color: "var(--ink-300)", marginBottom: 16 }}>No components yet — add one below.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
              {bundleItems.map((item) => (
                <div key={item.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                  <span style={{ fontSize: 15.5 }}>{item.quantity} × {item.component_name}</span>
                  <button className="btn btn-ghost" onClick={() => handleRemoveBundleItem(item.id)}>Remove</button>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            <Field label="Component">
              <select className="input" value={bundleComponentId} onChange={(e) => setBundleComponentId(e.target.value)}>
                <option value="">Select a product…</option>
                {products
                  .filter((p) => !p.is_bundle && p.id !== bundleProduct.id && !p.parent_product)
                  .map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </Field>
            <Field label="Quantity">
              <input className="input" type="number" style={{ width: 90 }} value={bundleQty} onChange={(e) => setBundleQty(e.target.value)} />
            </Field>
            <button className="btn btn-primary" onClick={handleAddBundleItem} disabled={bundleSubmitting || !bundleComponentId}>
              {bundleSubmitting ? "Adding…" : "Add"}
            </button>
          </div>
          {bundleError && <p className="inline-error">{bundleError}</p>}
        </Modal>
      )}
    </div>
  );
}

function ProfitPreview({ cost, price }: { cost: string; price: string }) {
  const c = parseFloat(cost) || 0;
  const p = parseFloat(price) || 0;
  const profit = p - c;
  const margin = p > 0 ? ((profit / p) * 100).toFixed(1) : "0.0";
  return (
    <div style={{ marginBottom: 18, fontSize: 15, padding: "10px 14px", borderRadius: 8, background: "var(--paper-100)" }}>
      {profit >= 0 ? (
        <span style={{ color: "var(--green-600)" }}>You'd gain {formatMoney(profit)} per unit ({margin}% margin).</span>
      ) : (
        <span style={{ color: "var(--red-600)" }}>You'd lose {formatMoney(Math.abs(profit))} per unit at these prices.</span>
      )}
    </div>
  );
}
