import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import { getOpeningBalance, saveOpeningBalance, fetchOpeningBalancePdfUrl } from "../api/ledger";
import type { OpeningBalanceStatement } from "../api/ledger";
import { formatMoney, formatDate, extractErrorMessage } from "../lib/format";

const FIELDS: { key: keyof typeof emptyForm; label: string; hint: string; kind: "asset" | "liability" }[] = [
  { key: "cash_on_hand", label: "Cash on hand", hint: "Physical cash you're currently holding", kind: "asset" },
  { key: "bank_balance", label: "Bank balance", hint: "Total across your business bank account(s)", kind: "asset" },
  { key: "accounts_receivable", label: "Money customers owe you", hint: "Add customers individually later — this is just the starting total", kind: "asset" },
  { key: "inventory_value", label: "Current stock value", hint: "What your existing stock is worth at cost, not selling price", kind: "asset" },
  { key: "fixed_assets", label: "Equipment & fixed assets", hint: "Shelving, fridges, till, furniture — things you own, not for resale", kind: "asset" },
  { key: "accounts_payable", label: "Money you owe suppliers", hint: "Add suppliers individually later — this is just the starting total", kind: "liability" },
  { key: "loans_payable", label: "Outstanding loans", hint: "Any other money you owe — a loan, an advance, anything similar", kind: "liability" },
];

const emptyForm = {
  as_of_date: new Date().toISOString().slice(0, 10),
  cash_on_hand: "", bank_balance: "", accounts_receivable: "", inventory_value: "",
  fixed_assets: "", accounts_payable: "", loans_payable: "",
};

export default function OpeningBalancePage() {
  const [existing, setExisting] = useState<OpeningBalanceStatement | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    getOpeningBalance().then((s) => {
      setExisting(s);
      if (!s) setEditing(true); // nothing recorded yet — go straight to the form
    }).finally(() => setLoading(false));
  }, []);

  function startEdit() {
    if (existing) {
      setForm({
        as_of_date: existing.as_of_date,
        cash_on_hand: existing.cash_on_hand, bank_balance: existing.bank_balance,
        accounts_receivable: existing.accounts_receivable, inventory_value: existing.inventory_value,
        fixed_assets: existing.fixed_assets, accounts_payable: existing.accounts_payable,
        loans_payable: existing.loans_payable,
      });
    }
    setEditing(true);
  }

  function num(key: keyof typeof emptyForm): number {
    if (key === "as_of_date") return 0;
    const v = parseFloat(form[key]);
    return isNaN(v) ? 0 : v;
  }

  const totalAssets = num("cash_on_hand") + num("bank_balance") + num("accounts_receivable") + num("inventory_value") + num("fixed_assets");
  const totalLiabilities = num("accounts_payable") + num("loans_payable");
  const netWorth = totalAssets - totalLiabilities;

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const saved = await saveOpeningBalance(form);
      setExisting(saved);
      setEditing(false);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save this."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDownload() {
    setPdfLoading(true);
    try {
      window.open(await fetchOpeningBalancePdfUrl(), "_blank");
    } finally {
      setPdfLoading(false);
    }
  }

  if (loading) return <div className="loading-row">Loading…</div>;

  return (
    <div>
      <PageHeader
        title="Opening Balance"
        subtitle="Your business's starting financial position — what you have and owe as of a specific date. This is what every profit and net-worth calculation from here on builds on top of."
      />

      {!editing && existing && (
        <div className="card" style={{ padding: 20, marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 14.5, color: "var(--ink-300)" }}>As of {formatDate(existing.as_of_date)}</div>
              {existing.recorded_by_name && (
                <div style={{ fontSize: 14.5, color: "var(--ink-300)" }}>Recorded by {existing.recorded_by_name} on {formatDate(existing.created_at)}</div>
              )}
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-ghost" onClick={handleDownload} disabled={pdfLoading}>
                {pdfLoading ? "Preparing…" : "Download statement"}
              </button>
              <button className="btn btn-ghost" onClick={startEdit}>Correct this</button>
            </div>
          </div>

          <table className="data-table">
            <tbody>
              {FIELDS.filter((f) => parseFloat((existing as any)[f.key]) !== 0).map((f) => (
                <tr key={f.key}>
                  <td>{f.label}</td>
                  <td style={{ textAlign: "right" }}>
                    {f.kind === "liability" && "− "}{formatMoney((existing as any)[f.key])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ display: "flex", justifyContent: "space-between", paddingTop: 12, marginTop: 8, borderTop: "1px solid var(--line)" }}>
            <strong>Net worth at that time</strong>
            <strong>{formatMoney(existing.net_worth)}</strong>
          </div>
        </div>
      )}

      {editing && (
        <div className="card" style={{ padding: 20 }}>
          <Field label="As of date">
            <input className="input" type="date" value={form.as_of_date} onChange={(e) => setForm({ ...form, as_of_date: e.target.value })} />
          </Field>
          <p style={{ fontSize: 14.5, color: "var(--ink-300)", margin: "4px 0 16px" }}>
            Leave anything that doesn't apply to you blank — it'll be treated as zero.
          </p>

          <div className="form-grid">
            {FIELDS.map((f) => (
              <div className="field--half" key={f.key}>
                <Field label={f.label} hint={f.hint}>
                  <input
                    className="input" type="number" min="0" placeholder="0"
                    value={form[f.key]}
                    onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                  />
                </Field>
              </div>
            ))}
          </div>

          <div className="card" style={{ padding: 16, marginTop: 8, marginBottom: 20, background: "var(--paper-100)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 15.5, marginBottom: 4 }}>
              <span>Total assets</span><span>{formatMoney(totalAssets)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 15.5, marginBottom: 8 }}>
              <span>Total owed</span><span>− {formatMoney(totalLiabilities)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", paddingTop: 8, borderTop: "1px solid var(--line)", fontWeight: 700 }}>
              <span>Net worth</span><span>{formatMoney(netWorth)}</span>
            </div>
          </div>

          {error && <p className="inline-error">{error}</p>}
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Saving…" : "Save opening balance"}
            </button>
            {existing && (
              <button className="btn btn-ghost" onClick={() => setEditing(false)}>Cancel</button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
