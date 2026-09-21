from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/tenants/", include("apps.tenants.urls")),
    path("api/", include("apps.products.urls")),
    path("api/", include("apps.inventory.urls")),
    path("api/", include("apps.sales.urls")),
    path("api/", include("apps.customers.urls")),
    path("api/", include("apps.suppliers.urls")),
    path("api/", include("apps.expenses.urls")),
    path("api/", include("apps.shifts.urls")),
    path("api/", include("apps.returns.urls")),
    path("api/", include("apps.notifications.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/", include("apps.stock_audit.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/billing/", include("apps.billing.urls")),
    path("api/", include("apps.core.urls")),
    path("api/ledger/", include("apps.ledger.urls")),
    path("api/", include("apps.quotations.urls")),
    path("api/", include("apps.loan_readiness.urls")),
    path("api/", include("apps.cashflow.urls")),
    path("api/", include("apps.continuity.urls")),
]

# Media (user-uploaded product photos, business/branch logos, expense
# receipts, vault documents) is served unconditionally, not just in
# DEBUG. Whitenoise (see MIDDLEWARE) only serves STATIC_ROOT, never
# MEDIA_ROOT — so without this, every uploaded image 404s in
# production the moment DEBUG=False, even though a reverse proxy in
# front of this (nginx, docker-compose, etc.) would correctly expect
# something here to answer. Serving media through gunicorn is a
# reasonable choice at this scale (small-business POS, not high-
# traffic media hosting); if that changes, swap MEDIA storage for
# S3/object storage instead of re-adding a DEBUG gate here.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

