import { useState } from "react";
import PageHeader from "../components/PageHeader";
import FeatureTour from "../components/FeatureTour";

const SECTIONS: { title: string; body: React.ReactNode }[] = [
  {
    title: "Getting started",
    body: (
      <>
        <p><strong>Creating your account:</strong> tap "Create account," fill in your name, email,
          a password, and a username (just for signing in — pick anything, like your shop's name).
          You'll then set up your business — name, currency, address — once, the first time only.</p>
        <p><strong>Signing in later:</strong> just email and password. You'll land straight back on
          your dashboard with everything exactly as you left it.</p>
      </>
    ),
  },
  {
    title: "Your daily rhythm",
    body: (
      <ol>
        <li><strong>Open a shift</strong> (Shifts page) — count the cash in your drawer, enter it, tap "Open shift."</li>
        <li><strong>Sell things</strong> (Point of Sale) — add items to the cart, take payment, print or share the receipt.</li>
        <li><strong>Close your shift</strong> at day's end — count your cash again; the app tells you if it matches what it expects.</li>
      </ol>
    ),
  },
  {
    title: "Products & Inventory",
    body: (
      <>
        <p><strong>Adding a product:</strong> Products → Add product — name, price, unit. Photo optional.</p>
        <p><strong>Adding many at once:</strong> Products → Bulk add opens a table — fill in a row per product, save them all together.</p>
        <p><strong>Recording stock movement:</strong> Inventory → Record movement. Pick the reason —
          Stock Purchase (restocking), Customer Return, Damage/Expiry, Personal Use, Supplier Return,
          or Stock Adjustment — the app adds or subtracts automatically based on which you choose.</p>
        <p><strong>Low stock warnings:</strong> set a reorder level per product; it flags on the
          Inventory page once stock drops to or below that number.</p>
      </>
    ),
  },
  {
    title: "Selling (POS)",
    body: (
      <>
        <p>Search or tap products into the cart, adjust quantities, choose how they're paying —
          cash, transfer, card, or on credit. If paid in a foreign currency, tick that box, pick the
          currency, and enter what they handed over — it converts automatically using the rate set in Settings.</p>
        <p><strong>Walk-in / one-time customers:</strong> you never have to enter a name. Leave the
          customer field blank and complete the sale as normal — every sale gets a unique receipt code
          automatically, shown right on the "Sale completed" screen and printed on the receipt. That
          code alone is enough to find the sale again later (see Returns, below).</p>
        <p><strong>No internet?</strong> The app keeps working — sales save on your device and sync
          automatically once you're back online. Nothing is lost.</p>
      </>
    ),
  },
  {
    title: "Customers & credit",
    body: <p>Add customers under Customers. Sales "on credit" add to their running balance — see who
      owes you what at a glance, and record payments as they pay you back.</p>,
  },
  {
    title: "Returns & Refunds",
    body: (
      <p>Returns → Record return. Have a receipt but no customer name to search by? Use "Find by
        receipt code" and type or paste the code from the receipt (e.g. <code>SL-7F2A91C0B3</code>) —
        this works for every sale, walk-in or regular customer alike. Otherwise pick from the list of
        recent sales. Choose the item, the reason, and whether it's a return, refund, exchange, damaged,
        or expired — approval (if required) happens from the same page.</p>
    ),
  },
  {
    title: "Statements",
    body: <p>Need a formal record to send an accountant, a lender, or a customer? Statements → pick a
      type (Sales, Expenses, a specific Customer's account, Ledger, or Profitability), choose a date
      range, and download it as a CSV you can open in Excel or Google Sheets.</p>,
  },
  {
    title: "Suppliers & Purchase Orders",
    body: <p>Track who you buy from under Suppliers. Create a Purchase Order when ordering stock,
      mark it "received" when it arrives — this adds the stock and updates what you owe that supplier.</p>,
  },
  {
    title: "Expenses & money out",
    body: <p>Record anything you spend under Expenses — this is what makes your profit numbers
      accurate. Made a mistake? Void it with a reason instead of deleting — nothing is ever silently removed.</p>,
  },
  {
    title: "Staff & Roles",
    body: <p>Invite staff under Staff & Roles. Each person gets a role (Owner, Manager, Cashier) that
      controls what they can see and do.</p>,
  },
  {
    title: "Reports, Dashboard & Ledger",
    body: <p>The dashboard shows sales, profit, and warning signs at a glance. Deeper reports are
      under Reports, exportable as CSV. The Ledger page shows the formal double-entry record behind
      every sale, expense, and withdrawal — kept in balance automatically, for anyone who wants the
      full accounting view. (Both need the "view profit" permission — ask an owner or admin if a
      page looks restricted.)</p>,
  },
  {
    title: "Activity Log",
    body: <p>Owners and admins can see a full history of sensitive actions under Activity Log —
      price changes, discounts, refunds, cancellations, stock adjustments, permission changes, logins,
      and receipt reprints. Nothing in it can ever be edited or deleted, so it's always a true record
      of what happened. Filter by action type or date, and tap "Details" on any entry to see exactly
      what changed.</p>,
  },
  {
    title: "Owner Away Mode",
    body: <p>Not physically at the shop? Turn on Away Mode (Settings) and set thresholds — e.g.
      "alert me on any discount over 10%." You get notified the moment something crosses that line.</p>,
  },
  {
    title: "Your Profile & Security",
    body: <>
      <p>Under Profile, update your name and photo, see every device you're signed into, and sign
        any of them out remotely if you lose your phone or suspect someone else is using your account.</p>
      <p><strong>Two-factor authentication:</strong> also under Profile — adds a 6-digit code step to
        signing in, using any authenticator app, so a stolen password alone isn't enough to get in.</p>
    </>,
  },
  {
    title: "What's not finished yet",
    body: (
      <ul>
        <li>AI features (voice bookkeeping, receipt scanning) — not built yet.</li>
        <li>Dedicated hardware (receipt printers, barcode scanners) — not verified against real devices.</li>
        <li>WhatsApp/Email notifications — built, but need real credentials entered in Settings before they'll actually send.</li>
      </ul>
    ),
  },
];

export default function HelpPage() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  const [showTour, setShowTour] = useState(false);

  return (
    <div>
      <PageHeader title="Help & User Manual" subtitle="Everything you need to know, in plain language — no computer background required." />
      <div className="card" style={{ padding: 16, marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <div>
          <strong style={{ fontSize: 16 }}>New here, or just want a refresher?</strong>
          <p style={{ fontSize: 15, color: "var(--ink-600)", margin: "2px 0 0" }}>
            A 30-second walkthrough of where everything lives.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowTour(true)}>Take the tour</button>
      </div>
      {showTour && <FeatureTour onClose={() => setShowTour(false)} />}
      {SECTIONS.map((section, i) => (
        <div key={section.title} className="card" style={{ padding: 0, marginBottom: 12, overflow: "hidden" }}>
          <button
            onClick={() => setOpenIndex(openIndex === i ? null : i)}
            style={{
              width: "100%", textAlign: "left", padding: "16px 20px", background: "none", border: "none",
              cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center",
              fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 16.5,
            }}
          >
            {section.title}
            <span style={{ color: "var(--ink-300)" }}>{openIndex === i ? "−" : "+"}</span>
          </button>
          {openIndex === i && (
            <div style={{ padding: "0 20px 20px", fontSize: 15.5, color: "var(--ink-800)", lineHeight: 1.6 }}>
              {section.body}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
