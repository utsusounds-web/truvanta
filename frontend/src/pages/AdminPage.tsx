import { useEffect, useState } from "react";
import { Navigate, useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import {
  adminGetFeatures, adminCreateFeature, adminUpdateFeature,
  adminGetPlans, adminCreatePlan, adminUpdatePlan,
  adminGetSubscriptions, adminGetBusinesses,
  adminGetOverrides, adminCreateOverride, adminDeleteOverride,
  adminGetUsageAnalytics, adminActivateSubscription, adminBroadcastNotification,
  adminExtendTrial, adminFreezeAccount, adminKillSwitch, adminGetAuditLogs,
  adminGetTenantUsage, type TenantUsage,
  adminGetWebhookEvents, adminReplayWebhookEvent, type BillingEvent,
  adminScheduleDeletion, adminCancelDeletion, adminExecutePurge,
} from "../api/billing";
import type { Feature, Plan, Subscription, FeatureOverride, PlatformUsageSummary } from "../api/billing";
import type { AuditLog } from "../api/types";
import { formatMoney, formatDate, extractErrorMessage } from "../lib/format";
import { getPlatformSettings, updatePlatformSettings, getLatestBackup, adminSupportLogin, getAdminFeatureLayout, updateAdminFeatureLayout, type PlatformSettings, type AdminFeatureLayoutEntry } from "../api/tenants";
import type { BackupLog } from "../api/tenants";
import { applyAccentColor } from "../lib/accentColor";
import { APP_VERSION } from "../lib/appVersion";
import { FEATURE_CATALOG, HUB_TITLES, type HubKey } from "../lib/featureCatalog";

type Tab = "usage" | "plans" | "features" | "subscriptions" | "overrides" | "broadcast" | "support" | "audit" | "webhooks" | "purge" | "layout";
const TABS: Tab[] = ["usage", "plans", "features", "subscriptions", "overrides", "broadcast", "support", "audit", "webhooks", "purge", "layout"];

export default function AdminPage() {
  const { user } = useAuth();
  // The tab now lives in the URL (driven by AdminLayout's own sidebar
  // nav) rather than local state, so the admin console behaves like a
  // real standalone app — bookmarkable, back-button-able pages, not a
  // single page with buttons that forget where you were.
  const { tab: rawTab } = useParams<{ tab: string }>();
  const tab: Tab = TABS.includes(rawTab as Tab) ? (rawTab as Tab) : "usage";

  if (!user?.is_staff) return <Navigate to="/dashboard" replace />;

  return (
    <div>
      <PageHeader title="Platform Admin" subtitle="Manage paid plans, features, and who has access to what." />
      <RentModeSwitch />
      <BackupStatusCard />
      <UniversalColorCard />
      <MinimumVersionCard />
      <PlatformIntegrationsCard />
      {tab === "usage" && <UsageTab />}
      {tab === "plans" && <PlansTab />}
      {tab === "features" && <FeaturesTab />}
      {tab === "subscriptions" && <SubscriptionsTab />}
      {tab === "broadcast" && <BroadcastTab />}
      {tab === "overrides" && <OverridesTab />}
      {tab === "support" && <SupportAccessTab />}
      {tab === "audit" && <GlobalAuditTab />}
      {tab === "webhooks" && <WebhooksTab />}
      {tab === "purge" && <DataPurgeTab />}
      {tab === "layout" && <FeatureLayoutTab />}
    </div>
  );
}

// --- Rent Mode master switch ------------------------------------------

function UniversalColorCard() {
  const [color, setColor] = useState<string>("#E3A635");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getPlatformSettings().then((s) => setColor(s.universal_color || "#E3A635")).catch(() => {});
  }, []);

  async function handleSave() {
    // No validation needed here — a native colour-picker swatch can
    // only ever produce a valid hex value itself, unlike free-typed
    // text, which is exactly why typing was removed.
    setSubmitting(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updatePlatformSettings({ universal_color: color });
      setColor(updated.universal_color);
      applyAccentColor(updated.universal_color); // reflects immediately in this admin session too
      setSaved(true);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save the universal colour."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ padding: 20, marginBottom: 20, maxWidth: 480 }}>
      <h2 className="section-title">Universal colour</h2>
      <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 14 }}>
        The default accent colour shown on the login screen and used by any business that hasn't
        picked its own colour yet (Settings → Business branding always overrides this once set).
        Click the swatch to choose one.
      </p>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <input
          type="color"
          value={color}
          onChange={(e) => { setColor(e.target.value); setSaved(false); }}
          style={{ width: 56, height: 44, padding: 0, border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", cursor: "pointer" }}
        />
        <button className="btn btn-primary" onClick={handleSave} disabled={submitting}>
          {submitting ? "Saving…" : "Save"}
        </button>
        {saved && !error && <span style={{ fontSize: 15, color: "var(--green-600)" }}>Saved.</span>}
      </div>
      {error && <p className="inline-error">{error}</p>}
    </div>
  );
}

function MinimumVersionCard() {
  const [version, setVersion] = useState("");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getPlatformSettings().then((s) => setVersion(s.minimum_client_version || "")).catch(() => {});
  }, []);

  async function handleSave() {
    setSubmitting(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updatePlatformSettings({ minimum_client_version: version });
      setVersion(updated.minimum_client_version);
      setSaved(true);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ padding: 20, marginBottom: 20, maxWidth: 480 }}>
      <h2 className="section-title">Minimum client version</h2>
      <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 14 }}>
        Raise this after shipping a build with a critical fix (e.g. ledger math) — anyone on an
        older build gets a full-screen "please refresh" notice until they update. Leave blank to
        never force a refresh. Current app version: <code>{APP_VERSION}</code>.
      </p>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <input
          className="input"
          placeholder="e.g. 1.2.0 — blank to disable"
          value={version}
          onChange={(e) => { setVersion(e.target.value); setSaved(false); }}
          style={{ maxWidth: 200, fontFamily: "var(--font-mono)" }}
        />
        <button className="btn btn-primary" onClick={handleSave} disabled={submitting}>
          {submitting ? "Saving…" : "Save"}
        </button>
        {saved && !error && <span style={{ fontSize: 15, color: "var(--green-600)" }}>Saved.</span>}
      </div>
      {error && <p className="inline-error">{error}</p>}
    </div>
  );
}

function RentModeSwitch() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPlatformSettings().then((s) => setEnabled(s.rent_mode_enabled)).catch(() => setEnabled(false));
  }, []);

  async function toggle() {
    if (enabled === null) return;
    const next = !enabled;
    setSaving(true);
    setError(null);
    try {
      await updatePlatformSettings({ rent_mode_enabled: next });
      setEnabled(next);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't update Rent Mode."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ marginBottom: 20 }}>
      <div
        className="card"
        style={{
          padding: 20, display: "flex", justifyContent: "space-between", alignItems: "center",
          border: enabled ? "1px solid var(--gold-600, #b8860b)" : undefined,
        }}
      >
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>
            Rent Mode {enabled === null ? "" : <span className={`badge ${enabled ? "badge--good" : "badge--neutral"}`}>{enabled ? "ON — enforcing" : "OFF — everything free"}</span>}
          </div>
          <p style={{ fontSize: 14.5, color: "var(--ink-300)", maxWidth: 480, margin: 0 }}>
            {enabled
              ? "Paid features (Document Vault, Purchase Orders, CSV export, and anything else you gate) now require a subscription or an admin override. Flip off any time to make everything free again instantly."
              : "Every feature is unlocked for every business right now, regardless of billing. Turn this on when you're ready to start charging — nothing else needs to change."}
          </p>
        </div>
        <button
          className={`btn ${enabled ? "btn-ghost" : "btn-primary"}`}
          onClick={toggle}
          disabled={enabled === null || saving}
          style={{ flexShrink: 0 }}
        >
          {saving ? "Saving…" : enabled ? "Turn off" : "Turn on"}
        </button>
      </div>
      {error && <p className="inline-error" style={{ marginTop: 8 }}>{error}</p>}
    </div>
  );
}

// --- Backup status ------------------------------------------------------

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return "";
  const mb = bytes / (1024 * 1024);
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`;
}

function BackupStatusCard() {
  const [backup, setBackup] = useState<BackupLog | null | undefined>(undefined); // undefined = loading
  const [error, setError] = useState(false);

  useEffect(() => {
    getLatestBackup().then(setBackup).catch(() => setError(true));
  }, []);

  if (backup === undefined && !error) return null; // don't flash a warning while still loading

  const hoursSinceBackup = backup ? (Date.now() - new Date(backup.started_at).getTime()) / 3_600_000 : Infinity;
  // Plain-language status, not jargon: a business owner shouldn't have
  // to know what "backup log status=failed" means to know if they're safe.
  const isHealthy = backup?.status === "success" && hoursSinceBackup < 48;
  const isStale = backup?.status === "success" && hoursSinceBackup >= 48;
  const isFailed = backup?.status === "failed";
  const isMissing = !backup || error;

  const tone = isHealthy ? "good" : isMissing || isFailed ? "critical" : "attention";
  const headline = isMissing
    ? "No backups yet"
    : isFailed
    ? "Last backup failed"
    : isStale
    ? "Backup is overdue"
    : "Backups are up to date";
  const detail = isMissing
    ? "Your data isn't being automatically backed up yet. Set up the scheduled backup job so a copy of your data is always safe."
    : isFailed
    ? `The last attempt ${timeAgo(backup!.started_at)} didn't finish. ${backup!.error || "Check the server logs for why."}`
    : `Last successful backup ${timeAgo(backup!.started_at)}${backup!.size_bytes ? ` — ${formatBytes(backup!.size_bytes)}` : ""}.`;

  return (
    <div
      className="card"
      style={{
        padding: 20, marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16,
      }}
    >
      <div>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4, display: "flex", alignItems: "center", gap: 8 }}>
          Data Backups
          <span className={`badge badge--${tone === "good" ? "good" : tone === "critical" ? "critical" : "attention"}`}>
            {headline}
          </span>
        </div>
        <p style={{ fontSize: 14.5, color: "var(--ink-300)", maxWidth: 520, margin: 0 }}>{detail}</p>
      </div>
    </div>
  );
}

// --- Features ---------------------------------------------------------

function FeaturesTab() {
  const [features, setFeatures] = useState<Feature[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Feature | null>(null);
  const [form, setForm] = useState({ key: "", name: "", description: "", category: "" });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    adminGetFeatures().then(setFeatures).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  function openCreate() {
    setEditing(null);
    setForm({ key: "", name: "", description: "", category: "" });
    setError(null);
    setShowModal(true);
  }
  function openEdit(f: Feature) {
    setEditing(f);
    setForm({ key: f.key, name: f.name, description: f.description, category: f.category });
    setError(null);
    setShowModal(true);
  }

  async function handleSave() {
    if (!form.key || !form.name) { setError("Key and name are required."); return; }
    setSubmitting(true); setError(null);
    try {
      if (editing) await adminUpdateFeature(editing.id, form);
      else await adminCreateFeature(form);
      setShowModal(false);
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save feature."));
    } finally { setSubmitting(false); }
  }

  async function toggleActive(f: Feature) {
    await adminUpdateFeature(f.id, { is_active: !f.is_active });
    refresh();
  }

  async function updateLockPriority(f: Feature, value: string) {
    const n = parseInt(value, 10);
    if (isNaN(n)) return;
    setFeatures((prev) => prev.map((x) => x.id === f.id ? { ...x, lock_priority: n } : x));
    await adminUpdateFeature(f.id, { lock_priority: n });
  }

  return (
    <div>
      <div className="card" style={{ padding: 20, marginBottom: 20, maxWidth: 640 }}>
        <h2 className="section-title">Lock priority</h2>
        <p style={{ fontSize: 15, color: "var(--ink-600)" }}>
          When a business's trial or subscription lapses, every gated feature normally locks at
          once. Lower numbers here lock <strong>first</strong> — set these so the features you're
          fine losing immediately are low, and anything you'd rather keep working a little longer
          (during a grace period, if one is configured below) is higher.
        </p>
      </div>
      <TrialGraceCard />
      <div className="toolbar" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-primary" onClick={openCreate}>New feature</button>
      </div>
      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : features.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No features defined yet" subtitle="Create the first one, or run `python manage.py seed_billing`." /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Key</th><th>Name</th><th>Category</th><th>Status</th><th>Lock priority</th><th></th></tr></thead>
            <tbody>
              {[...features].sort((a, b) => a.lock_priority - b.lock_priority).map((f) => (
                <tr key={f.id}>
                  <td><code>{f.key}</code></td>
                  <td>{f.name}</td>
                  <td>{f.category || "—"}</td>
                  <td><span className={`badge ${f.is_active ? "badge--good" : "badge--neutral"}`}>{f.is_active ? "active" : "inactive"}</span></td>
                  <td>
                    <input
                      className="input" type="number" style={{ width: 80 }}
                      value={f.lock_priority}
                      onChange={(e) => updateLockPriority(f, e.target.value)}
                    />
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn btn-ghost" onClick={() => openEdit(f)}>Edit</button>{" "}
                    <button className="btn btn-ghost" onClick={() => toggleActive(f)}>{f.is_active ? "Deactivate" : "Activate"}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <Modal title={editing ? "Edit feature" : "New feature"} onClose={() => setShowModal(false)}>
          <Field label="Key" required>
            <input className="input" value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} disabled={!!editing} placeholder="e.g. ai_addon" />
          </Field>
          <Field label="Name" required><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Category"><input className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} /></Field>
          <Field label="Description"><textarea className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleSave} disabled={submitting}>{submitting ? "Saving…" : "Save feature"}</button>
        </Modal>
      )}
    </div>
  );
}

function TrialGraceCard() {
  const [days, setDays] = useState("0");
  const [count, setCount] = useState("0");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getPlatformSettings().then((s) => {
      setDays(String(s.trial_grace_days ?? 0));
      setCount(String(s.trial_grace_feature_count ?? 0));
    }).catch(() => {});
  }, []);

  async function handleSave() {
    setSubmitting(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updatePlatformSettings({
        trial_grace_days: parseInt(days, 10) || 0,
        trial_grace_feature_count: parseInt(count, 10) || 0,
      });
      setDays(String(updated.trial_grace_days));
      setCount(String(updated.trial_grace_feature_count));
      setSaved(true);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save this."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ padding: 20, marginBottom: 20, maxWidth: 640 }}>
      <h2 className="section-title">Grace period after expiry</h2>
      <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 14 }}>
        Optional softer landing: for this many days after a trial or subscription lapses, keep a
        few features working instead of locking everything at once — specifically, whichever
        features above have the lowest lock priority numbers. Leave both at 0 to lock everything
        immediately, as before.
      </p>
      <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
        <Field label="Grace period (days)">
          <input className="input" type="number" min="0" style={{ width: 120 }} value={days} onChange={(e) => setDays(e.target.value)} />
        </Field>
        <Field label="Features to keep working" hint="Lowest lock-priority features, counted from the table above">
          <input className="input" type="number" min="0" style={{ width: 120 }} value={count} onChange={(e) => setCount(e.target.value)} />
        </Field>
      </div>
      {error && <p className="inline-error">{error}</p>}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={submitting}>{submitting ? "Saving…" : "Save"}</button>
        {saved && !error && <span style={{ fontSize: 15, color: "var(--green-600)" }}>Saved.</span>}
      </div>
    </div>
  );
}

// --- Plans --------------------------------------------------------------

function PlansTab() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Plan | null>(null);
  const [form, setForm] = useState({
    name: "", slug: "", description: "", price_amount: "", currency: "NGN",
    billing_interval: "monthly", sort_order: "0", feature_ids: [] as string[],
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.allSettled([adminGetPlans(), adminGetFeatures()]).then(([p, f]) => {
      if (p.status === "fulfilled") setPlans(p.value); else console.error("Failed to load plans:", p.reason);
      if (f.status === "fulfilled") setFeatures(f.value); else console.error("Failed to load features:", f.reason);
    }).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  function openCreate() {
    setEditing(null);
    setForm({ name: "", slug: "", description: "", price_amount: "", currency: "NGN", billing_interval: "monthly", sort_order: "0", feature_ids: [] });
    setError(null);
    setShowModal(true);
  }
  function openEdit(p: Plan) {
    setEditing(p);
    setForm({
      name: p.name, slug: p.slug, description: p.description, price_amount: p.price_amount,
      currency: p.currency, billing_interval: p.billing_interval, sort_order: String(p.sort_order),
      feature_ids: p.features.map((f) => f.id),
    });
    setError(null);
    setShowModal(true);
  }

  function toggleFeature(id: string) {
    setForm((f) => ({
      ...f,
      feature_ids: f.feature_ids.includes(id) ? f.feature_ids.filter((x) => x !== id) : [...f.feature_ids, id],
    }));
  }

  async function handleSave() {
    if (!form.name || !form.slug || !form.price_amount) { setError("Name, slug, and price are required."); return; }
    setSubmitting(true); setError(null);
    try {
      const payload = {
        name: form.name, slug: form.slug, description: form.description,
        price_amount: Number(form.price_amount), currency: form.currency,
        billing_interval: form.billing_interval, sort_order: Number(form.sort_order),
        feature_ids: form.feature_ids,
      };
      if (editing) await adminUpdatePlan(editing.id, payload);
      else await adminCreatePlan(payload);
      setShowModal(false);
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save plan."));
    } finally { setSubmitting(false); }
  }

  async function toggleActive(p: Plan) {
    await adminUpdatePlan(p.id, { is_active: !p.is_active });
    refresh();
  }

  return (
    <div>
      <div className="toolbar" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-primary" onClick={openCreate}>New plan</button>
      </div>
      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : plans.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No plans yet" subtitle="Create one, or run `python manage.py seed_billing`." /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Name</th><th>Price</th><th>Features</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {plans.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td className="num">{formatMoney(p.price_amount, p.currency)}/{p.billing_interval === "monthly" ? "mo" : p.billing_interval === "yearly" ? "yr" : p.billing_interval === "daily" ? "day" : "wk"}</td>
                  <td>{p.features.length}</td>
                  <td><span className={`badge ${p.is_active ? "badge--good" : "badge--neutral"}`}>{p.is_active ? "active" : "inactive"}</span></td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn btn-ghost" onClick={() => openEdit(p)}>Edit</button>{" "}
                    <button className="btn btn-ghost" onClick={() => toggleActive(p)}>{p.is_active ? "Deactivate" : "Activate"}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <Modal title={editing ? "Edit plan" : "New plan"} onClose={() => setShowModal(false)} width={560}>
          <div className="form-grid">
            <div className="field--half"><Field label="Name" required><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field></div>
            <div className="field--half"><Field label="Slug" required><input className="input" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} disabled={!!editing} /></Field></div>
          </div>
          <div className="form-grid">
            <div className="field--half"><Field label="Price" required><input className="input" type="number" value={form.price_amount} onChange={(e) => setForm({ ...form, price_amount: e.target.value })} /></Field></div>
            <div className="field--half"><Field label="Currency"><input className="input" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} /></Field></div>
          </div>
          <div className="form-grid">
            <div className="field--half">
              <Field label="Interval">
                <select className="input" value={form.billing_interval} onChange={(e) => setForm({ ...form, billing_interval: e.target.value })}>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </Field>
            </div>
            <div className="field--half"><Field label="Sort order"><input className="input" type="number" value={form.sort_order} onChange={(e) => setForm({ ...form, sort_order: e.target.value })} /></Field></div>
          </div>
          <Field label="Description"><textarea className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
          <Field label="Included features">
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {features.map((f) => (
                <label key={f.id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 15, border: "1px solid var(--line)", borderRadius: 6, padding: "5px 10px" }}>
                  <input type="checkbox" checked={form.feature_ids.includes(f.id)} onChange={() => toggleFeature(f.id)} />
                  {f.name}
                </label>
              ))}
            </div>
          </Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleSave} disabled={submitting}>{submitting ? "Saving…" : "Save plan"}</button>
        </Modal>
      )}
    </div>
  );
}

// --- Subscriptions (read-only overview) ------------------------------

function UsageTab() {
  const [data, setData] = useState<PlatformUsageSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminGetUsageAnalytics().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-row">Loading…</div>;
  if (!data) return <EmptyState title="Couldn't load usage data" />;

  return (
    <div>
      <div className="stat-grid" style={{ marginBottom: 20 }}>
        <div className="stat-card">
          <div style={{ fontSize: 14, color: "var(--ink-300)" }}>Businesses</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{data.totals.businesses}</div>
        </div>
        <div className="stat-card">
          <div style={{ fontSize: 14, color: "var(--ink-300)" }}>Total users</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{data.totals.users}</div>
        </div>
        <div className="stat-card">
          <div style={{ fontSize: 14, color: "var(--ink-300)" }}>Active last 7 days</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{data.activity.active_users_last_7_days}</div>
        </div>
        <div className="stat-card">
          <div style={{ fontSize: 14, color: "var(--ink-300)" }}>Active last 30 days</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{data.activity.active_users_last_30_days}</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div className="card" style={{ padding: 24 }}>
          <h2 className="section-title">Business activity (last 30 days)</h2>
          <p style={{ fontSize: 15.5, marginBottom: 4 }}>
            <strong>{data.activity.businesses_that_made_a_sale_last_30_days}</strong> businesses made at least one sale
          </p>
          <p style={{ fontSize: 15.5, color: data.activity.businesses_with_no_sale_last_30_days > 0 ? "var(--gold-600)" : undefined }}>
            <strong>{data.activity.businesses_with_no_sale_last_30_days}</strong> businesses had no sales — may be dormant or just onboarding
          </p>
        </div>

        <div className="card" style={{ padding: 24 }}>
          <h2 className="section-title">Subscriptions by status</h2>
          {Object.entries(data.subscriptions.by_status).map(([status, count]) => (
            <p key={status} style={{ fontSize: 15.5, display: "flex", justifyContent: "space-between" }}>
              <span style={{ textTransform: "capitalize" }}>{status.replace("_", " ")}</span>
              <strong>{count}</strong>
            </p>
          ))}
        </div>
      </div>

      {data.subscriptions.by_plan.length > 0 && (
        <div className="card" style={{ padding: 24, marginTop: 20 }}>
          <h2 className="section-title">Active subscribers by plan</h2>
          <table className="data-table">
            <thead><tr><th>Plan</th><th>Billing interval</th><th className="num">Subscribers</th></tr></thead>
            <tbody>
              {data.subscriptions.by_plan.map((p, i) => (
                <tr key={i}>
                  <td>{p.plan_name}</td>
                  <td style={{ textTransform: "capitalize" }}>{p.billing_interval}</td>
                  <td className="num">{p.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SubscriptionsTab() {
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [businesses, setBusinesses] = useState<{ id: string; name: string; is_active: boolean }[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showActivate, setShowActivate] = useState(false);
  const [activateBusiness, setActivateBusiness] = useState("");
  const [activatePlan, setActivatePlan] = useState("");
  const [activateNote, setActivateNote] = useState("");
  const [activateError, setActivateError] = useState<string | null>(null);
  const [activating, setActivating] = useState(false);
  const [extendingId, setExtendingId] = useState<string | null>(null);
  const [freezingId, setFreezingId] = useState<string | null>(null);
  const [killingId, setKillingId] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);
  const [usageFor, setUsageFor] = useState<TenantUsage | null>(null);
  const [loadingUsageId, setLoadingUsageId] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    Promise.allSettled([adminGetSubscriptions(), adminGetBusinesses(), adminGetPlans()]).then(([s, b, p]) => {
      if (s.status === "fulfilled") setSubs(s.value);
      if (b.status === "fulfilled") setBusinesses(b.value);
      if (p.status === "fulfilled") setPlans(p.value);
    }).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  function businessFor(businessId: string) {
    return businesses.find((b) => b.id === businessId);
  }

  async function handleActivate() {
    if (!activateBusiness || !activatePlan) { setActivateError("Pick a business and a plan."); return; }
    setActivating(true); setActivateError(null);
    try {
      await adminActivateSubscription({ business: activateBusiness, plan: activatePlan, note: activateNote || undefined });
      setShowActivate(false);
      setActivateBusiness(""); setActivatePlan(""); setActivateNote("");
      refresh();
    } catch (err: any) {
      setActivateError(extractErrorMessage(err, "Couldn't activate that subscription."));
    } finally {
      setActivating(false);
    }
  }

  async function handleExtendTrial(businessId: string) {
    const raw = window.prompt("Extend by how many days?", "7");
    if (!raw) return;
    const days = Number(raw);
    if (!Number.isFinite(days) || days < 1) { setRowError("Enter a valid number of days."); return; }
    setExtendingId(businessId); setRowError(null);
    try {
      await adminExtendTrial(businessId, days);
      refresh();
    } catch (err: any) {
      setRowError(extractErrorMessage(err, "Couldn't extend the trial."));
    } finally {
      setExtendingId(null);
    }
  }

  async function handleToggleFreeze(business: { id: string; name: string; is_active: boolean }) {
    const freezing = business.is_active;
    if (!window.confirm(
      freezing
        ? `Freeze "${business.name}"? Every user at this business loses access immediately.`
        : `Unfreeze "${business.name}"? They'll be able to log in again immediately.`,
    )) return;
    setFreezingId(business.id); setRowError(null);
    try {
      await adminFreezeAccount(business.id, !freezing);
      refresh();
    } catch (err: any) {
      setRowError(extractErrorMessage(err, "Couldn't update that account's status."));
    } finally {
      setFreezingId(null);
    }
  }

  async function handleKillSwitch(business: { id: string; name: string }) {
    if (!window.confirm(
      `Emergency kill switch for "${business.name}" — this immediately signs out every active session for every user at this business. Use this for a reported compromise. Continue?`,
    )) return;
    setKillingId(business.id); setRowError(null);
    try {
      const res = await adminKillSwitch(business.id);
      window.alert(`${res.revoked} session(s) revoked.`);
    } catch (err: any) {
      setRowError(extractErrorMessage(err, "Couldn't run the kill switch."));
    } finally {
      setKillingId(null);
    }
  }

  async function handleViewUsage(businessId: string) {
    setLoadingUsageId(businessId);
    setRowError(null);
    try {
      const usage = await adminGetTenantUsage(businessId);
      setUsageFor(usage);
    } catch (err: any) {
      setRowError(extractErrorMessage(err, "Couldn't load usage for that business."));
    } finally {
      setLoadingUsageId(null);
    }
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <button className="btn btn-primary" onClick={() => setShowActivate(true)}>Activate a subscription</button>
      </div>
    <div className="card">
      {rowError && <p className="inline-error" style={{ padding: "12px 20px 0" }}>{rowError}</p>}
      {loading ? <div className="loading-row">Loading…</div> : subs.length === 0 ? (
        <div style={{ padding: 24 }}><EmptyState title="No subscriptions yet" /></div>
      ) : (
        <table className="data-table">
          <thead><tr><th>Business</th><th>Plan</th><th>Status</th><th>Renews / ends</th><th></th></tr></thead>
          <tbody>
            {subs.map((s) => {
              const business = businessFor(s.business);
              return (
              <tr key={s.id}>
                <td>{s.business_name}</td>
                <td>{s.plan?.name || "—"}</td>
                <td>
                  <span className={`badge badge--${s.status === "active" ? "good" : s.status === "past_due" ? "attention" : "neutral"}`}>
                    {s.status.replace("_", " ")}
                  </span>
                  {s.cancel_at_period_end && <span className="badge badge--attention" style={{ marginLeft: 6 }}>ending</span>}
                  {business && !business.is_active && <span className="badge badge--attention" style={{ marginLeft: 6 }}>frozen</span>}
                </td>
                <td>{s.current_period_end ? formatDate(s.current_period_end) : "—"}</td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  <button className="btn btn-ghost" disabled={extendingId === s.business} onClick={() => handleExtendTrial(s.business)}>
                    {extendingId === s.business ? "…" : "Extend"}
                  </button>{" "}
                  {business && (
                    <button className="btn btn-ghost" disabled={freezingId === business.id} onClick={() => handleToggleFreeze(business)}>
                      {freezingId === business.id ? "…" : business.is_active ? "Freeze" : "Unfreeze"}
                    </button>
                  )}{" "}
                  {business && (
                    <button className="btn btn-ghost" style={{ color: "var(--red-600)" }} disabled={killingId === business.id} onClick={() => handleKillSwitch(business)}>
                      {killingId === business.id ? "…" : "🛑 Kill switch"}
                    </button>
                  )}{" "}
                  {business && (
                    <button className="btn btn-ghost" disabled={loadingUsageId === business.id} onClick={() => handleViewUsage(business.id)}>
                      {loadingUsageId === business.id ? "…" : "Usage"}
                    </button>
                  )}
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>

    {showActivate && (
      <Modal title="Activate a subscription" onClose={() => setShowActivate(false)}>
        <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
          Directly puts a business on a plan — for an offline payment, a comp, or fixing something a
          webhook missed. Bypasses Paystack entirely.
        </p>
        <Field label="Business">
          <select className="input" value={activateBusiness} onChange={(e) => setActivateBusiness(e.target.value)}>
            <option value="">Select…</option>
            {businesses.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </Field>
        <Field label="Plan">
          <select className="input" value={activatePlan} onChange={(e) => setActivatePlan(e.target.value)}>
            <option value="">Select…</option>
            {plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} — {formatMoney(p.price_amount, p.currency)}/{p.billing_interval}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Note" hint="Optional — e.g. 'Bank transfer received 12 Aug'">
          <input className="input" value={activateNote} onChange={(e) => setActivateNote(e.target.value)} />
        </Field>
        {activateError && <p className="inline-error">{activateError}</p>}
        <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleActivate} disabled={activating}>
          {activating ? "Activating…" : "Activate"}
        </button>
      </Modal>
    )}
    {usageFor && (
      <Modal title={`Usage — ${usageFor.business_name}`} onClose={() => setUsageFor(null)}>
        <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
          Approximate — media is measured directly from stored files; row counts are a proxy for
          data volume in a shared database, not exact disk usage.
        </p>
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 15, color: "var(--ink-600)" }}>Media storage (logos, photos, receipts, documents)</div>
          <div style={{ fontSize: 22, fontFamily: "var(--font-display)" }}>
            {(usageFor.media_bytes / (1024 * 1024)).toFixed(2)} MB
          </div>
        </div>
        <table className="data-table">
          <thead><tr><th>Table</th><th className="num">Rows</th></tr></thead>
          <tbody>
            {Object.entries(usageFor.row_counts).map(([key, count]) => (
              <tr key={key}>
                <td style={{ textTransform: "capitalize" }}>{key.replace(/_/g, " ")}</td>
                <td className="num">{count.toLocaleString()}</td>
              </tr>
            ))}
            <tr>
              <td><strong>Total</strong></td>
              <td className="num"><strong>{usageFor.total_rows.toLocaleString()}</strong></td>
            </tr>
          </tbody>
        </table>
      </Modal>
    )}
    </div>
  );
}

// --- Overrides (manual per-business grants) --------------------------

function OverridesTab() {
  const [overrides, setOverrides] = useState<FeatureOverride[]>([]);
  const [businesses, setBusinesses] = useState<{ id: string; name: string }[]>([]);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ business: "", feature: "", is_enabled: true, note: "", expires_at: "" });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.allSettled([adminGetOverrides(), adminGetBusinesses(), adminGetFeatures()]).then(([o, b, f]) => {
      if (o.status === "fulfilled") setOverrides(o.value); else console.error("Failed to load overrides:", o.reason);
      if (b.status === "fulfilled") setBusinesses(b.value); else console.error("Failed to load businesses:", b.reason);
      if (f.status === "fulfilled") setFeatures(f.value); else console.error("Failed to load features:", f.reason);
    }).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  function openCreate() {
    setForm({ business: businesses[0]?.id || "", feature: features[0]?.id || "", is_enabled: true, note: "", expires_at: "" });
    setError(null);
    setShowModal(true);
  }

  async function handleSave() {
    if (!form.business || !form.feature) { setError("Pick a business and a feature."); return; }
    setSubmitting(true); setError(null);
    try {
      await adminCreateOverride({
        business: form.business, feature: form.feature, is_enabled: form.is_enabled,
        note: form.note, expires_at: form.expires_at || null,
      });
      setShowModal(false);
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save override."));
    } finally { setSubmitting(false); }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Remove this override? The business will fall back to whatever their plan includes.")) return;
    await adminDeleteOverride(id);
    refresh();
  }

  return (
    <div>
      <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginBottom: 12 }}>
        Grant or revoke a specific feature for a specific business — for comps, trials, or manual enforcement,
        regardless of what their subscription plan includes.
      </p>
      <div className="toolbar" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-primary" onClick={openCreate}>New override</button>
      </div>
      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : overrides.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No manual overrides" subtitle="Everyone's access is driven purely by their subscription plan." /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Business</th><th>Feature</th><th>Status</th><th>Note</th><th>Expires</th><th></th></tr></thead>
            <tbody>
              {overrides.map((o) => (
                <tr key={o.id}>
                  <td>{o.business_name}</td>
                  <td><code>{o.feature_key}</code></td>
                  <td><span className={`badge ${o.is_enabled ? "badge--good" : "badge--critical"}`}>{o.is_enabled ? "granted" : "revoked"}</span></td>
                  <td>{o.note || "—"}</td>
                  <td>{o.expires_at ? formatDate(o.expires_at) : "Never"}</td>
                  <td style={{ textAlign: "right" }}><button className="btn btn-ghost" onClick={() => handleDelete(o.id)}>Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <Modal title="New override" onClose={() => setShowModal(false)}>
          <Field label="Business" required>
            <select className="input" value={form.business} onChange={(e) => setForm({ ...form, business: e.target.value })}>
              {businesses.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </Field>
          <Field label="Feature" required>
            <select className="input" value={form.feature} onChange={(e) => setForm({ ...form, feature: e.target.value })}>
              {features.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </Field>
          <Field label="Action">
            <select className="input" value={form.is_enabled ? "grant" : "revoke"} onChange={(e) => setForm({ ...form, is_enabled: e.target.value === "grant" })}>
              <option value="grant">Grant (turn on)</option>
              <option value="revoke">Revoke (force off)</option>
            </select>
          </Field>
          <Field label="Note"><input className="input" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} placeholder="e.g. trial until launch" /></Field>
          <Field label="Expires (optional)"><input className="input" type="date" value={form.expires_at} onChange={(e) => setForm({ ...form, expires_at: e.target.value })} /></Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleSave} disabled={submitting}>{submitting ? "Saving…" : "Save override"}</button>
        </Modal>
      )}
    </div>
  );
}

// --- Broadcast (platform-wide notification) ---------------------------

function BroadcastTab() {
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [level, setLevel] = useState<"critical" | "important" | "info">("info");
  const [target, setTarget] = useState<"all" | "active_subscribers" | "specific">("all");
  const [businesses, setBusinesses] = useState<{ id: string; name: string }[]>([]);
  const [selectedBusinesses, setSelectedBusinesses] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    adminGetBusinesses().then(setBusinesses).catch(() => {});
  }, []);

  async function handleSend() {
    if (!title.trim() || !message.trim()) { setError("Enter a title and a message."); return; }
    if (target === "specific" && selectedBusinesses.length === 0) { setError("Select at least one business."); return; }
    setSubmitting(true); setError(null); setResult(null);
    try {
      const res = await adminBroadcastNotification({
        title: title.trim(), message: message.trim(), level, target,
        business_ids: target === "specific" ? selectedBusinesses : undefined,
      });
      setResult(`Sent to ${res.sent_to_businesses} business${res.sent_to_businesses === 1 ? "" : "es"}.`);
      setTitle(""); setMessage("");
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't send that."));
    } finally {
      setSubmitting(false);
    }
  }

  function toggleBusiness(id: string) {
    setSelectedBusinesses((prev) => prev.includes(id) ? prev.filter((b) => b !== id) : [...prev, id]);
  }

  return (
    <div className="card" style={{ padding: 24, maxWidth: 560 }}>
      <h2 className="section-title">Broadcast a notification</h2>
      <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginBottom: 16 }}>
        Posts into every recipient business's own notification feed — the same channel their own
        automated alerts use, including their configured WhatsApp/email delivery.
      </p>
      <Field label="Send to">
        <select className="input" value={target} onChange={(e) => setTarget(e.target.value as any)}>
          <option value="all">All businesses</option>
          <option value="active_subscribers">Active subscribers only</option>
          <option value="specific">Specific businesses</option>
        </select>
      </Field>
      {target === "specific" && (
        <div style={{ maxHeight: 160, overflowY: "auto", border: "1px solid var(--line)", borderRadius: 8, padding: 10, marginBottom: 16 }}>
          {businesses.map((b) => (
            <label key={b.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 15, padding: "4px 0", cursor: "pointer" }}>
              <input type="checkbox" checked={selectedBusinesses.includes(b.id)} onChange={() => toggleBusiness(b.id)} />
              {b.name}
            </label>
          ))}
        </div>
      )}
      <Field label="Priority">
        <select className="input" value={level} onChange={(e) => setLevel(e.target.value as any)}>
          <option value="info">Information</option>
          <option value="important">Important</option>
          <option value="critical">Critical</option>
        </select>
      </Field>
      <Field label="Title">
        <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
      </Field>
      <Field label="Message">
        <textarea className="input" rows={4} value={message} onChange={(e) => setMessage(e.target.value)} />
      </Field>
      {error && <p className="inline-error">{error}</p>}
      {result && <p style={{ fontSize: 15, color: "var(--green-600)", marginBottom: 12 }}>{result}</p>}
      <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleSend} disabled={submitting}>
        {submitting ? "Sending…" : "Send"}
      </button>
    </div>
  );
}

function PlatformIntegrationsCard() {
  const [settings, setSettings] = useState<PlatformSettings | null>(null);
  const [whatsappToken, setWhatsappToken] = useState("");
  const [whatsappPhoneId, setWhatsappPhoneId] = useState("");
  const [emailUser, setEmailUser] = useState("");
  const [emailPassword, setEmailPassword] = useState("");
  const [platformPaystackPublic, setPlatformPaystackPublic] = useState("");
  const [platformPaystackSecret, setPlatformPaystackSecret] = useState("");
  const [googleClientId, setGoogleClientId] = useState("");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getPlatformSettings().then((s) => {
      setSettings(s);
      setWhatsappPhoneId(s.whatsapp_phone_number_id || "");
      setEmailUser(s.email_host_user || "");
      setPlatformPaystackPublic(s.platform_paystack_public_key || "");
      setGoogleClientId(s.google_oauth_client_id || "");
    });
  }, []);

  async function handleSave() {
    setSubmitting(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updatePlatformSettings({
        whatsapp_phone_number_id: whatsappPhoneId,
        email_host_user: emailUser,
        platform_paystack_public_key: platformPaystackPublic,
        google_oauth_client_id: googleClientId,
        ...(whatsappToken ? { whatsapp_access_token: whatsappToken } : {}),
        ...(emailPassword ? { email_host_password: emailPassword } : {}),
        ...(platformPaystackSecret ? { platform_paystack_secret_key: platformPaystackSecret } : {}),
      });
      setSettings(updated);
      setWhatsappToken(""); setEmailPassword(""); setPlatformPaystackSecret("");
      setSaved(true);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save platform settings."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ padding: 24, maxWidth: 520 }}>
      <h2 className="section-title">Platform Integrations (staff only)</h2>
      <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 18 }}>
        These credentials belong to this Truvanta deployment, not to any one business — the WhatsApp number
        and Gmail account notifications are sent from, and the platform's own Paystack keys for billing
        the AI add-on. Set once here instead of editing <code>.env</code> and redeploying.
      </p>

      <p style={{ fontSize: 14.5, fontWeight: 600, marginBottom: 8 }}>
        WhatsApp {settings?.whatsapp_configured && <span className="badge badge--good">configured</span>}
      </p>
      <Field label="Access token" hint="From your Meta WhatsApp Business app">
        <input className="input" type="password" value={whatsappToken} onChange={(e) => setWhatsappToken(e.target.value)} placeholder={settings?.whatsapp_configured ? "•••• leave blank to keep" : ""} />
      </Field>
      <Field label="Phone number ID">
        <input className="input" value={whatsappPhoneId} onChange={(e) => setWhatsappPhoneId(e.target.value)} />
      </Field>

      <p style={{ fontSize: 14.5, fontWeight: 600, marginBottom: 8, marginTop: 8 }}>
        Gmail (for sending notification emails) {settings?.email_configured && <span className="badge badge--good">configured</span>}
      </p>
      <Field label="Gmail address">
        <input className="input" type="email" value={emailUser} onChange={(e) => setEmailUser(e.target.value)} />
      </Field>
      <Field label="App password" hint="Generate at myaccount.google.com/apppasswords — not your normal password">
        <input className="input" type="password" value={emailPassword} onChange={(e) => setEmailPassword(e.target.value)} placeholder={settings?.email_configured ? "•••• leave blank to keep" : ""} />
      </Field>

      <p style={{ fontSize: 14.5, fontWeight: 600, marginBottom: 8, marginTop: 8 }}>
        Platform Paystack (for AI subscription billing) {settings?.paystack_configured && <span className="badge badge--good">configured</span>}
      </p>
      <Field label="Public key">
        <input className="input" value={platformPaystackPublic} onChange={(e) => setPlatformPaystackPublic(e.target.value)} placeholder="pk_live_…" />
      </Field>
      <Field label="Secret key">
        <input className="input" type="password" value={platformPaystackSecret} onChange={(e) => setPlatformPaystackSecret(e.target.value)} placeholder={settings?.paystack_configured ? "•••• leave blank to keep" : "sk_live_…"} />
      </Field>

      <p style={{ fontSize: 14.5, fontWeight: 600, marginBottom: 8, marginTop: 8 }}>
        Google sign-in {settings?.google_oauth_client_id && <span className="badge badge--good">configured</span>}
      </p>
      <Field label="OAuth Client ID" hint="From Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client ID (Web application). Not a secret — leave blank to hide the Google button on the login screen.">
        <input className="input" value={googleClientId} onChange={(e) => setGoogleClientId(e.target.value)} placeholder="xxxxxxxxxx.apps.googleusercontent.com" />
      </Field>

      {error && <p className="inline-error">{error}</p>}
      {saved && !error && <p style={{ color: "var(--green-600)", fontSize: 15, marginBottom: 14 }}>Saved.</p>}
      <button className="btn btn-primary" onClick={handleSave} disabled={submitting}>
        {submitting ? "Saving…" : "Save platform settings"}
      </button>
    </div>
  );
}

// --- Support Access: log into a business the owner has explicitly granted access to ---

function SupportAccessTab() {
  const { setActiveBusiness, loadMe } = useAuth();
  const navigate = useNavigate();
  const [businesses, setBusinesses] = useState<{ id: string; name: string; support_access_expires_at: string | null }[]>([]);
  const [loading, setLoading] = useState(true);
  const [loggingInId, setLoggingInId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    adminGetBusinesses().then(setBusinesses).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  const granted = businesses.filter(
    (b) => b.support_access_expires_at && new Date(b.support_access_expires_at).getTime() > Date.now(),
  );

  async function handleLogin(businessId: string) {
    setLoggingInId(businessId);
    setError(null);
    try {
      const res = await adminSupportLogin(businessId);
      setActiveBusiness(res.business_id);
      // The support membership was just created server-side — refetch
      // /auth/me/ so it actually shows up in this session's membership
      // list before we navigate into business-scoped pages.
      await loadMe();
      navigate("/dashboard");
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't log in — the business may not have an open access window."));
    } finally {
      setLoggingInId(null);
    }
  }

  return (
    <div>
      <div className="card" style={{ padding: 24 }}>
        <h2 className="section-title">Businesses with an open support window</h2>
        <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 18 }}>
          Only businesses whose owner/admin has explicitly granted a time-limited window show up
          here. Logging in creates a real, labelled membership on their Staff page, and is logged
          to their Activity Log — never invisible to them.
        </p>
        {error && <p className="inline-error">{error}</p>}
        {loading ? (
          <div className="loading-row">Loading…</div>
        ) : granted.length === 0 ? (
          <EmptyState title="No businesses currently have support access open" />
        ) : (
          <table className="data-table">
            <thead><tr><th>Business</th><th>Access expires</th><th></th></tr></thead>
            <tbody>
              {granted.map((b) => (
                <tr key={b.id}>
                  <td>{b.name}</td>
                  <td>{formatDate(b.support_access_expires_at!)}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn btn-primary" disabled={loggingInId === b.id} onClick={() => handleLogin(b.id)}>
                      {loggingInId === b.id ? "Logging in…" : "Log in as this business"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// --- Global Audit: the security trail across every business, not just one ---

const ACTION_LABELS: Record<string, string> = {
  create: "Create", update: "Update", price_change: "Price change", discount: "Discount",
  refund: "Refund", return: "Return", cancellation: "Cancellation", stock_adjustment: "Stock adjustment",
  expense_change: "Expense change", credit_change: "Credit change", permission_change: "Permission change",
  login: "Login", login_failed: "Failed login", receipt_reprint: "Receipt reprint", shift_event: "Shift event",
  other: "Platform admin action",
};

function GlobalAuditTab() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("");

  function refresh() {
    setLoading(true);
    adminGetAuditLogs(actionFilter ? { action: actionFilter } : undefined)
      .then(setLogs)
      .finally(() => setLoading(false));
  }
  useEffect(refresh, [actionFilter]);

  return (
    <div>
      <div className="card" style={{ padding: 0 }}>
        <div style={{ padding: "18px 20px 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 className="section-title">Global audit trail</h2>
            <p style={{ fontSize: 15, color: "var(--ink-600)" }}>
              Every sensitive action across every business — for investigating a pattern or a report
              that spans tenants. Each business still only ever sees its own trail on their own
              Activity Log page; this view is staff-only.
            </p>
          </div>
          <select className="input" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)} style={{ maxWidth: 200 }}>
            <option value="">All actions</option>
            {Object.entries(ACTION_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        {loading ? (
          <div className="loading-row">Loading…</div>
        ) : logs.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No matching activity" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Business</th><th>Action</th><th>Who</th><th>Reason</th><th>When</th></tr></thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td>{l.business_name || "—"}</td>
                  <td>{ACTION_LABELS[l.action] || l.action}</td>
                  <td>{l.actor_name || "System"}</td>
                  <td style={{ maxWidth: 340, whiteSpace: "normal" }}>{l.reason || "—"}</td>
                  <td>{formatDate(l.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// --- Webhooks: Paystack event log with manual replay for failures ---

function WebhooksTab() {
  const [events, setEvents] = useState<BillingEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [onlyFailed, setOnlyFailed] = useState(true);
  const [replayingId, setReplayingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    adminGetWebhookEvents(onlyFailed ? { processed_ok: "false" } : undefined)
      .then(setEvents)
      .finally(() => setLoading(false));
  }
  useEffect(refresh, [onlyFailed]);

  async function handleReplay(id: string) {
    setReplayingId(id);
    setError(null);
    try {
      await adminReplayWebhookEvent(id);
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't replay that webhook."));
    } finally {
      setReplayingId(null);
    }
  }

  return (
    <div>
      <div className="card" style={{ padding: 0 }}>
        <div style={{ padding: "18px 20px 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 className="section-title">Paystack webhook log</h2>
            <p style={{ fontSize: 15, color: "var(--ink-600)" }}>
              Every webhook Paystack has sent, whether it processed cleanly or not. Replaying
              re-runs the exact original payload — useful once a bug is fixed or a business that
              didn't exist yet at the time now does.
            </p>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 15, whiteSpace: "nowrap" }}>
            <input type="checkbox" checked={onlyFailed} onChange={(e) => setOnlyFailed(e.target.checked)} />
            Failed only
          </label>
        </div>
        {error && <p className="inline-error" style={{ padding: "0 20px" }}>{error}</p>}
        {loading ? (
          <div className="loading-row">Loading…</div>
        ) : events.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title={onlyFailed ? "No failed webhooks" : "No webhooks yet"} /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Business</th><th>Event</th><th>Reference</th><th>Status</th><th>When</th><th></th></tr></thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id}>
                  <td>{e.business_name || "—"}</td>
                  <td>{e.event_type}</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: 14 }}>{e.paystack_reference || "—"}</td>
                  <td>
                    {e.processed_ok ? (
                      <span className="badge badge--good">OK</span>
                    ) : (
                      <span className="badge badge--attention" title={e.error}>Failed</span>
                    )}
                    {!e.processed_ok && e.error && (
                      <div style={{ fontSize: 13.5, color: "var(--red-600)", marginTop: 4, maxWidth: 260 }}>{e.error}</div>
                    )}
                  </td>
                  <td>{formatDate(e.created_at)}</td>
                  <td style={{ textAlign: "right" }}>
                    {!e.processed_ok && (
                      <button className="btn btn-primary" disabled={replayingId === e.id} onClick={() => handleReplay(e.id)}>
                        {replayingId === e.id ? "Replaying…" : "⚡ Replay"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// --- Data Purge: two-step, name-confirmed, delayed permanent deletion ---

type PurgeBusiness = { id: string; name: string; is_active: boolean; pending_deletion_at: string | null };

function DataPurgeTab() {
  const [businesses, setBusinesses] = useState<PurgeBusiness[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scheduleTarget, setScheduleTarget] = useState<PurgeBusiness | null>(null);
  const [purgeTarget, setPurgeTarget] = useState<PurgeBusiness | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [graceDays, setGraceDays] = useState(7);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    adminGetBusinesses().then((data: any) => setBusinesses(data)).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  const scheduled = businesses.filter((b) => b.pending_deletion_at);
  const eligibleNow = (b: PurgeBusiness) => b.pending_deletion_at && new Date(b.pending_deletion_at).getTime() <= Date.now();

  async function handleSchedule() {
    if (!scheduleTarget) return;
    setSubmitting(true);
    setError(null);
    try {
      await adminScheduleDeletion(scheduleTarget.id, confirmText, graceDays);
      setScheduleTarget(null);
      setConfirmText("");
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't schedule deletion — check the name matches exactly."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel(business: PurgeBusiness) {
    if (!window.confirm(`Cancel the scheduled deletion for "${business.name}" and unfreeze the account?`)) return;
    setError(null);
    try {
      await adminCancelDeletion(business.id);
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't cancel."));
    }
  }

  async function handleExecute() {
    if (!purgeTarget) return;
    setSubmitting(true);
    setError(null);
    try {
      await adminExecutePurge(purgeTarget.id, confirmText);
      setPurgeTarget(null);
      setConfirmText("");
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't execute the purge — check the name matches exactly."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="card card--vault" style={{ padding: 20, marginBottom: 20 }}>
        <h2 className="section-title">Permanent data deletion</h2>
        <p style={{ fontSize: 15, color: "var(--ink-600)" }}>
          For account-closure / GDPR-style "forget me" requests. Deliberately two steps, both
          requiring you to type the business's exact name: scheduling freezes the account and
          starts a grace window (you can cancel any time before it passes); executing — only
          possible once that window has genuinely passed — is permanent and cannot be undone.
        </p>
      </div>

      {error && <p className="inline-error">{error}</p>}

      <div className="card" style={{ padding: 0, marginBottom: 20 }}>
        <h2 className="section-title" style={{ padding: "18px 20px 0" }}>Scheduled for deletion</h2>
        {loading ? (
          <div className="loading-row">Loading…</div>
        ) : scheduled.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="Nothing is currently scheduled for deletion" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Business</th><th>Eligible from</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {scheduled.map((b) => (
                <tr key={b.id}>
                  <td>{b.name}</td>
                  <td>{formatDate(b.pending_deletion_at!)}</td>
                  <td>{eligibleNow(b) ? <span className="badge badge--attention">Ready to purge</span> : <span className="badge badge--neutral">Grace period</span>}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn btn-ghost" onClick={() => handleCancel(b)}>Cancel</button>{" "}
                    <button
                      className="btn btn-primary" style={{ background: "var(--red-600)" }}
                      disabled={!eligibleNow(b)}
                      onClick={() => setPurgeTarget(b)}
                    >
                      Execute purge
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card" style={{ padding: 0 }}>
        <h2 className="section-title" style={{ padding: "18px 20px 0" }}>All businesses</h2>
        {!loading && (
          <table className="data-table">
            <thead><tr><th>Business</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {businesses.filter((b) => !b.pending_deletion_at).map((b) => (
                <tr key={b.id}>
                  <td>{b.name}</td>
                  <td>{b.is_active ? <span className="badge badge--good">Active</span> : <span className="badge badge--attention">Frozen</span>}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn btn-ghost" style={{ color: "var(--red-600)" }} onClick={() => setScheduleTarget(b)}>
                      Schedule deletion
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {scheduleTarget && (
        <Modal title={`Schedule deletion — ${scheduleTarget.name}`} onClose={() => { setScheduleTarget(null); setConfirmText(""); }}>
          <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 14 }}>
            This freezes the account immediately and starts a grace window. Type the business's
            exact name to confirm.
          </p>
          <Field label="Grace period (days)">
            <input className="input" type="number" min={1} max={30} value={graceDays} onChange={(e) => setGraceDays(Number(e.target.value))} />
          </Field>
          <Field label={`Type "${scheduleTarget.name}" to confirm`}>
            <input className="input" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} />
          </Field>
          <button
            className="btn btn-primary" style={{ width: "100%", background: "var(--red-600)" }}
            disabled={submitting || confirmText !== scheduleTarget.name}
            onClick={handleSchedule}
          >
            {submitting ? "Scheduling…" : "Schedule deletion & freeze account"}
          </button>
        </Modal>
      )}

      {purgeTarget && (
        <Modal title={`Permanently delete — ${purgeTarget.name}`} onClose={() => { setPurgeTarget(null); setConfirmText(""); }}>
          <p style={{ fontSize: 15, color: "var(--red-600)", marginBottom: 14, fontWeight: 600 }}>
            This cannot be undone. Every product, sale, customer, and record for this business
            will be permanently deleted.
          </p>
          <Field label={`Type "${purgeTarget.name}" to confirm`}>
            <input className="input" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} />
          </Field>
          <button
            className="btn btn-primary" style={{ width: "100%", background: "var(--red-600)" }}
            disabled={submitting || confirmText !== purgeTarget.name}
            onClick={handleExecute}
          >
            {submitting ? "Deleting…" : "Permanently delete everything"}
          </button>
        </Modal>
      )}
    </div>
  );
}

function FeatureLayoutTab() {
  const [features, setFeatures] = useState<AdminFeatureLayoutEntry[]>([]);
  const [hubs, setHubs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminFeatureLayout()
      .then((data) => { setFeatures(data.features); setHubs(data.hubs); })
      .catch((err) => setError(extractErrorMessage(err, "Couldn't load the feature layout.")))
      .finally(() => setLoading(false));
  }, []);

  async function handleMove(featureKey: string, hub: string) {
    setSavingKey(featureKey);
    setError(null);
    try {
      const updated = await updateAdminFeatureLayout(featureKey, hub);
      setFeatures((prev) => prev.map((f) => (f.key === featureKey ? { ...f, current_hub: updated.current_hub } : f)));
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't move that feature."));
    } finally {
      setSavingKey(null);
    }
  }

  if (loading) return <p style={{ fontSize: 15, color: "var(--ink-300)" }}>Loading…</p>;

  const catalogByKey = new Map(FEATURE_CATALOG.map((f) => [f.key, f]));

  return (
    <div className="card" style={{ padding: 20 }}>
      <h2 className="section-title">Feature layout</h2>
      <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
        Move any existing feature to a different dashboard — takes effect immediately for every
        business, no code change or redeploy needed. This only rearranges where a feature lives;
        it doesn't add, remove, or rename anything.
      </p>
      {error && <p className="inline-error" style={{ marginBottom: 12 }}>{error}</p>}
      <table className="data-table">
        <thead>
          <tr><th>Feature</th><th>Currently under</th><th></th></tr>
        </thead>
        <tbody>
          {features.map((f) => {
            const display = catalogByKey.get(f.key);
            return (
              <tr key={f.key}>
                <td>{display?.title || f.key}</td>
                <td>
                  <select
                    className="input"
                    style={{ maxWidth: 200 }}
                    value={f.current_hub}
                    disabled={savingKey === f.key}
                    onChange={(e) => handleMove(f.key, e.target.value)}
                  >
                    {hubs.map((h) => <option key={h} value={h}>{HUB_TITLES[h as HubKey] || h}</option>)}
                  </select>
                </td>
                <td style={{ fontSize: 14, color: "var(--ink-300)" }}>
                  {f.current_hub !== f.default_hub && `Default: ${HUB_TITLES[f.default_hub as HubKey] || f.default_hub}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
