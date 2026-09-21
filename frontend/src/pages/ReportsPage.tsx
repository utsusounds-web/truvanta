import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import { useBusiness } from "../context/BusinessContext";
import { useAuth } from "../context/AuthContext";
import {
  getWhereDidMyMoneyGo, getSales, cancelSale, getInventoryProfitability,
  fetchSalesCsvUrl, fetchProfitabilityCsvUrl, fetchOwnerDashboardCsvUrl,
} from "../api/resources";
import type { WhereDidMyMoneyGo, Sale, InventoryProfitability } from "../api/types";
import { formatMoney, formatDate, extractErrorMessage } from "../lib/format";

function downloadBlobUrl(url: string, filename: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

export default function ReportsPage() {
  const { activeBranchId } = useBusiness();
  const { hasPermission } = useAuth();
  const canViewProfit = hasPermission("view_profit");
  const canCancelSales = hasPermission("cancel_sales");
  const [money, setMoney] = useState<WhereDidMyMoneyGo | null>(null);
  const [sales, setSales] = useState<Sale[]>([]);
  const [profitability, setProfitability] = useState<InventoryProfitability | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    if (!activeBranchId) return;
    setLoading(true);
    Promise.allSettled([
      canViewProfit ? getWhereDidMyMoneyGo({ branch: activeBranchId }) : Promise.resolve(null),
      getSales({ branch: activeBranchId }),
      canViewProfit ? getInventoryProfitability({ branch: activeBranchId }) : Promise.resolve(null),
    ]).then(([m, s, p]) => {
      if (m.status === "fulfilled") setMoney(m.value); else console.error("Failed to load money report:", m.reason);
      if (s.status === "fulfilled") setSales(s.value); else console.error("Failed to load sales:", s.reason);
      if (p.status === "fulfilled") setProfitability(p.value); else console.error("Failed to load profitability:", p.reason);
    }).finally(() => setLoading(false));
  }
  useEffect(refresh, [activeBranchId]);

  async function handleCancel(sale: Sale) {
    const reason = window.prompt("Reason for cancelling this sale:");
    if (!reason) return;
    setError(null);
    try {
      await cancelSale(sale.id, reason);
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't cancel that sale."));
    }
  }

  async function handleExportSalesCsv() {
    const url = await fetchSalesCsvUrl({ branch: activeBranchId || "" });
    downloadBlobUrl(url, "sales.csv");
  }

  async function handleExportProfitabilityCsv() {
    const url = await fetchProfitabilityCsvUrl({ branch: activeBranchId || "" });
    downloadBlobUrl(url, "profitability.csv");
  }

  async function handleExportDashboardCsv() {
    const url = await fetchOwnerDashboardCsvUrl({ branch: activeBranchId || "" });
    downloadBlobUrl(url, "owner-dashboard.csv");
  }

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Where your money went, and the full sales record."
        actions={canViewProfit ? <button className="btn btn-ghost" onClick={handleExportDashboardCsv}>Export dashboard CSV</button> : undefined}
      />

      {canViewProfit && (
      <div className="card" style={{ padding: 24, marginBottom: 24 }}>
        <h2 className="section-title">Where Did My Money Go?</h2>
        {!money ? <div className="loading-row">Loading…</div> : (
          <>
            <p style={{ fontSize: 16, marginBottom: 14 }}>You received <strong>{formatMoney(money.money_received)}</strong>.</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 15.5 }}>
              <MoneyRow label="Stock purchases" value={money.breakdown.stock_purchases} />
              <MoneyRow label="Expenses" value={money.breakdown.expenses} />
              <MoneyRow label="Supplier payments" value={money.breakdown.supplier_payments} />
              <MoneyRow label="Outstanding customer credit" value={money.breakdown.outstanding_customer_credit} />
              <div style={{ borderTop: "1px solid var(--line)", paddingTop: 8, display: "flex", justifyContent: "space-between", fontWeight: 700 }}>
                <span>Cash remaining</span><span>{formatMoney(money.cash_remaining)}</span>
              </div>
            </div>
          </>
        )}
      </div>
      )}

      {canViewProfit && (
      <div className="card" style={{ padding: 24, marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
          <h2 className="section-title" style={{ margin: 0 }}>Profitability</h2>
          <button className="btn btn-ghost" onClick={handleExportProfitabilityCsv}>Export CSV</button>
        </div>
        {!profitability ? <div className="loading-row">Loading…</div> : (
          <>
            <div className="stat-grid" style={{ marginBottom: 20 }}>
              <div className="stat-card">
                <div className="stat-label">Stock cost value</div>
                <div className="stat-value">{formatMoney(profitability.total_cost_value)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Stock retail value</div>
                <div className="stat-value">{formatMoney(profitability.total_retail_value)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Potential profit</div>
                <div className="stat-value" style={{ color: parseFloat(profitability.total_potential_profit) >= 0 ? "var(--green-600)" : "var(--red-600)" }}>
                  {formatMoney(profitability.total_potential_profit)}
                </div>
              </div>
            </div>

            {profitability.products_at_loss.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <p style={{ fontSize: 15, fontWeight: 700, color: "var(--red-600)", marginBottom: 8 }}>
                  Selling at a loss right now
                </p>
                <table className="data-table">
                  <thead><tr><th>Product</th><th className="num">Qty</th><th className="num">Cost</th><th className="num">Price</th><th className="num">Loss / unit</th></tr></thead>
                  <tbody>
                    {profitability.products_at_loss.map((p) => (
                      <tr key={p.product_id}>
                        <td>{p.product_name}</td>
                        <td className="num">{p.quantity_on_hand}</td>
                        <td className="num">{formatMoney(p.cost_price)}</td>
                        <td className="num">{formatMoney(p.selling_price)}</td>
                        <td className="num" style={{ color: "var(--red-600)" }}>{formatMoney(p.profit_per_unit)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {profitability.old_stock_needing_price_review.length > 0 && (
              <div>
                <p style={{ fontSize: 15, fontWeight: 700, color: "var(--gold-600)", marginBottom: 8 }}>
                  Old stock — no sale in 30+ days, worth a price review
                </p>
                <table className="data-table">
                  <thead><tr><th>Product</th><th className="num">Qty</th><th className="num">Margin</th><th>Last sold</th></tr></thead>
                  <tbody>
                    {profitability.old_stock_needing_price_review.map((p) => (
                      <tr key={p.product_id}>
                        <td>{p.product_name}</td>
                        <td className="num">{p.quantity_on_hand}</td>
                        <td className="num">{p.profit_margin_percent}%</td>
                        <td>{p.last_sale_at ? formatDate(p.last_sale_at) : "Never"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {profitability.products_at_loss.length === 0 && profitability.old_stock_needing_price_review.length === 0 && (
              <EmptyState title="Nothing flagged" subtitle="No products are currently at a loss or sitting stale." />
            )}
          </>
        )}
      </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h2 className="section-title" style={{ margin: 0 }}>All sales</h2>
        <button className="btn btn-ghost" onClick={handleExportSalesCsv}>Export CSV</button>
      </div>
      {error && <p className="inline-error">{error}</p>}
      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : sales.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No sales recorded yet" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Receipt #</th><th>Date</th><th className="num">Total</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {sales.map((s) => (
                <tr key={s.id}>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: 14.5 }}>{s.transaction_number}</td>
                  <td>{formatDate(s.created_at)}</td>
                  <td className="num">{formatMoney(s.grand_total)}</td>
                  <td><span className={`badge badge--${s.status}`}>{s.status.replace(/_/g, " ")}</span></td>
                  <td>{s.status === "completed" && canCancelSales && <button className="btn btn-ghost" onClick={() => handleCancel(s)}>Cancel</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function MoneyRow({ label, value }: { label: string; value: string }) {
  return <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--ink-600)" }}>{label}</span><span>{formatMoney(value)}</span></div>;
}
