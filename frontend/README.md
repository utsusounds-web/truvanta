# Truvanta — Frontend

React + TypeScript (Vite) frontend for Truvanta.

## Setup
```bash
npm install
cp .env.example .env   # points at http://localhost:8000/api by default
npm run dev
```

## Running tests
```bash
npm test          # run once
npm run test:watch  # watch mode
```
Covers `lib/format.ts` (error-message extraction for every failure mode —
network down, timeout, wrong credentials, validation errors) and `AuthPage`
(registration validation, password confirmation, mode switching) via Vitest
+ React Testing Library.

See `../RUNNING.md` at the project root for running frontend + backend together.

## Screens implemented
- **Auth** — register (first/last name, username, email, password + verify-password
  confirmation, show/hide password toggle) / sign in (JWT). Shows a live backend
  connectivity banner on load if the API can't be reached, before you even submit.
- **Onboarding** — business basics, contact/location, branding (logo upload)
  with a live receipt preview
- **Dashboard** — sales/stock/debt stats, business health, risk alerts, recent
  sensitive activity
- **Point of Sale** — product search, cart, cash/credit checkout, branded
  PDF receipt, automatic tax calculation, offline queueing
- **Products** — list + add (with on-the-fly unit-of-measure creation),
  per-product gain/loss and margin shown inline, an "Update cost price"
  flow that suggests a rebalanced selling price, and photo upload/editing
- **Inventory** — stock levels, movement history, manual stock adjustments
  (offline-capable)
- **Shifts** — open with a cash count, close with a blind count
- **Customers** — list, add, credit ledger, record payments
- **Suppliers** — list, add, outstanding balances
- **Purchase Orders** — create with line items, receive goods with
  discrepancy tracking
- **Expenses** — record, approve/reject
- **Returns & Refunds** — record against a recent sale, approve
- **Branch Transfers** — send stock between branches, confirm receipt
- **Quick Stock Audit** — trigger a random spot-check, enter counts, see
  discrepancies and their estimated value
- **Document Vault** — upload and browse supplier invoices, receipts, and
  other supporting documents
- **Reports** — "Where Did My Money Go?", full sales list with cancellation,
  and a Profitability section
- **Notifications** — history of alerts with per-channel delivery status
- **Staff & Roles** — create roles, assign granular permissions, add/revoke
  staff
- **Settings** — alert delivery (WhatsApp/email), your own Paystack keys,
  Owner Away Mode thresholds, default tax rate, AI add-on status, and
  (staff-only) platform-wide integration credentials
- **My Profile** — name and photo
- **Forgot/Reset Password** — standard email-link based password recovery
- **Receipt History** — every print/reprint across the business, reprints flagged
- **Payment Reconciliation** — bank transfer/card/other payments matched against
  a bank statement; cash is confirmed automatically
- **Verify** (public) — receipt authenticity check, the QR-code destination

## Not yet built
Role/permission UI is complete; still missing: multi-branch UI polish beyond
transfers, receipt reprint history browser, PWA installability, offline
queueing for anything beyond sales/stock movements, and any AI features.

## Architecture notes
- `src/api/client.ts` — axios instance that attaches the JWT and the active
  `X-Business-ID` header to every request automatically.
- `src/context/AuthContext.tsx` — session state (login/register/me).
- `src/context/BusinessContext.tsx` — active business/branch selection.
- `src/api/resources.ts` — typed functions for every backend endpoint used.
- Design tokens live in `src/styles/tokens.css`; shared table/card/badge
  styles in `src/styles/shared.css`.
