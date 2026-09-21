from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.billing.permissions import HasFeature
from apps.core.viewsets import BranchScopedModelViewSet
from .models import VaultDocument
from .serializers import VaultDocumentSerializer


class RequireDocumentVault(HasFeature):
    required_feature_key = "document_vault"


class VaultDocumentViewSet(BranchScopedModelViewSet):
    permission_classes = [RequireDocumentVault]
    queryset = VaultDocument.objects.all()
    serializer_class = VaultDocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["category", "branch"]
    search_fields = ["title", "note"]

    def perform_create(self, serializer):
        branch = serializer.validated_data.get("branch")
        self._check_branch_access(branch)
        serializer.save(business_id=self.request.business_id, uploaded_by=self.request.user)
