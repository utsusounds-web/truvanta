from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.permissions import IsPlatformAdmin
from apps.core.permissions import IsBusinessMember
from .models import BackupLog
from .serializers import BackupLogSerializer


class LatestBackupView(APIView):
    """Powers the 'last backed up' indicator in Platform Admin — so
    whoever runs the deployment never has to just hope the cron job
    they set up is actually working."""
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        latest = BackupLog.objects.first()
        if not latest:
            return Response({"detail": "No backups recorded yet."}, status=404)
        return Response(BackupLogSerializer(latest).data)


class GlobalSearchView(APIView):
    """One search box across the things a business actually looks up
    day to day — products, customers, suppliers, and a specific sale
    by its receipt number — instead of scrolling a list that only gets
    longer as the business grows. Every query is scoped to the
    caller's own business; nothing here ever crosses tenants.
    """
    permission_classes = [IsBusinessMember]

    def get(self, request):
        from apps.products.models import Product
        from apps.customers.models import Customer
        from apps.suppliers.models import Supplier
        from apps.sales.models import Sale

        query = (request.query_params.get("q") or "").strip()
        if len(query) < 2:
            return Response({"results": []})

        business_id = request.business_id
        limit = 6  # per category — this is a jump-to lookup, not a full report

        results = []

        products = Product.objects.filter(business_id=business_id).filter(
            _search_q(query, "name", "sku", "barcode")
        )[:limit]
        for p in products:
            results.append({
                "type": "product", "id": str(p.id), "label": p.name,
                "sublabel": p.sku or p.barcode or "", "path": "/products",
            })

        customers = Customer.objects.filter(business_id=business_id).filter(
            _search_q(query, "name", "phone_number", "email")
        )[:limit]
        for c in customers:
            results.append({
                "type": "customer", "id": str(c.id), "label": c.name,
                "sublabel": c.phone_number or c.email or "", "path": "/customers",
            })

        suppliers = Supplier.objects.filter(business_id=business_id).filter(
            _search_q(query, "name", "phone_number", "email")
        )[:limit]
        for s in suppliers:
            results.append({
                "type": "supplier", "id": str(s.id), "label": s.name,
                "sublabel": s.phone_number or s.email or "", "path": "/suppliers",
            })

        sales = Sale.objects.filter(business_id=business_id, transaction_number__icontains=query)[:limit]
        for sale in sales:
            results.append({
                "type": "sale", "id": str(sale.id), "label": f"Sale {sale.transaction_number}",
                "sublabel": sale.created_at.strftime("%d %b %Y") if getattr(sale, "created_at", None) else "",
                "path": "/receipt-history",
            })

        return Response({"results": results})


def _search_q(query, *fields):
    from django.db.models import Q
    q = Q()
    for f in fields:
        q |= Q(**{f"{f}__icontains": query})
    return q
