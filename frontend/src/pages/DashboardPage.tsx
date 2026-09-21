import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import SimpleBarChart from "../components/SimpleBarChart";
import FeatureTour from "../components/FeatureTour";
import { useBusiness } from "../context/BusinessContext";
import { useAuth } from "../context/AuthContext";
import { getOwnerDashboard, getBusinessHealth, getRiskAlerts, getProducts, getShifts, getDailyPriorities, getContinuityStatus, getSalesTrend } from "../api/resources";
import { getBusiness } from "../api/tenants";
import type { OwnerDashboard, BusinessHealth, RiskAlert, PriorityItem, ContinuityStatus } from "../api/types";
import type { BusinessResponse } from "../api/tenants";
import { formatMoney, formatDate } from "../lib/format";
import EmptyState from "../components/EmptyState";

function tourSeenKey(userId: string) {
  return `sbos_tour_seen_${userId}`;
}

export default function DashboardPage() {
  const { activeBranchId } = useBusiness();
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState<OwnerDashboard | null>(null);
  const [health, setHealth] = useState<BusinessHealth | null>(null);
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [priorities, setPriorities] = useState<PriorityItem[]>([]);
  const [continuityStatus, setContinuityStatus] = useState<ContinuityStatus | null>(null);
  const [business, setBusiness] = useState<BusinessResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checklist, setChecklist] = useState<{ hasProducts: boolean; hasOpenShift: boolean } | null>(null);
  const [showChart, setShowChart] = useState(false);
  const [salesTrend, setSalesTrend] = useState<{ date: string; total: string }[] | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [showTour, setShowTour] = useState(false);
  const [figuresHidden, setFiguresHidden] = useState(() => localStorage.getItem("sbos_figures_hidden") === "1");

  function toggleFiguresHidden() {
    setFiguresHidden((prev) => {
      const next = !prev;
      localStorage.setItem("sbos_figures_hidden", next ? "1" : "0");
      return next;
    });
  }

  function maskable(value: string): string {
    return figuresHidden ? "••••••" : value;
  }

  useEffect(() => {
    if (!user?.id) return;
    if (!localStorage.getItem(tourSeenKey(user.id))) {
      setShowTour(true);
    }
  }, [user?.id]);

  function dismissTour() {
    setShowTour(false);
    if (user?.id) localStorage.setItem(tourSeenKey(user.id), "1");
  }

  function handleToggleChart() {
    setShowChart((prev) => {
      const next = !prev;
      // Fetched lazily, only the first time it's actually opened — no
      // point loading a chart nobody's chosen to look at yet.
      if (next && !salesTrend && activeBranchId) {
        setChartLoading(true);
        getSalesTrend({ branch: activeBranchId, days: "7" })
          .then(setSalesTrend)
          .finally(() => setChartLoading(false));
      }
      return next;
    });
  }

  useEffect(() => {
    const businessId = localStorage.getItem("sbos_business_id");
    if (businessId) getBusiness(businessId).then(setBusiness).catch((err) => console.error("Failed to load business info for dashboard header:", err));
  }, []);

  useEffect(() => {
    if (!activeBranchId) return;
    setLoading(true);
    setError(null);
    Promise.allSettled([
      getOwnerDashboard({ branch: activeBranchId }),
      getBusinessHealth({ branch: activeBranchId }),
      getRiskAlerts({ branch: activeBranchId, days: "7" }),
      getDailyPriorities({ branch: activeBranchId }),
    ]).then(([d, h, a, p]) => {
      if (d.status === "fulfilled") setDashboard(d.value); else console.error("Dashboard totals failed:", d.reason);
      if (h.status === "fulfilled") setHealth(h.value); else console.error("Business health failed:", h.reason);
      if (a.status === "fulfilled") setAlerts(a.value); else console.error("Risk alerts failed:", a.reason);
      if (p.status === "fulfilled") setPriorities(p.value); else console.error("Daily priorities failed:", p.reason);
      if ([d, h, a].some((r) => r.status === "rejected")) {
        setError("Some parts of the dashboard didn't load — check your connection and reload.");
      }
    }).finally(() => setLoading(false));
  }, [activeBranchId]);

  useEffect(() => {
    getContinuityStatus().then(setContinuityStatus).catch((err) => console.error("Continuity status failed:", err));
  }, []);

  useEffect(() => {
    if (!activeBranchId || !dashboard) return;
    // Only worth the extra calls for a brand-new business — anyone
    // with sales history doesn't need a getting-started checklist.
    if (dashboard.number_of_sales > 0) { setChecklist(null); return; }
    Promise.allSettled([
      getProducts({ branch: activeBranchId }),
      getShifts({ branch: activeBranchId, status: "open" }),
    ]).then(([p, s]) => {
      setChecklist({
        hasProducts: p.status === "fulfilled" && p.value.length > 0,
        hasOpenShift: s.status === "fulfilled" && s.value.length > 0,
      });
    });
  }, [activeBranchId, dashboard]);

  if (loading) {
    return (
      <div>
        <div className="loading-row">Loading your dashboard…</div>
        {showTour && <FeatureTour onClose={dismissTour} />}
      </div>
    );
  }

  const ownerName = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.email || "Owner";

  return (
    <div>
      <PageHeader
        title={
          <span style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {business?.logo_url && (
              <img src={business.logo_url} alt="" style={{ width: 40, height: 40, objectFit: "cover", borderRadius: 8, border: "1px solid var(--line)" }} />
            )}
            {`Welcome back, ${ownerName}`}
          </span>
        }
        subtitle={business?.name ?? undefined}
      />

      {error && <p className="inline-error">{error}</p>}

      <div className="card" style={{ marginBottom: 20 }}>
        <button
          onClick={handleToggleChart}
          style={{
            width: "100%", textAlign: "left", background: "none", border: "none", cursor: "pointer",
            padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center",
          }}
        >
          <span className="section-title" style={{ margin: 0 }}>Sales — last 7 days</span>
          <span style={{ fontSize: 15, color: "var(--ink-600)" }}>{showChart ? "Hide ▲" : "Show ▼"}</span>
        </button>
        {showChart && (
          <div style={{ padding: "0 20px 20px" }}>
            {chartLoading ? (
              <div className="loading-row">Loading…</div>
            ) : salesTrend && salesTrend.length > 0 ? (
              <SimpleBarChart
                data={salesTrend.map((d) => ({
                  label: new Date(d.date).toLocaleDateString(undefined, { weekday: "short" }),
                  value: parseFloat(d.total),
                }))}
                formatValue={(v) => maskable(formatMoney(v, business?.currency_code || "NGN"))}
              />
            ) : (
              <EmptyState title="No sales in the last 7 days" />
            )}
          </div>
        )}
      </div>

      {continuityStatus?.is_currently_active && (
        <div
          className="card"
          style={{ padding: "14px 20px", marginBottom: 20, background: "#FBF1DD", border: "1px solid var(--gold-600, #b8860b)" }}
        >
          <strong style={{ fontSize: 15.5 }}>Business Continuity Mode is active.</strong>
          <p style={{ fontSize: 14.5, color: "var(--ink-600)", margin: "4px 0 0" }}>
            No owner has logged in for a while, so {continuityStatus.backup_manager_name} currently has
            temporary owner-level access to keep things running. This ends automatically once an owner
            logs back in.
          </p>
        </div>
      )}

      {checklist && (!checklist.hasProducts || !checklist.hasOpenShift) && (
        <div className="card" style={{ padding: "16px 20px", marginBottom: 20 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <ChecklistItem
              done={checklist.hasProducts}
              label="Add your first product"
              to="/products"
              cta="Add products"
            />
            <ChecklistItem
              done={checklist.hasOpenShift}
              label="Open a shift so you can start taking sales"
              to="/shifts"
              cta="Open shift"
            />
            <ChecklistItem
              done={checklist.hasProducts && checklist.hasOpenShift}
              label="Make your first sale"
              to="/pos"
              cta="Go to POS"
            />
          </div>
        </div>
      )}

      {priorities.length > 0 && (
        <div className="card" style={{ padding: "18px 20px", marginBottom: 20 }}>
          <h2 className="section-title" style={{ marginBottom: 10 }}>What should I do today?</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {priorities.map((p, i) => (
              <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                <span
                  className={`badge badge--${p.severity === "critical" ? "critical" : p.severity === "important" ? "attention" : "neutral"}`}
                  style={{ flexShrink: 0, marginTop: 1 }}
                >
                  {p.severity === "critical" ? "Urgent" : p.severity === "important" ? "Today" : "FYI"}
                </span>
                <span style={{ fontSize: 15.5, color: "var(--ink-800)" }}>{p.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            Total Sales
            <button
              type="button"
              onClick={toggleFiguresHidden}
              title={figuresHidden ? "Show figures" : "Hide figures"}
              style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16, padding: 0, color: "var(--ink-300)", lineHeight: 1 }}
            >
              {figuresHidden ? "🙈" : "👁"}
            </button>
          </div>
          <div className="stat-value">{dashboard ? maskable(formatMoney(dashboard.total_sales)) : "—"}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label"># of Sales</div>
          <div className="stat-value">{dashboard?.number_of_sales ?? "—"}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Low Stock Items</div>
          <div className="stat-value">{dashboard?.low_stock_product_count ?? "—"}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Customer Debt</div>
          <div className="stat-value">{dashboard ? maskable(formatMoney(dashboard.total_customer_debt)) : "—"}</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div className="card" style={{ padding: 24 }}>
          <h2 className="section-title">Business Health</h2>
          {health ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <HealthRow label="Stock Control" value={health.stock_control} />
              <HealthRow label="Debt Management" value={health.debt_management} />
            </div>
          ) : <EmptyState title="No data yet" />}
        </div>

        <div className="card" style={{ padding: 24 }}>
          <h2 className="section-title">Needs a Look</h2>
          {alerts.length === 0 ? (
            <EmptyState title="Nothing unusual in the last 7 days" subtitle="Alerts appear here when a pattern is worth reviewing." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {alerts.slice(0, 6).map((a, i) => (
                <div key={i} style={{ fontSize: 15, padding: "8px 0", borderBottom: "1px solid var(--paper-100)" }}>
                  <span className={`badge badge--${a.severity}`} style={{ marginRight: 8 }}>{a.rule.replace(/_/g, " ")}</span>
                  {a.message}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {dashboard && dashboard.items_to_investigate.length > 0 && (
        <div className="card" style={{ padding: 24, marginTop: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <h2 className="section-title">Recent Sensitive Activity</h2>
            <Link to="/activity-log" style={{ fontSize: 14.5 }}>View full Activity Log →</Link>
          </div>
          <table className="data-table">
            <thead><tr><th>When</th><th>Action</th><th>Reason</th></tr></thead>
            <tbody>
              {dashboard.items_to_investigate.slice(0, 8).map((item, i) => (
                <tr key={i}>
                  <td>{formatDate(item.created_at)}</td>
                  <td style={{ textTransform: "capitalize" }}>{item.action.replace(/_/g, " ")}</td>
                  <td>{item.reason || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {showTour && <FeatureTour onClose={dismissTour} />}
    </div>
  );
}

function HealthRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ fontSize: 15.5, color: "var(--ink-600)" }}>{label}</span>
      <span className={`badge badge--${value}`}>{value}</span>
    </div>
  );
}

function ChecklistItem({ done, label, to, cta }: { done: boolean; label: string; to: string; cta: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0" }}>
      <span style={{ fontSize: 15.5, display: "flex", alignItems: "center", gap: 8 }}>
        <span
          style={{
            width: 18, height: 18, borderRadius: "50%", display: "inline-flex", alignItems: "center",
            justifyContent: "center", fontSize: 13, flexShrink: 0,
            background: done ? "var(--vault-100)" : "var(--paper-100)",
            color: done ? "var(--vault-700)" : "var(--ink-300)",
            border: done ? "none" : "1px solid var(--line)",
          }}
        >
          {done ? "✓" : ""}
        </span>
        <span style={{ color: done ? "var(--ink-300)" : "var(--ink-800)", textDecoration: done ? "line-through" : "none" }}>
          {label}
        </span>
      </span>
      {!done && <Link to={to} className="btn btn-ghost" style={{ textDecoration: "none", fontSize: 14.5 }}>{cta}</Link>}
    </div>
  );
}
