import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { getCustomers, createCustomer, getCustomerCreditTransactions, getDebtAging, fetchStatementCsvUrl } from "../api/resources";
import { queueGenericOffline, isOnline } from "../offline/sync";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { Customer, DebtAging } from "../api/types";
import { formatMoney, formatDate, extractErrorMessage } from "../lib/format";

export default function CustomersPage() {
  const { hasPermission } = useAuth();
  const canViewProfit = hasPermission("view_profit");
  const [view, setView] = useState<"customers" | "aging">("customers");
  const [aging, setAging] = useState<DebtAging | null>(null);
  const [agingLoading, setAgingLoading] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", phone_number: "", address: "" });
  const [selected, setSelected] = useState<Customer | null>(null);
  const [ledger, setLedger] = useState<{ id: string; entry_type: string; amount: string; created_at: string; reference_note: string }[]>([]);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [offlineQueuedMsg, setOfflineQueuedMsg] = useState(false);

  function refresh() {
    setLoading(true);
    getCustomers().then(setCustomers).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  useEffect(() => {
    if (view !== "aging" || !canViewProfit) return;
    setAgingLoading(true);
    getDebtAging().then(setAging).finally(() => setAgingLoading(false));
  }, [view, canViewProfit]);

  async function handleDownloadAging() {
    const url = await fetchStatementCsvUrl("debt_aging");
    const a = document.createElement("a");
    a.href = url; a.download = "debt-aging.csv"; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  async function handleAdd() {
    if (!form.name) { setError("Name is required."); return; }
    setSubmitting(true); setError(null);
    try {
      await createCustomer(form);
      setShowAdd(false);
      setForm({ name: "", phone_number: "", address: "" });
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't add customer."));
    } finally { setSubmitting(false); }
  }

  function openLedger(c: Customer) {
    setSelected(c);
    getCustomerCreditTransactions(c.id).then(setLedger);
  }

  async function handleRecordPayment() {
    if (!selected || !paymentAmount) return;
    setSubmitting(true); setError(null);
    const payload = {
      customer: selected.id, entry_type: "payment", amount: -Math.abs(parseFloat(paymentAmount)),
      reference_note: "Payment received",
    };

    if (!isOnline()) {
      await queueGenericOffline("/customer-credit-transactions/", payload);
      setError(null);
      setPaymentAmount("");
      setOfflineQueuedMsg(true);
      setSubmitting(false);
      return;
    }

    try {
      await client.post("/customer-credit-transactions/", payload);
      setPaymentAmount("");
      openLedger(selected);
      refresh();
    } catch (err: any) {
      if (err?.code === "ERR_NETWORK") {
        await queueGenericOffline("/customer-credit-transactions/", payload);
        setPaymentAmount("");
        setOfflineQueuedMsg(true);
      } else {
        setError(extractErrorMessage(err, "Couldn't record payment."));
      }
    } finally { setSubmitting(false); }
  }

  return (
    <div>
      <PageHeader
        title="Customers"
        subtitle="Credit balances and payment history."
        actions={<button className="btn btn-primary" onClick={() => setShowAdd(true)}>Add customer</button>}
      />

      {canViewProfit && (
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button className={`btn ${view === "customers" ? "btn-primary" : "btn-ghost"}`} onClick={() => setView("customers")}>Customers</button>
          <button className={`btn ${view === "aging" ? "btn-primary" : "btn-ghost"}`} onClick={() => setView("aging")}>Debt Aging</button>
        </div>
      )}

      {view === "aging" ? (
        <div className="card">
          {agingLoading ? (
            <div className="loading-row">Loading…</div>
          ) : !aging || aging.customers.length === 0 ? (
            <div style={{ padding: 24 }}><EmptyState title="No outstanding balances" subtitle="Nobody currently owes the business anything." /></div>
          ) : (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 20px 0" }}>
                <p style={{ fontSize: 14.5, color: "var(--ink-300)" }}>As of {formatDate(aging.as_of)}</p>
                <button className="btn btn-ghost" onClick={handleDownloadAging}>Download CSV</button>
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Customer</th><th className="num">Outstanding</th><th className="num">Current</th>
                    <th className="num">1–30 days</th><th className="num">31–60 days</th><th className="num">61–90 days</th><th className="num">90+ days</th>
                  </tr>
                </thead>
                <tbody>
                  {aging.customers.map((c) => {
                    const overdue = parseFloat(c.buckets["1_30"]) + parseFloat(c.buckets["31_60"]) + parseFloat(c.buckets["61_90"]) + parseFloat(c.buckets.over_90);
                    return (
                      <tr key={c.customer_id}>
                        <td>{c.customer_name}{overdue > 0 && <span className="badge badge--attention" style={{ marginLeft: 8 }}>Overdue</span>}</td>
                        <td className="num">{formatMoney(c.outstanding_balance)}</td>
                        <td className="num">{formatMoney(c.buckets.current)}</td>
                        <td className="num">{formatMoney(c.buckets["1_30"])}</td>
                        <td className="num">{formatMoney(c.buckets["31_60"])}</td>
                        <td className="num">{formatMoney(c.buckets["61_90"])}</td>
                        <td className="num" style={{ color: parseFloat(c.buckets.over_90) > 0 ? "var(--red-600)" : undefined }}>{formatMoney(c.buckets.over_90)}</td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr style={{ fontWeight: 700 }}>
                    <td>Total</td>
                    <td className="num">{formatMoney(aging.total_outstanding)}</td>
                    <td className="num">{formatMoney(aging.totals.current)}</td>
                    <td className="num">{formatMoney(aging.totals["1_30"])}</td>
                    <td className="num">{formatMoney(aging.totals["31_60"])}</td>
                    <td className="num">{formatMoney(aging.totals["61_90"])}</td>
                    <td className="num">{formatMoney(aging.totals.over_90)}</td>
                  </tr>
                </tfoot>
              </table>
            </>
          )}
        </div>
      ) : (
      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : customers.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No customers yet" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Name</th><th>Phone</th><th className="num">Outstanding balance</th><th></th></tr></thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>{c.phone_number || "—"}</td>
                  <td className="num">{formatMoney(c.outstanding_balance)}</td>
                  <td><button className="btn btn-ghost" onClick={() => openLedger(c)}>View ledger</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      )}

      {showAdd && (
        <Modal title="Add customer" onClose={() => setShowAdd(false)}>
          <Field label="Name" required><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Phone number"><input className="input" value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} /></Field>
          <Field label="Address"><input className="input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleAdd} disabled={submitting}>{submitting ? "Saving…" : "Save customer"}</button>
        </Modal>
      )}

      {selected && (
        <Modal title={`${selected.name} — Ledger`} onClose={() => { setSelected(null); setError(null); }}>
          <p style={{ fontSize: 16, marginBottom: 16 }}>Outstanding: <strong>{formatMoney(selected.outstanding_balance)}</strong></p>

          <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
            <input className="input" type="number" placeholder="Payment amount" value={paymentAmount} onChange={(e) => setPaymentAmount(e.target.value)} />
            <button className="btn btn-primary" onClick={handleRecordPayment} disabled={submitting}>Record payment</button>
          </div>
          {error && <p className="inline-error">{error}</p>}
          {offlineQueuedMsg && (
            <p className="inline-error" style={{ background: "#E4F3EA", color: "var(--green-600)" }}>
              You're offline — this payment is saved on this device and will sync automatically once you're back online.
            </p>
          )}

          {ledger.length === 0 ? <EmptyState title="No transactions yet" /> : (
            <table className="data-table">
              <thead><tr><th>Date</th><th>Type</th><th className="num">Amount</th></tr></thead>
              <tbody>
                {ledger.map((t) => (
                  <tr key={t.id}>
                    <td>{formatDate(t.created_at)}</td>
                    <td style={{ textTransform: "capitalize" }}>{t.entry_type.replace(/_/g, " ")}</td>
                    <td className="num" style={{ color: parseFloat(t.amount) >= 0 ? "var(--red-600)" : "var(--green-600)" }}>{formatMoney(t.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Modal>
      )}
    </div>
  );
}
