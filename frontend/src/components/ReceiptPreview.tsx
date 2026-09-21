import type { OnboardingFormState } from "../types/business";
import { currencySymbol } from "../types/business";
import "./ReceiptPreview.css";

const SAMPLE_ITEMS = [
  { name: "Rice (5kg bag)", qty: 1, price: 8500 },
  { name: "Cooking Oil (1L)", qty: 2, price: 2300 },
  { name: "Sugar (500g)", qty: 3, price: 650 },
];

export default function ReceiptPreview({ form }: { form: OnboardingFormState }) {
  const symbol = currencySymbol(form.currency_code);
  const subtotal = SAMPLE_ITEMS.reduce((sum, i) => sum + i.qty * i.price, 0);

  return (
    <div className="receipt-preview-wrap">
      <div className="receipt-preview-label">Live preview — this is what your customers will see</div>
      <div className="receipt-paper">
        <div className="receipt-perf" aria-hidden="true" />
        <div className="receipt-body">
          <div className="receipt-logo-slot">
            {form.logoPreviewUrl ? (
              <img src={form.logoPreviewUrl} alt="Business logo" />
            ) : (
              <div className="receipt-logo-placeholder">LOGO</div>
            )}
          </div>

          <div className="receipt-business-name">{form.name || "Your Business Name"}</div>
          {form.address && <div className="receipt-line muted">{form.address}</div>}
          {form.phone_number && <div className="receipt-line muted">{form.phone_number}</div>}
          {form.receipt_header_note && <div className="receipt-line muted">{form.receipt_header_note}</div>}

          <div className="receipt-divider" />

          <div className="receipt-meta">
            <span>Receipt: SL-A1B2C3D4E5</span>
            <span>{new Date().toLocaleString()}</span>
          </div>

          <div className="receipt-divider" />

          <table className="receipt-items">
            <thead>
              <tr><th>Item</th><th className="num">Total</th></tr>
            </thead>
            <tbody>
              {SAMPLE_ITEMS.map((i) => (
                <tr key={i.name}>
                  <td>{i.name} x{i.qty}</td>
                  <td className="num">{symbol}{(i.qty * i.price).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="receipt-divider" />

          <div className="receipt-total-row">
            <span>TOTAL</span>
            <span>{symbol}{subtotal.toLocaleString()}</span>
          </div>

          <div className="receipt-qr" aria-hidden="true">
            <svg viewBox="0 0 60 60" width="46" height="46">
              <rect width="60" height="60" fill="none" />
              {Array.from({ length: 8 }).map((_, r) =>
                Array.from({ length: 8 }).map((_, c) =>
                  (r + c) % 3 === 0 ? (
                    <rect key={`${r}-${c}`} x={c * 7.5} y={r * 7.5} width="7" height="7" fill="var(--ink-900)" />
                  ) : null
                )
              )}
            </svg>
          </div>

          {form.receipt_footer_note && <div className="receipt-footer">{form.receipt_footer_note}</div>}
        </div>
      </div>
    </div>
  );
}
