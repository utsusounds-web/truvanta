import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import { getTrialBalance } from "../api/ledger";
import type { LedgerAccountBalance } from "../api/ledger";
import { formatMoney } from "../lib/format";
import { useAuth } from "../context/AuthContext";

const TYPE_LABELS: Record<string, string> = {
  asset: "What you own",
  liability: "What you owe",
  equity: "Owner's stake",
  income: "Money coming in",
  expense: "Money going out",
};

export default function LedgerPage() {
  const { hasPermission } = useAuth();
  const canViewProfit = hasPermission("view_profit");
  const [accounts, setAccounts] = useState<LedgerAccountBalance[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!canViewProfit) { setLoading(false); return; }
    getTrialBalance().then(setAccounts).finally(() => setLoading(false));
  }, [canViewProfit]);

  const grouped = accounts.reduce<Record<string, LedgerAccountBalance[]>>((acc, a) => {
    (acc[a.type] ||= []).push(a);
    return acc;
  }, {});

  if (!canViewProfit) {
    return (
      <div>
        <PageHeader
          title="Ledger"
          subtitle="A formal double-entry record behind every sale, expense, and withdrawal — automatically kept in balance."
        />
        <EmptyState
          title="Restricted"
          subtitle="The ledger holds the business's full financial records. Ask an owner or admin for access if you need it."
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Ledger"
        subtitle="A formal double-entry record behind every sale, expense, and withdrawal — automatically kept in balance."
      />
      {loading ? (
        <div className="loading-row">Loading…</div>
      ) : accounts.length === 0 ? (
        <EmptyState title="Nothing posted yet" subtitle="Entries appear here automatically as you make sales and record expenses." />
      ) : (
        Object.entries(grouped).map(([type, rows]) => (
          <div key={type} className="card" style={{ padding: 20, marginBottom: 16 }}>
            <div className="section-title" style={{ marginBottom: 10 }}>{TYPE_LABELS[type] || type}</div>
            <table className="data-table">
              <tbody>
                {rows.map((a) => (
                  <tr key={a.code}>
                    <td>{a.name}</td>
                    <td className="num">{formatMoney(a.balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  );
}
