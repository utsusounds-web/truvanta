import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import { getReceiptPrintLogs, fetchReceiptPdfUrl, fetchInvoicePdfUrl } from "../api/resources";
import type { ReceiptPrintLogEntry } from "../api/types";
import { formatDate } from "../lib/format";

export default function ReceiptHistoryPage() {
  const [logs, setLogs] = useState<ReceiptPrintLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [openingId, setOpeningId] = useState<string | null>(null);

  useEffect(() => {
    getReceiptPrintLogs().then(setLogs).finally(() => setLoading(false));
  }, []);

  async function handleOpen(saleId: string, kind: "receipt" | "invoice") {
    setOpeningId(saleId + kind);
    try {
      const url = kind === "receipt" ? await fetchReceiptPdfUrl(saleId, true) : await fetchInvoicePdfUrl(saleId);
      window.open(url, "_blank");
    } finally {
      setOpeningId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Receipt History"
        subtitle="Every time a receipt was printed or reprinted — reprints are always flagged, never silent. Reprint a receipt or pull the formal invoice for any past sale here, any time — not just right after checkout."
      />
      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : logs.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No receipts printed yet" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Receipt #</th><th>Branch</th><th>Printed by</th><th className="num">Copy #</th><th>When</th><th></th></tr></thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: 14.5 }}>{l.transaction_number}</td>
                  <td>{l.branch_name}</td>
                  <td>{l.printed_by_email || "—"}</td>
                  <td className="num">
                    {l.copy_number}
                    {l.copy_number > 1 && <span className="badge badge--attention" style={{ marginLeft: 8 }}>reprint</span>}
                  </td>
                  <td>{formatDate(l.created_at)}</td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    <button className="btn btn-ghost" disabled={openingId === l.sale_id + "receipt"} onClick={() => handleOpen(l.sale_id, "receipt")}>
                      Receipt
                    </button>{" "}
                    <button className="btn btn-ghost" disabled={openingId === l.sale_id + "invoice"} onClick={() => handleOpen(l.sale_id, "invoice")}>
                      Invoice
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
