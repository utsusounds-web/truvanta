import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { useBusiness } from "../context/BusinessContext";
import { useAuth } from "../context/AuthContext";
import { getExpenses, getExpenseCategories, createExpenseCategory, createExpense, approveExpense, rejectExpense } from "../api/resources";
import { queueGenericOffline, isOnline } from "../offline/sync";
import type { Expense, ExpenseCategory } from "../api/types";
import { formatMoney, formatDate, extractErrorMessage } from "../lib/format";

export default function ExpensesPage() {
  const { hasPermission } = useAuth();
  const canApproveExpenses = hasPermission("approve_expenses");
  const { activeBranchId } = useBusiness();
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ category: "", amount: "", reason: "" });
  const [newCategory, setNewCategory] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [queuedOfflineMsg, setQueuedOfflineMsg] = useState(false);

  function refresh() {
    if (!activeBranchId) return;
    setLoading(true);
    Promise.allSettled([getExpenses({ branch: activeBranchId }), getExpenseCategories()]).then(([e, c]) => {
      if (e.status === "fulfilled") setExpenses(e.value); else console.error("Failed to load expenses:", e.reason);
      if (c.status === "fulfilled") setCategories(c.value); else console.error("Failed to load categories:", c.reason);
    }).finally(() => setLoading(false));
  }
  useEffect(refresh, [activeBranchId]);

  async function handleAddCategory() {
    if (!newCategory) return;
    const cat = await createExpenseCategory(newCategory);
    setCategories((c) => [...c, cat]);
    setForm((f) => ({ ...f, category: cat.id }));
    setNewCategory("");
  }

  async function handleAdd() {
    if (!activeBranchId || !form.category || !form.amount || !form.reason) {
      setError("Category, amount, and reason are all required.");
      return;
    }
    setSubmitting(true); setError(null);
    const payload = { branch: activeBranchId, category: form.category, amount: parseFloat(form.amount), reason: form.reason };

    if (!isOnline()) {
      await queueGenericOffline("/expenses/", payload);
      setQueuedOfflineMsg(true);
      setShowAdd(false);
      setForm({ category: "", amount: "", reason: "" });
      setSubmitting(false);
      return;
    }

    try {
      await createExpense(payload);
      setShowAdd(false);
      setForm({ category: "", amount: "", reason: "" });
      refresh();
    } catch (err: any) {
      if (err?.code === "ERR_NETWORK") {
        await queueGenericOffline("/expenses/", payload);
        setQueuedOfflineMsg(true);
        setShowAdd(false);
        setForm({ category: "", amount: "", reason: "" });
      } else {
        setError(extractErrorMessage(err, "Couldn't record expense."));
      }
    } finally { setSubmitting(false); }
  }

  async function handleApprove(id: string) { await approveExpense(id); refresh(); }
  async function handleReject(id: string) { await rejectExpense(id, "Rejected by owner"); refresh(); }

  return (
    <div>
      <PageHeader
        title="Expenses"
        subtitle="What went out, and why — kept separate from owner withdrawals."
        actions={<button className="btn btn-primary" onClick={() => setShowAdd(true)}>Record expense</button>}
      />

      {queuedOfflineMsg && (
        <div className="inline-error" style={{ background: "#E4F3EA", color: "var(--green-600)" }}>
          You're offline — this expense is saved on this device and will sync automatically once you're back online.
        </div>
      )}

      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : expenses.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No expenses recorded yet" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Date</th><th>Reason</th><th className="num">Amount</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {expenses.map((e) => (
                <tr key={e.id}>
                  <td>{formatDate(e.created_at)}</td>
                  <td>{e.reason}</td>
                  <td className="num">{formatMoney(e.amount)}</td>
                  <td><span className={`badge badge--${e.status}`}>{e.status.replace(/_/g, " ")}</span></td>
                  <td>
                    {e.status === "pending_approval" && canApproveExpenses && (
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="btn btn-ghost" onClick={() => handleApprove(e.id)}>Approve</button>
                        <button className="btn btn-ghost" onClick={() => handleReject(e.id)}>Reject</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showAdd && (
        <Modal title="Record expense" onClose={() => setShowAdd(false)}>
          <Field label="Category" required>
            <select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              <option value="">Select…</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
            <input className="input" placeholder="New category" value={newCategory} onChange={(e) => setNewCategory(e.target.value)} />
            <button type="button" className="btn btn-ghost" onClick={handleAddCategory}>Add</button>
          </div>
          <Field label="Amount" required><input className="input" type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></Field>
          <Field label="Reason" required><input className="input" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleAdd} disabled={submitting}>{submitting ? "Saving…" : "Save expense"}</button>
        </Modal>
      )}
    </div>
  );
}
