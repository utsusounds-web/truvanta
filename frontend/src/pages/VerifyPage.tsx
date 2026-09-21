import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { verifySale } from "../api/resources";
import type { SaleVerification } from "../api/types";
import { formatMoney } from "../lib/format";
import "./VerifyPage.css";

export default function VerifyPage() {
  const { saleId } = useParams<{ saleId: string }>();
  const [result, setResult] = useState<SaleVerification | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!saleId) return;
    verifySale(saleId).then(setResult).catch(() => setResult({ valid: false })).finally(() => setLoading(false));
  }, [saleId]);

  return (
    <div className="verify-shell">
      <div className="verify-card">
        <div className="auth-mark">TRUVANTA</div>
        {loading ? (
          <p className="verify-status">Checking…</p>
        ) : result?.valid ? (
          <>
            <div className="verify-badge verify-badge--valid">✓ Genuine receipt</div>
            <dl className="verify-details">
              <div><dt>Business</dt><dd>{result.business_name}</dd></div>
              <div><dt>Branch</dt><dd>{result.branch_name}</dd></div>
              <div><dt>Receipt #</dt><dd>{result.transaction_number}</dd></div>
              <div><dt>Date</dt><dd>{result.date}</dd></div>
              <div><dt>Total</dt><dd>{formatMoney(result.grand_total || "0", result.currency)}</dd></div>
              <div><dt>Status</dt><dd style={{ textTransform: "capitalize" }}>{result.status}</dd></div>
            </dl>
          </>
        ) : (
          <>
            <div className="verify-badge verify-badge--invalid">✕ Not found</div>
            <p className="verify-status">This receipt couldn't be verified — it may be invalid or the link is incorrect.</p>
          </>
        )}
      </div>
    </div>
  );
}
