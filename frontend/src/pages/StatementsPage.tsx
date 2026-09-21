import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import Field from "../components/Field";
import Modal from "../components/Modal";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { getCustomers, fetchStatementCsvUrl, getLoanReadinessReports, generateLoanReadinessReport, fetchLoanReadinessPdfUrl,
  getRecurringExpenseSchedules, createRecurringExpenseSchedule, updateRecurringExpenseSchedule, deleteRecurringExpenseSchedule,
  getCashFlowForecast } from "../api/resources";
import type { Customer, LoanReadinessReport, RecurringExpenseSchedule, CashFlowForecast } from "../api/types";
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

type StatementType = "sales" | "expenses" | "customer" | "ledger" | "profitability";

const STATEMENT_OPTIONS: { type: StatementType; label: string; description: string; needsProfit: boolean }[] = [
  { type: "sales", label: "Sales statement", description: "Every completed sale in the period — receipt code, branch, cashier, customer, and totals.", needsProfit: true },
  { type: "expenses", label: "Expense statement", description: "All non-voided expenses in the period, with category, status, and who requested/approved each.", needsProfit: true },
  { type: "customer", label: "Customer statement", description: "One customer's full account history — credit sales, payments, and running balance.", needsProfit: false },
  { type: "ledger", label: "Ledger statement", description: "The full double-entry transaction record for the period — every posted journal entry and its lines.", needsProfit: true },
  { type: "profitability", label: "Profitability statement", description: "Cost, price, margin, and profit per product, as of right now.", needsProfit: true },
];

export default function StatementsPage() {
  const { hasPermission } = useAuth();
  const { activeBranchId } = useBusiness();
  const canViewProfit = hasPermission("view_profit");

  const [selected, setSelected] = useState<StatementType>(canViewProfit ? "sales" : "customer");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [loanReports, setLoanReports] = useState<LoanReadinessReport[]>([]);
  const [loanLoading, setLoanLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [loanError, setLoanError] = useState<string | null>(null);

  function refreshLoanReports() {
    if (!canViewProfit) return;
    setLoanLoading(true);
    getLoanReadinessReports().then(setLoanReports).finally(() => setLoanLoading(false));
  }
  useEffect(refreshLoanReports, [canViewProfit]);

  const [schedules, setSchedules] = useState<RecurringExpenseSchedule[]>([]);
  const [forecast, setForecast] = useState<CashFlowForecast | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [showAddSchedule, setShowAddSchedule] = useState(false);
  const [scheduleName, setScheduleName] = useState("");
  const [scheduleAmount, setScheduleAmount] = useState("");
  const [scheduleDay, setScheduleDay] = useState("1");
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [scheduleSubmitting, setScheduleSubmitting] = useState(false);

  function refreshForecast() {
    if (!canViewProfit) return;
    setForecastLoading(true);
    Promise.all([getRecurringExpenseSchedules(), getCashFlowForecast(30)])
      .then(([s, f]) => { setSchedules(s); setForecast(f); })
      .finally(() => setForecastLoading(false));
  }
  useEffect(refreshForecast, [canViewProfit]);

  async function handleAddSchedule() {
    if (!scheduleName.trim() || !scheduleAmount) { setScheduleError("Enter a name and amount."); return; }
    setScheduleSubmitting(true);
    setScheduleError(null);
    try {
      await createRecurringExpenseSchedule({
        name: scheduleName.trim(), amount: parseFloat(scheduleAmount), day_of_month: parseInt(scheduleDay, 10) || 1,
      });
      setShowAddSchedule(false);
      setScheduleName(""); setScheduleAmount(""); setScheduleDay("1");
      refreshForecast();
    } catch (err: any) {
      setScheduleError(extractErrorMessage(err, "Couldn't add that."));
    } finally {
      setScheduleSubmitting(false);
    }
  }

  async function handleToggleSchedule(s: RecurringExpenseSchedule) {
    await updateRecurringExpenseSchedule(s.id, { is_active: !s.is_active });
    refreshForecast();
  }

  async function handleDeleteSchedule(id: string) {
    await deleteRecurringExpenseSchedule(id);
    refreshForecast();
  }

  async function handleGenerateLoanReport() {
    setGenerating(true);
    setLoanError(null);
    try {
      await generateLoanReadinessReport(12);
      refreshLoanReports();
    } catch (err: any) {
      setLoanError(extractErrorMessage(err, "Couldn't generate the report."));
    } finally {
      setGenerating(false);
    }
  }

  useEffect(() => {
    getCustomers().then(setCustomers).catch((err) => console.error("Failed to load customers:", err));
  }, []);

  const availableOptions = STATEMENT_OPTIONS.filter((o) => canViewProfit || !o.needsProfit);
  const current = STATEMENT_OPTIONS.find((o) => o.type === selected)!;

  async function handleDownload() {
    setError(null);
    if (selected === "customer" && !customerId) {
      setError("Choose a customer first.");
      return;
    }
    setDownloading(true);
    try {
      const params: Record<string, string> = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (selected !== "customer" && activeBranchId) params.branch = activeBranchId;
      if (selected === "customer") params.customer = customerId;
      const url = await fetchStatementCsvUrl(selected, params);
      const customerName = customers.find((c) => c.id === customerId)?.name;
      const filename = selected === "customer" && customerName
        ? `${customerName}-statement.csv`
        : `${selected}-statement.csv`;
      downloadBlobUrl(url, filename);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't generate that statement."));
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Statements"
        subtitle="Download a formal record of the business's sales, expenses, customer accounts, ledger, or product profitability."
      />

      <div className="card" style={{ padding: 20, maxWidth: 560 }}>
        <Field label="Statement type">
          <select className="input" value={selected} onChange={(e) => setSelected(e.target.value as StatementType)}>
            {availableOptions.map((o) => (
              <option key={o.type} value={o.type}>{o.label}</option>
            ))}
          </select>
        </Field>
        <p style={{ fontSize: 15, color: "var(--ink-300)", marginTop: -8, marginBottom: 16 }}>
          {current.description}
        </p>

        {selected === "customer" && (
          <Field label="Customer" required>
            <select className="input" value={customerId} onChange={(e) => setCustomerId(e.target.value)}>
              <option value="">Select a customer…</option>
              {customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
        )}

        <div style={{ display: "flex", gap: 12 }}>
          <Field label="From">
            <input className="input" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </Field>
          <Field label="To">
            <input className="input" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </Field>
        </div>
        {selected !== "customer" && (
          <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginTop: -8, marginBottom: 16 }}>
            Leave dates blank for the full history. Scoped to your currently active branch.
          </p>
        )}

        {error && <p className="inline-error">{error}</p>}
        <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleDownload} disabled={downloading}>
          {downloading ? "Preparing…" : `Download ${current.label}`}
        </button>
      </div>

      {canViewProfit && (
        <div className="card" style={{ padding: 20, maxWidth: 560, marginTop: 20 }}>
          <h2 className="section-title">Loan / Investor Readiness Report</h2>
          <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
            A formatted summary of the business's revenue, profit, and debt position — built for showing a bank
            or investor, not for your own bookkeeping. Each report is a frozen snapshot with a QR code a lender
            can scan to confirm it's genuine and unedited; generating a new one never changes an older one already
            in someone's hands.
          </p>
          <button className="btn btn-primary" onClick={handleGenerateLoanReport} disabled={generating} style={{ marginBottom: 16 }}>
            {generating ? "Generating…" : "Generate new report (last 12 months)"}
          </button>
          {loanError && <p className="inline-error">{loanError}</p>}

          {loanLoading ? (
            <div className="loading-row">Loading…</div>
          ) : loanReports.length === 0 ? (
            <p style={{ fontSize: 15, color: "var(--ink-300)" }}>No reports generated yet.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {loanReports.map((r) => (
                <div key={r.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
                  <div>
                    <div style={{ fontSize: 15.5 }}>Generated {formatDate(r.created_at)}</div>
                    <div style={{ fontSize: 14, color: "var(--ink-300)" }}>
                      Revenue {formatMoney(r.snapshot_json.total_revenue)}
                      {r.snapshot_json.gross_margin_percent && ` · ${r.snapshot_json.gross_margin_percent}% margin`}
                    </div>
                  </div>
                  <button className="btn btn-ghost" onClick={async () => window.open(await fetchLoanReadinessPdfUrl(r.id), "_blank")}>
                    Download PDF
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {canViewProfit && (
        <div className="card" style={{ padding: 20, maxWidth: 560, marginTop: 20 }}>
          <h2 className="section-title">Cash-Flow Danger-Day Forecast</h2>
          <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
            Compares your average daily sales against known upcoming obligations — rent, salaries, loan
            repayments — so you see a day that's likely to be tight before it happens, not after. Plain
            arithmetic on your own numbers, not a prediction.
          </p>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <span style={{ fontSize: 15, fontWeight: 600 }}>Known recurring obligations</span>
            <button className="btn btn-ghost" onClick={() => setShowAddSchedule(true)}>+ Add</button>
          </div>
          {schedules.length === 0 ? (
            <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginBottom: 16 }}>
              None added yet — add rent, salaries, or anything else that's due on a predictable day each month.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 16 }}>
              {schedules.map((s) => (
                <div key={s.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 15 }}>
                  <span style={{ color: s.is_active ? "var(--ink-800)" : "var(--ink-300)" }}>
                    {s.name} — {formatMoney(s.amount)} on day {s.day_of_month} {!s.is_active && "(off)"}
                  </span>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button className="btn btn-ghost" onClick={() => handleToggleSchedule(s)}>{s.is_active ? "Turn off" : "Turn on"}</button>
                    <button className="btn btn-ghost" onClick={() => handleDeleteSchedule(s.id)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {forecastLoading ? (
            <div className="loading-row">Loading…</div>
          ) : forecast?.insufficient_data ? (
            <p style={{ fontSize: 14.5, color: "var(--ink-300)" }}>{forecast.reason}</p>
          ) : forecast && (
            <>
              <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginBottom: 10 }}>
                Average daily cash-in (last 30 days): {formatMoney(forecast.average_daily_cash_in || "0")}
              </p>
              {forecast.danger_days.length === 0 ? (
                <p style={{ fontSize: 15, color: "var(--green-600)" }}>No danger days in the next 30 days.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {forecast.danger_days.map((d) => (
                    <div key={d.date} className="badge badge--attention" style={{ display: "block", padding: "8px 12px", textAlign: "left" }}>
                      <strong>{formatDate(d.date)}</strong> ({d.days_from_now === 0 ? "today" : `in ${d.days_from_now} days`}) —
                      {" "}{d.items.map((i) => i.name).join(", ")} totals {formatMoney(d.expected_outflow)},
                      {" "}above your average day of {formatMoney(d.average_daily_cash_in)} by {formatMoney(d.shortfall)}.
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {!canViewProfit && (
        <div style={{ marginTop: 16 }}>
          <EmptyState
            title="Some statements are restricted"
            subtitle="Sales, expense, ledger, and profitability statements need the view profit permission. Ask an owner or admin if you need one of those."
          />
        </div>
      )}

      {showAddSchedule && (
        <Modal title="Add recurring obligation" onClose={() => setShowAddSchedule(false)}>
          <Field label="Name" hint="e.g. Shop rent, Staff salaries">
            <input className="input" value={scheduleName} onChange={(e) => setScheduleName(e.target.value)} />
          </Field>
          <Field label="Amount">
            <input className="input" type="number" value={scheduleAmount} onChange={(e) => setScheduleAmount(e.target.value)} />
          </Field>
          <Field label="Day of month due" hint="1–31 — if a month is shorter, treated as due on its last day">
            <input className="input" type="number" min={1} max={31} value={scheduleDay} onChange={(e) => setScheduleDay(e.target.value)} />
          </Field>
          {scheduleError && <p className="inline-error">{scheduleError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleAddSchedule} disabled={scheduleSubmitting}>
            {scheduleSubmitting ? "Adding…" : "Add"}
          </button>
        </Modal>
      )}
    </div>
  );
}
