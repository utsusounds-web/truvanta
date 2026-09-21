from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from apps.core.permissions import IsBusinessMember


class TenantScopedModelViewSet(viewsets.ModelViewSet):
    """Base for any ViewSet on a TenantScopedModel. Filters every
    queryset to request.business_id (set by IsBusinessMember) and
    stamps new objects with that business — this is what makes tenant
    isolation automatic instead of something each view must remember.
    """

    permission_classes = [IsBusinessMember]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(business_id=self.request.business_id)

    def perform_create(self, serializer):
        serializer.save(business_id=self.request.business_id)


class BranchScopedModelViewSet(TenantScopedModelViewSet):
    """For any ViewSet on a model with a direct `branch` FK (Sales,
    Shifts, StockMovement, Returns, PurchaseOrders, etc.). Restricts
    both reads and writes to the branches the requesting membership
    can actually access — a staff member scoped to one branch can't
    see or touch another branch's records through the API, even by
    guessing an ID or passing a different `branch` value directly.

    request.accessible_branch_ids is set by IsBusinessMember: None
    means "every branch of this business" (owner/admin, or any
    membership with no branch restriction); otherwise a set of
    specific branch ids, already widened to include mini branches of
    an accessible main branch.
    """

    branch_field = "branch"

    def get_queryset(self):
        qs = super().get_queryset()
        accessible = self.request.accessible_branch_ids
        if accessible is None:
            return qs
        from django.db.models import Q

        field = self.branch_field
        # isnull=True included so business-wide records (a nullable
        # branch FK left blank) stay visible to everyone rather than
        # disappearing for branch-restricted staff.
        return qs.filter(Q(**{f"{field}_id__in": accessible}) | Q(**{f"{field}_id__isnull": True}))

    def perform_create(self, serializer):
        branch = serializer.validated_data.get(self.branch_field)
        self._check_branch_access(branch)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        branch = serializer.validated_data.get(self.branch_field, getattr(serializer.instance, self.branch_field))
        self._check_branch_access(branch)
        super().perform_update(serializer)

    def _check_branch_access(self, branch):
        accessible = self.request.accessible_branch_ids
        if accessible is None or branch is None:
            return
        branch_id = branch.id if hasattr(branch, "id") else branch
        if branch_id not in accessible:
            raise PermissionDenied("You don't have access to that branch.")
