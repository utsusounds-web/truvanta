from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsOwnerOrAdmin
from apps.billing.permissions import IsPlatformAdmin
from .models import AuditLog
from .serializers import AuditLogSerializer
from . import staff_integrity


class AdminAuditLogListView(generics.ListAPIView):
    """Platform staff only: the audit trail across every business, not
    just one — for spotting patterns or investigating a report that
    spans tenants. Every business's own AuditLogListView above stays
    exactly as strict as before; this is a separate, additional view,
    not a loosening of it."""
    permission_classes = [IsPlatformAdmin]
    serializer_class = AuditLogSerializer
    filterset_fields = ["action", "business", "actor"]

    def get_queryset(self):
        return AuditLog.objects.select_related(
            "actor", "branch", "business", "content_type",
        ).order_by("-created_at")


class AuditLogListView(generics.ListAPIView):
    """The business's security/activity trail — price changes,
    discounts, refunds, cancellations, stock adjustments, permission
    changes, logins, receipt reprints, shift events. Read-only: the
    model itself refuses updates/deletes (see AuditLog.save/delete),
    this view just adds the same guarantee on the read side.

    Owner/admin only rather than gated by a granular permission code:
    this includes login and permission-change history, which is
    security data even a trusted staff member with financial-view
    access shouldn't necessarily see about their colleagues."""
    permission_classes = [IsOwnerOrAdmin]
    serializer_class = AuditLogSerializer
    filterset_fields = ["action", "branch", "actor"]

    def get_queryset(self):
        qs = AuditLog.objects.filter(business_id=self.request.business_id).select_related(
            "actor", "branch", "content_type")
        accessible = self.request.accessible_branch_ids
        if accessible is not None:
            qs = qs.filter(branch_id__in=accessible)
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)
        return qs


class StaffIntegrityView(APIView):
    """Private, owner/admin-only view of each staff member's
    exception rate against the business's own average — see
    staff_integrity.py for why this is deliberately not a punitive
    single-number 'score'."""
    permission_classes = [IsOwnerOrAdmin]

    def get(self, request):
        from apps.tenants.models import Business, Branch
        business = Business.objects.get(pk=request.business_id)
        branch = None
        if request.query_params.get("branch"):
            branch = Branch.objects.get(pk=request.query_params["branch"], business=business)
        return Response(staff_integrity.staff_integrity_summary(business=business, branch=branch))
