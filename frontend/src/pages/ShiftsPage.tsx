import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { useBusiness } from "../context/BusinessContext";
import { getShifts, openShift as openShiftApi, closeShift as closeShiftApi, fetchShiftClosingPdfUrl } from "../api/resources";
import type { Shift } from "../api/types";
import { formatMoney, formatDate, extractErrorMessage } from "../lib/format";

export default function ShiftsPage() {
  const { activeBranchId } = useBusiness();
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [showOpenModal, setShowOpenModal] = useState(false);
  const [openingCash, setOpeningCash] = useState("");
  const [closingShift, setClosingShift] = useState<Shift | null>(null);
  const [physicalCash, setPhysicalCash] = useState("");
  const [closedResult, setClosedResult] = useState<Shift | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  const [openShift, setOpenShift] = useState<Shift | null>(null);

  function refresh() {
    if (!activeBranchId) return;
    setLoading(true);
    Promise.all([
      getShifts({ branch: activeBranchId }),
      getShifts({ branch: activeBranchId, status: "open" }),
    ]).then(([all, open]) => {
      setShifts(all);
      setOpenShift(open[0] || null);
    }).finally(() => setLoading(false));
  }
  useEffect(refresh, [activeBranchId]);

  const openOne = openShift;

  async function handleOpen() {
    if (!activeBranchId || !openingCash) return;
    setSubmitting(true); setError(null);
    try {
      await openShiftApi(activeBranchId, parseFloat(openingCash));
      setShowOpenModal(false);
      setOpeningCash("");
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't open the shift."));
    } finally { setSubmitting(false); }
  }

  async function handleClose() {
    if (!closingShift || !physicalCash) return;
    setSubmitting(true); setError(null);
    try {
      const result = await closeShiftApi(closingShift.id, parseFloat(physicalCash));
      setClosingShift(null);
      setPhysicalCash("");
      setClosedResult(result);
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't close the shift."));
    } finally { setSubmitting(false); }
  }

  return (
    <div>
      <PageHeader
        title="Shifts"
        subtitle="Open with a cash count, close with a blind count — the system tells you what to expect only after you enter what's physically there."
        actions={openOne
          ? <button className="btn btn-primary" onClick={() => setClosingShift(openOne)}>Close shift</button>
          : <button className="btn btn-primary" onClick={() => setShowOpenModal(true)}>Open shift</button>}
        vaultAccent
      />

      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : shifts.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No shifts yet" subtitle="Open one before taking sales for accurate cash control." /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Opened</th><th className="num">Opening cash</th><th className="num">Expected</th><th className="num">Physical</th><th className="num">Variance</th><th>Result</th><th></th></tr></thead>
            <tbody>
              {shifts.map((s) => (
                <tr key={s.id}>
                  <td>{formatDate(s.opened_at)}</td>
                  <td className="num">{formatMoney(s.opening_cash)}</td>
                  <td className="num">{s.expected_closing_cash ? formatMoney(s.expected_closing_cash) : "—"}</td>
                  <td className="num">{s.closing_physical_cash ? formatMoney(s.closing_physical_cash) : "—"}</td>
                  <td className="num">{s.variance ? formatMoney(s.variance) : "—"}</td>
                  <td>{s.result ? <span className={`badge badge--${s.result}`}>{s.result.replace(/_/g, " ")}</span> : <span className="badge badge--attention">open</span>}</td>
                  <td>{s.closed_at && <button className="btn btn-ghost" onClick={async () => window.open(await fetchShiftClosingPdfUrl(s.id), "_blank")}>Report</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showOpenModal && (
        <Modal title="Open shift" onClose={() => setShowOpenModal(false)}>
          <Field label="Opening cash" required hint="Count the cash drawer before your first sale">
            <input className="input" type="number" min={0} value={openingCash} onChange={(e) => setOpeningCash(e.target.value)} autoFocus />
          </Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleOpen} disabled={submitting}>
            {submitting ? "Opening…" : "Open shift"}
          </button>
        </Modal>
      )}

      {closingShift && (
        <Modal title="Close shift — blind count" onClose={() => setClosingShift(null)}>
          <p style={{ fontSize: 15.5, color: "var(--ink-600)", marginBottom: 18 }}>
            Count the physical cash in the drawer right now and enter it below. The expected amount is only revealed after you submit — this keeps the count honest.
          </p>
          <Field label="Physical cash counted" required>
            <input className="input" type="number" min={0} value={physicalCash} onChange={(e) => setPhysicalCash(e.target.value)} autoFocus />
          </Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleClose} disabled={submitting}>
            {submitting ? "Closing…" : "Submit count"}
          </button>
        </Modal>
      )}

      {closedResult && (
        <Modal title="Shift closed" onClose={() => setClosedResult(null)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 16 }}>
            <Row label="Expected cash" value={formatMoney(closedResult.expected_closing_cash || "0")} />
            <Row label="Physical cash" value={formatMoney(closedResult.closing_physical_cash || "0")} />
            <Row label="Variance" value={formatMoney(closedResult.variance || "0")} />
            <div style={{ marginTop: 8 }}>
              <span className={`badge badge--${closedResult.result}`}>{closedResult.result.replace(/_/g, " ")}</span>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--ink-600)" }}>{label}</span><strong>{value}</strong></div>;
}
