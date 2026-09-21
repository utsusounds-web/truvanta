import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import LogoDropzone from "../components/LogoDropzone";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import {
  getBusiness, updateBusinessSettings, updateBusinessLogo,
  type BusinessSettings,
} from "../api/tenants";
import { getExchangeRates, setExchangeRate, getPaymentMethods, createPaymentMethod, updatePaymentMethod, deletePaymentMethod } from "../api/resources";
import type { ExchangeRate, PaymentMethod } from "../api/types";
import { extractErrorMessage } from "../lib/format";

export default function SettingsPage() {
  const { isOwnerOrAdmin } = useAuth();
  const { refreshBusinessProfile } = useBusiness();
  const businessId = localStorage.getItem("sbos_business_id") || "";
  const [business, setBusiness] = useState<BusinessSettings | null>(null);

  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [logoSaved, setLogoSaved] = useState(false);
  const [logoError, setLogoError] = useState<string | null>(null);
  const [logoSubmitting, setLogoSubmitting] = useState(false);

  const [themeColor, setThemeColor] = useState("#E3A635");
  const [themeColorSaved, setThemeColorSaved] = useState(false);
  const [themeColorError, setThemeColorError] = useState<string | null>(null);
  const [themeColorSubmitting, setThemeColorSubmitting] = useState(false);
  const [themeSaved, setThemeSaved] = useState(false);
  const [themeError, setThemeError] = useState<string | null>(null);
  const [themeSubmitting, setThemeSubmitting] = useState(false);

  const [whatsapp, setWhatsapp] = useState("");
  const [email, setEmail] = useState("");
  const [alertsSaved, setAlertsSaved] = useState(false);
  const [alertsError, setAlertsError] = useState<string | null>(null);
  const [alertsSubmitting, setAlertsSubmitting] = useState(false);

  const [paystackPublic, setPaystackPublic] = useState("");
  const [paystackSecret, setPaystackSecret] = useState("");
  const [paystackSaved, setPaystackSaved] = useState(false);
  const [paystackError, setPaystackError] = useState<string | null>(null);
  const [paystackSubmitting, setPaystackSubmitting] = useState(false);

  const [awayEnabled, setAwayEnabled] = useState(false);
  const [discountThreshold, setDiscountThreshold] = useState("");
  const [refundThreshold, setRefundThreshold] = useState("");
  const [priceChangeThreshold, setPriceChangeThreshold] = useState("");
  const [awaySaved, setAwaySaved] = useState(false);
  const [awayError, setAwayError] = useState<string | null>(null);
  const [awaySubmitting, setAwaySubmitting] = useState(false);

  const [taxRate, setTaxRate] = useState("");
  const [taxSaved, setTaxSaved] = useState(false);
  const [taxError, setTaxError] = useState<string | null>(null);
  const [taxSubmitting, setTaxSubmitting] = useState(false);

  useEffect(() => {
    if (!businessId) return;
    getBusiness(businessId).then((b) => {
      setBusiness(b);
      setLogoPreview(b.logo_url || null);
      setThemeColor(b.theme_color || "#E3A635");
      setWhatsapp(b.notification_whatsapp_number || "");
      setEmail(b.notification_email || "");
      setPaystackPublic(b.paystack_public_key || "");
      setAwayEnabled(b.away_mode_enabled);
      setDiscountThreshold(b.away_mode_discount_threshold_percent || "");
      setRefundThreshold(b.away_mode_refund_threshold_amount || "");
      setPriceChangeThreshold(b.away_mode_price_change_threshold_percent || "");
      setTaxRate(b.default_tax_rate_percent || "");
    });
  }, [businessId]);

  async function handleSaveLogo() {
    if (!logoFile) return;
    setLogoSubmitting(true); setLogoError(null); setLogoSaved(false);
    try {
      const updated = await updateBusinessLogo(businessId, logoFile);
      setBusiness(updated);
      setLogoPreview(updated.logo_url || null);
      setLogoFile(null);
      setLogoSaved(true);
      await refreshBusinessProfile(); // so the sidebar mark updates immediately
    } catch (err: any) {
      setLogoError(extractErrorMessage(err, "Couldn't save the logo."));
    } finally {
      setLogoSubmitting(false);
    }
  }

  async function handleSaveThemeColor() {
    // No validation needed — a native colour-picker swatch can only
    // ever produce a valid hex value itself, unlike free-typed text.
    setThemeColorSubmitting(true); setThemeColorError(null); setThemeColorSaved(false);
    try {
      const updated = await updateBusinessSettings(businessId, { theme_color: themeColor });
      setBusiness(updated);
      setThemeColorSaved(true);
      await refreshBusinessProfile(); // applies the new colour across the app immediately
    } catch (err: any) {
      setThemeColorError(extractErrorMessage(err, "Couldn't save the colour."));
    } finally {
      setThemeColorSubmitting(false);
    }
  }

  function handleLogoSelect(file: File) {
    setLogoFile(file);
    setLogoPreview(URL.createObjectURL(file));
    setLogoSaved(false);
    setLogoError(null);
  }

  async function handleSaveTax() {
    setTaxSubmitting(true); setTaxError(null); setTaxSaved(false);
    try {
      const updated = await updateBusinessSettings(businessId, { default_tax_rate_percent: taxRate || null });
      setBusiness(updated);
      setTaxSaved(true);
    } catch (err: any) {
      setTaxError(extractErrorMessage(err, "Couldn't save tax settings."));
    } finally {
      setTaxSubmitting(false);
    }
  }

  async function handleSaveAlerts() {
    setAlertsSubmitting(true);
    setAlertsError(null);
    setAlertsSaved(false);
    try {
      const updated = await updateBusinessSettings(businessId, {
        notification_whatsapp_number: whatsapp,
        notification_email: email,
      });
      setBusiness(updated);
      setAlertsSaved(true);
    } catch (err: any) {
      setAlertsError(extractErrorMessage(err, "Couldn't save notification settings."));
    } finally {
      setAlertsSubmitting(false);
    }
  }

  async function handleSavePaystack() {
    setPaystackSubmitting(true);
    setPaystackError(null);
    setPaystackSaved(false);
    try {
      const updated = await updateBusinessSettings(businessId, {
        paystack_public_key: paystackPublic,
        ...(paystackSecret ? { paystack_secret_key: paystackSecret } : {}),
      });
      setBusiness(updated);
      setPaystackSecret("");
      setPaystackSaved(true);
    } catch (err: any) {
      setPaystackError(extractErrorMessage(err, "Couldn't save payment settings."));
    } finally {
      setPaystackSubmitting(false);
    }
  }

  async function handleSaveAwayMode() {
    setAwaySubmitting(true);
    setAwayError(null);
    setAwaySaved(false);
    try {
      const updated = await updateBusinessSettings(businessId, {
        away_mode_enabled: awayEnabled,
        away_mode_discount_threshold_percent: discountThreshold || null,
        away_mode_refund_threshold_amount: refundThreshold || null,
        away_mode_price_change_threshold_percent: priceChangeThreshold || null,
      });
      setBusiness(updated);
      setAwaySaved(true);
    } catch (err: any) {
      setAwayError(extractErrorMessage(err, "Couldn't save away mode settings."));
    } finally {
      setAwaySubmitting(false);
    }
  }

  return (
    <div>
      <PageHeader title="Settings" subtitle="Where alerts get sent, how you accept payments, and what's available on your plan." />

      {isOwnerOrAdmin() && (
        <div className="card" style={{ padding: 24, marginBottom: 20, maxWidth: 520 }}>
          <h2 className="section-title">Business branding</h2>
          <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 18 }}>
            This logo appears in the sidebar, on receipts, and on every document Truvanta generates for your business.
          </p>
          <LogoDropzone
            previewUrl={logoPreview}
            onSelect={handleLogoSelect}
            onClear={() => { setLogoFile(null); setLogoPreview(business?.logo_url || null); }}
            error={logoError || undefined}
          />
          {logoFile && (
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 14 }}>
              <button className="btn btn-primary" onClick={handleSaveLogo} disabled={logoSubmitting}>
                {logoSubmitting ? "Saving…" : "Save logo"}
              </button>
              {logoSaved && <span style={{ fontSize: 15, color: "var(--green-600)" }}>Saved.</span>}
            </div>
          )}

          <div style={{ marginTop: 20, paddingTop: 20, borderTop: "1px solid var(--line)" }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>This business's colour</h3>
            <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 14 }}>
              Used across your sidebar and highlights, just for your business. (This is different from
              the platform's overall default colour, which a Truvanta admin controls separately.)
              Click the swatch to choose one.
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <input
                type="color"
                value={themeColor}
                onChange={(e) => { setThemeColor(e.target.value); setThemeColorSaved(false); }}
                style={{ width: 56, height: 44, padding: 0, border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", cursor: "pointer" }}
              />
              <button className="btn btn-primary" onClick={handleSaveThemeColor} disabled={themeColorSubmitting}>
                {themeColorSubmitting ? "Saving…" : "Save colour"}
              </button>
              {themeColorSaved && !themeColorError && <span style={{ fontSize: 15, color: "var(--green-600)" }}>Saved.</span>}
            </div>
            {themeColorError && <p className="inline-error">{themeColorError}</p>}
          </div>
        </div>
      )}

      {isOwnerOrAdmin() && (
      <div className="card" style={{ padding: 24, marginBottom: 20, maxWidth: 520 }}>
        <h2 className="section-title">Alert delivery</h2>
        <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 18 }}>
          Critical and important alerts — cash variances, low stock — are sent here in addition to
          always showing up on the Notifications page.
        </p>
        <Field label="WhatsApp number" hint="Include country code, e.g. +2348012345678">
          <input className="input" value={whatsapp} onChange={(e) => setWhatsapp(e.target.value)} />
        </Field>
        <Field label="Notification email">
          <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        {alertsError && <p className="inline-error">{alertsError}</p>}
        {alertsSaved && !alertsError && <p style={{ color: "var(--green-600)", fontSize: 15, marginBottom: 14 }}>Saved.</p>}
        <button className="btn btn-primary" onClick={handleSaveAlerts} disabled={alertsSubmitting}>
          {alertsSubmitting ? "Saving…" : "Save"}
        </button>
      </div>
      )}

      {isOwnerOrAdmin() && (
      <div className="card" style={{ padding: 24, marginBottom: 20, maxWidth: 520 }}>
        <h2 className="section-title">Tax</h2>
        <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
          Set a default rate to have it applied automatically at checkout. Leave blank to charge no tax by default.
        </p>
        <Field label="Default tax rate (%)">
          <input className="input" type="number" min={0} max={100} step="0.01" value={taxRate} onChange={(e) => setTaxRate(e.target.value)} />
        </Field>
        {taxError && <p className="inline-error">{taxError}</p>}
        {taxSaved && !taxError && <p style={{ color: "var(--green-600)", fontSize: 15, marginBottom: 14 }}>Saved.</p>}
        <button className="btn btn-primary" onClick={handleSaveTax} disabled={taxSubmitting}>
          {taxSubmitting ? "Saving…" : "Save"}
        </button>
      </div>
      )}

      {isOwnerOrAdmin() && (
      <div className="card" style={{ padding: 24, marginBottom: 20, maxWidth: 520 }}>
        <h2 className="section-title">Payments — your Paystack account</h2>
        <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 18 }}>
          Add your own Paystack keys here to accept card/transfer payments from customers through the app.
          Your secret key is never shown again once saved — leave it blank to keep the current one.
        </p>
        <Field label="Paystack public key">
          <input className="input" value={paystackPublic} onChange={(e) => setPaystackPublic(e.target.value)} placeholder="pk_live_…" />
        </Field>
        <Field label="Paystack secret key" hint={business?.paystack_configured ? "A key is already saved — leave blank to keep it" : "Not set yet"}>
          <input className="input" type="password" value={paystackSecret} onChange={(e) => setPaystackSecret(e.target.value)} placeholder="sk_live_…" />
        </Field>
        {paystackError && <p className="inline-error">{paystackError}</p>}
        {paystackSaved && !paystackError && <p style={{ color: "var(--green-600)", fontSize: 15, marginBottom: 14 }}>Saved.</p>}
        <button className="btn btn-primary" onClick={handleSavePaystack} disabled={paystackSubmitting}>
          {paystackSubmitting ? "Saving…" : "Save"}
        </button>
      </div>
      )}

      {isOwnerOrAdmin() && (
      <div className="card card--vault" style={{ padding: 24, marginBottom: 20, maxWidth: 520 }}>
        <h2 className="section-title">Owner Away Mode</h2>
        <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
          When you're not physically at the shop, get an immediate alert (not just the weekly review)
          the moment a discount, refund, or price change crosses the limit you set here.
        </p>
        <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, fontSize: 15.5, fontWeight: 600, cursor: "pointer" }}>
          <input type="checkbox" checked={awayEnabled} onChange={(e) => setAwayEnabled(e.target.checked)} style={{ accentColor: "var(--vault-700)" }} />
          Away Mode enabled
        </label>
        <Field label="Discount threshold (%)" hint="Alert when a line's discount exceeds this % of its value">
          <input className="input" type="number" min={0} max={100} value={discountThreshold} onChange={(e) => setDiscountThreshold(e.target.value)} disabled={!awayEnabled} />
        </Field>
        <Field label="Refund threshold" hint="Alert when a requested refund exceeds this amount">
          <input className="input" type="number" min={0} value={refundThreshold} onChange={(e) => setRefundThreshold(e.target.value)} disabled={!awayEnabled} />
        </Field>
        <Field label="Price change threshold (%)" hint="Alert when a cost-price update changes by more than this %">
          <input className="input" type="number" min={0} max={100} value={priceChangeThreshold} onChange={(e) => setPriceChangeThreshold(e.target.value)} disabled={!awayEnabled} />
        </Field>
        {awayError && <p className="inline-error">{awayError}</p>}
        {awaySaved && !awayError && <p style={{ color: "var(--green-600)", fontSize: 15, marginBottom: 14 }}>Saved.</p>}
        <button className="btn btn-primary" onClick={handleSaveAwayMode} disabled={awaySubmitting}>
          {awaySubmitting ? "Saving…" : "Save"}
        </button>
      </div>
      )}

      <div className="card" style={{ padding: 24, marginBottom: 20, maxWidth: 520 }}>
        <h2 className="section-title">AI features</h2>
        <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 12 }}>
          Voice bookkeeping, receipt scanning, and "ask my business" are a paid add-on — not included
          by default, so every business only pays for AI if they actually want it. Subscribing will use
          the payment method above once billing is switched on.
        </p>
        <span className={`badge badge--${business?.ai_addon_enabled ? "good" : "neutral"}`}>
          {business?.ai_addon_enabled ? "AI add-on active" : "Not subscribed"}
        </span>
      </div>

      <ExchangeRatesCard businessCurrency={business?.currency_code || "NGN"} />
      {isOwnerOrAdmin() && <PaymentMethodsCard />}

      {/* Platform Integrations (staff-only WhatsApp/Gmail/Paystack credentials) now lives in the Admin console, not here. */}
    </div>
  );
}

function ExchangeRatesCard({ businessCurrency }: { businessCurrency: string }) {
  const { isOwnerOrAdmin } = useAuth();
  const [rates, setRates] = useState<ExchangeRate[]>([]);
  const [loading, setLoading] = useState(true);
  const [currencyCode, setCurrencyCode] = useState("USD");
  const [rate, setRate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    getExchangeRates().then(setRates).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  // Latest rate per currency — history stays in `rates` but only the
  // newest entry per code is worth showing at a glance.
  const latestByCode = new Map<string, ExchangeRate>();
  for (const r of rates) {
    if (!latestByCode.has(r.currency_code)) latestByCode.set(r.currency_code, r);
  }

  async function handleSave() {
    if (!currencyCode || !rate) { setError("Enter a currency code and rate."); return; }
    setSubmitting(true); setError(null);
    try {
      await setExchangeRate(currencyCode.toUpperCase(), Number(rate));
      setRate("");
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save rate."));
    } finally { setSubmitting(false); }
  }

  return (
    <div className="card" style={{ padding: 24, marginBottom: 20, maxWidth: 520 }}>
      <h2 className="section-title">Foreign currency rates</h2>
      <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 12 }}>
        No live exchange feed — set today's rate yourself when you accept a foreign-currency payment.
        Cashiers can then record a payment as e.g. "$50 at ₦1,600" and it converts to {businessCurrency}
        automatically. Update this whenever the rate changes; each payment keeps the rate that was
        actually used, so past sales are never affected by a later update.
      </p>

      {!loading && latestByCode.size > 0 && (
        <div style={{ marginBottom: 16 }}>
          {Array.from(latestByCode.values()).map((r) => (
            <div key={r.currency_code} style={{ display: "flex", justifyContent: "space-between", fontSize: 15, padding: "6px 0", borderBottom: "1px solid var(--paper-100)" }}>
              <span>1 {r.currency_code} = {r.rate_to_business_currency} {businessCurrency}</span>
              <span style={{ color: "var(--ink-300)" }}>set by {r.set_by_email || "—"}</span>
            </div>
          ))}
        </div>
      )}

      {isOwnerOrAdmin() && (
      <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
          <Field label="Currency code" hint="e.g. USD, GBP, EUR">
            <input className="input" style={{ width: 100 }} value={currencyCode} onChange={(e) => setCurrencyCode(e.target.value)} maxLength={8} />
          </Field>
          <Field label={`Rate to ${businessCurrency}`}>
            <input className="input" type="number" value={rate} onChange={(e) => setRate(e.target.value)} placeholder="e.g. 1600" />
          </Field>
          <button className="btn btn-primary" onClick={handleSave} disabled={submitting}>
            {submitting ? "Saving…" : "Set rate"}
          </button>
        </div>
      )}
      {error && <p className="inline-error">{error}</p>}
    </div>
  );
}

function PaymentMethodsCard() {
  const [methods, setMethods] = useState<PaymentMethod[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    getPaymentMethods().then(setMethods).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  async function handleAdd() {
    if (!newName.trim()) { setError("Enter a name."); return; }
    setSubmitting(true); setError(null);
    try {
      await createPaymentMethod({ name: newName.trim(), sort_order: methods.length });
      setNewName("");
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't add that payment method."));
    } finally { setSubmitting(false); }
  }

  async function handleToggle(m: PaymentMethod) {
    setError(null);
    try {
      await updatePaymentMethod(m.id, { is_active: !m.is_active });
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't update that payment method."));
    }
  }

  async function handleDelete(m: PaymentMethod) {
    setError(null);
    try {
      await deletePaymentMethod(m.id);
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't delete that payment method — it may already have sales recorded against it. Deactivate it instead."));
    }
  }

  return (
    <div className="card" style={{ padding: 24, marginBottom: 20, maxWidth: 520 }}>
      <h2 className="section-title">Payment methods</h2>
      <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
        These are the options your cashiers see at checkout. Add whatever your customers actually use —
        Mobile Money, Cheque, Crypto, anything — or turn off ones you don't accept. Cash can't be turned off,
        since cash-drawer reconciliation depends on it always being available.
      </p>
      {loading ? (
        <div className="loading-row">Loading…</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
          {methods.map((m) => (
            <div key={m.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
              <span style={{ fontSize: 15.5, color: m.is_active ? "var(--ink-800)" : "var(--ink-300)" }}>
                {m.name} {!m.is_active && <span style={{ fontSize: 13.5 }}>(off)</span>}
              </span>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn btn-ghost" onClick={() => handleToggle(m)} disabled={m.code === "cash"}>
                  {m.is_active ? "Turn off" : "Turn on"}
                </button>
                {m.code !== "cash" && (
                  <button className="btn btn-ghost" onClick={() => handleDelete(m)}>Delete</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      <div style={{ display: "flex", gap: 8 }}>
        <input className="input" placeholder="e.g. Mobile Money" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button className="btn btn-primary" onClick={handleAdd} disabled={submitting}>{submitting ? "Adding…" : "Add"}</button>
      </div>
      {error && <p className="inline-error">{error}</p>}
    </div>
  );
}

