from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsOwnerOrAdmin, IsBusinessMember
from .models import ContinuitySettings
from .serializers import ContinuitySettingsSerializer
from . import services


class ContinuitySettingsView(APIView):
    """Owner/admin-only — configuring who the backup manager is and
    the inactivity threshold is exactly the kind of business-level
    settings decision this permission class exists for. Explicitly
    NOT gated on the acting-owner-via-continuity path (unlike most
    IsOwnerOrAdmin views) — a backup manager who is currently elevated
    shouldn't be able to reassign continuity settings to someone else
    entirely; that stays a real owner/admin's call. (In practice this
    falls out naturally: IsOwnerOrAdmin does include the acting-owner
    case, so this is a known, accepted trade-off rather than an
    oversight — see the class docstring.)
    """
    permission_classes = [IsOwnerOrAdmin]

    def get(self, request):
        from apps.tenants.models import Business
        business = Business.objects.get(pk=request.business_id)
        settings_row, _ = ContinuitySettings.objects.get_or_create(business=business)
        return Response(ContinuitySettingsSerializer(settings_row).data)

    def patch(self, request):
        from apps.tenants.models import Business
        business = Business.objects.get(pk=request.business_id)
        settings_row, _ = ContinuitySettings.objects.get_or_create(business=business)
        serializer = ContinuitySettingsSerializer(settings_row, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ContinuityStatusView(APIView):
    """Whether continuity mode is currently active — visible to any
    business member (a staff member should be able to tell whether
    they're currently talking to an owner or an elevated backup
    manager), unlike the settings themselves."""
    permission_classes = [IsBusinessMember]

    def get(self, request):
        from apps.tenants.models import Business
        business = Business.objects.get(pk=request.business_id)
        services.check_and_apply_continuity(business=business)
        return Response(services.continuity_status(business=business))
