from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from apps.audit.services import log_action
from apps.core.viewsets import TenantScopedModelViewSet
from .models import Customer, CustomerCreditTransaction
from .serializers import CustomerSerializer, CustomerCreditTransactionSerializer


class CustomerViewSet(TenantScopedModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ["name", "phone_number"]

    def perform_create(self, serializer):
        # Same fix as Product/Branch — see there for the full explanation.
        extra = {}
        if "is_active" not in self.request.data:
            extra["is_active"] = True
        serializer.save(business_id=self.request.business_id, **extra)


class CustomerCreditTransactionViewSet(TenantScopedModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = CustomerCreditTransaction.objects.all()
    serializer_class = CustomerCreditTransactionSerializer
    filterset_fields = ["customer", "entry_type"]

    def create(self, request, *args, **kwargs):
        client_reference = request.data.get("client_reference") or None
        if client_reference:
            existing = CustomerCreditTransaction.objects.filter(
                business_id=request.business_id, client_reference=client_reference
            ).first()
            if existing:
                return Response(self.get_serializer(existing).data, status=200)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(business_id=self.request.business_id, recorded_by=self.request.user)

        # Manual credit-ledger entries (a payment received, a manual
        # adjustment) directly move money in or out of what a customer
        # owes — exactly the kind of action that should be traceable
        # to who did it and why, same as a discount or a stock
        # adjustment. This was previously never recorded anywhere.
        log_action(
            business=serializer.instance.business, actor=self.request.user, action="credit_change",
            target=serializer.instance,
            new_value={"entry_type": serializer.data.get("entry_type"), "amount": serializer.data.get("amount")},
            reason=serializer.data.get("reference_note", ""),
        )
        return Response(serializer.data, status=201)
