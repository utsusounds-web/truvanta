# Truvanta — Backend

Django + Django REST Framework backend for Truvanta, a multi-tenant
POS / inventory / cash-control platform for small businesses ("Smart
Business Operating System").

## Stack
- Python 3.12, Django 6, Django REST Framework
- SQLite for local/dev (zero setup), PostgreSQL for production
- JWT auth (SimpleJWT)
- reportlab + qrcode for branded receipt PDFs

## Setup (Windows, macOS, Linux)

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # edit as needed; sqlite works out of the box
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API is served at `http://localhost:8000/api/`. Admin at `/admin/`.

## Switching to PostgreSQL (production)
In `.env`:
```
DB_ENGINE=postgres
DB_NAME=sbos
DB_USER=sbos
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```
Then `pip install psycopg2-binary` (already in requirements.txt) and re-run `migrate`.

## Running tests
```bash
python manage.py test tests
```
Covers: tenant isolation, sale posting (inventory deduction, credit ledger,
cancellation reversal, receipt reprint tracking), blind-count shift
reconciliation, audit-log immutability, receipt PDF generation, report
calculations, and rule-based risk detection.

## API shape
Every business-data endpoint requires:
- `Authorization: Bearer <jwt>` (get one from `POST /api/auth/login/`)
- `X-Business-ID: <business uuid>` header — identifies which tenant you're
  acting in; the user must have an active Membership in it.

Key endpoints:
- `POST /api/auth/register/`, `POST /api/auth/login/`, `GET /api/auth/me/`
- `POST /api/tenants/businesses/` — onboarding: creates Business + Owner
  role/membership + default branch in one call. Accepts multipart form data
  so the logo can be uploaded at creation time.
- `PATCH /api/tenants/businesses/<id>/` — update branding (logo, name,
  address, phone, receipt footer) — used everywhere via `Business.branding_context`.
- `GET/POST /api/products/`, `/api/stock-movements/`, `/api/stock-levels/`
- `POST /api/sales/` — post a sale (see payload shape in `apps/sales/serializers.py`)
- `POST /api/sales/<id>/cancel/`, `POST /api/sales/<id>/reprint_receipt/`,
  `GET /api/sales/<id>/receipt-pdf/` — branded PDF receipt, marks REPRINT if applicable
- `POST /api/shifts/` (open), `POST /api/shifts/<id>/close/` (blind-count close)
- `GET /api/reports/owner-dashboard/`, `/api/reports/where-did-my-money-go/`,
  `/api/reports/business-health/`, `/api/reports/risk-alerts/`
- `POST /api/products/<id>/suggest-price/?new_cost_price=X` — preview a
  rebalanced selling price that preserves the product's current margin
- `POST /api/products/<id>/update-cost-price/` — apply a new cost (and
  optionally selling) price; records `PriceHistory` + audit log
- `GET /api/reports/inventory-profitability/` — shop-wide cost/retail value,
  potential profit, products currently sold at a loss, and old stock (no
  sale in 30+ days) worth a price review
- `GET/POST /api/auth/roles/`, `/api/auth/memberships/`, `POST /api/auth/staff/invite/`
  — staff & role/permission management
- `GET/POST /api/stock-transfers/`, `POST /api/stock-transfers/<id>/receive/`
  — branch-to-branch transfers with discrepancy tracking
- `GET/POST /api/purchase-orders/`, `/api/purchase-order-items/`,
  `POST /api/purchase-orders/<id>/receive/` — full PO → goods-receipt flow
- `GET/POST /api/documents/` — Document Vault
- `GET/POST /api/quick-audits/`, `POST /api/quick-audits/<id>/record_counts/`
  — Quick Random Stock Audit
- `GET /api/verify/<sale_id>/` — public receipt verification (QR code target)
- `GET/PATCH /api/platform-settings/` — staff-only deployment-wide integration
  credentials (WhatsApp, Gmail, platform Paystack)
- `PATCH /api/auth/me/` — update own profile (name, phone, photo)
- `POST /api/auth/password-reset/`, `POST /api/auth/password-reset/confirm/` —
  standard token-based password reset (email link, single-use, expires)
- `GET /api/sales/export-csv/`, `GET /api/reports/inventory-profitability/?export=csv`,
  `GET /api/reports/owner-dashboard/?export=csv` — CSV exports
- `GET /api/receipt-print-logs/` — every receipt print/reprint across the business
- `GET /api/payment-reconciliation/`, `POST /api/payment-reconciliation/<id>/set_status/`
  — reconcile bank transfer/card/other payments against a bank statement
  (pending → confirmed/reconciled/unmatched/disputed); cash is auto-confirmed
- `POST /api/notifications/check-overdue-debts/`, `POST /api/notifications/send-daily-summary/`
  — on-demand notification triggers; `python manage.py check_notifications` runs both
  for every active business (point a cron job at this for automatic scheduling)

## Architecture notes
- Every tenant-owned model inherits `TenantScopedModel` (UUID pk + `business` FK).
- Inventory: `StockMovement` is the only source of truth (append-only,
  enforced in `save()`); `StockLevel` is a derived cache, never written directly.
- Financial/audit records (`AuditLog`, `StockMovement`) are immutable —
  corrections are new, linked reversing records, never edits.
- Business logic that spans multiple models lives in each app's
  `services.py`, not in views — views only translate HTTP <-> service calls.
- Branding (logo/name/address/receipt footer) lives once on `Business`
  (with per-branch override) and is read via `.branding_context` by every
  document generator — see `apps/sales/documents.py`.

## Deploying to production
Before going live: `python -c "import secrets; print(secrets.token_urlsafe(50))"`
and put that in `SECRET_KEY` in `.env`, set `DEBUG=False`, and set `ALLOWED_HOSTS`
to your real domain. With `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE`, and HSTS all switch on automatically (override any of them in
`.env` if you terminate SSL somewhere Django can't see, like behind a load balancer).
Run `python manage.py check --deploy` to confirm.

## Not yet implemented
Offline-first sync covers Sales and Stock Movements only (other actions — expenses,
customer payments — don't queue offline yet). AI features (voice bookkeeping, receipt
scanning, "ask my business"), hardware integrations (printers/scanners/cash drawers),
real Paystack checkout/webhooks (keys can be saved via Settings, but nothing collects
payment yet), CSV/Excel export of reports, bank/payment reconciliation status tracking,
multi-currency conversion — models and audit hooks are in place to build on.
