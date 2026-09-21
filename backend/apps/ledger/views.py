from rest_framework import generics
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsBusinessMember, HasBusinessPermission, IsOwnerOrAdmin
from apps.tenants.models import Business

from . import services
from .models import Account, JournalEntry, OpeningBalanceStatement
from .serializers import AccountSerializer, JournalEntrySerializer, OpeningBalanceStatementSerializer


class RequireViewProfit(HasBusinessPermission):
    required_permission_code = "view_profit"


class AccountListView(generics.ListAPIView):
    """The business's Chart of Accounts — seeded automatically on
    first access, so this works even for a business that's never
    triggered a ledger entry yet.

    Gated on view_profit: the chart of accounts, journal entries, and
    trial balance are the most sensitive financial data in the app,
    so they get the same gate as Reports rather than being open to
    every business member."""
    permission_classes = [RequireViewProfit]
    serializer_class = AccountSerializer

    def get_queryset(self):
        business = Business.objects.get(pk=self.request.business_id)
        services.ensure_chart_of_accounts(business)
        return Account.objects.filter(business=business, is_active=True)


class JournalEntryViewSet(generics.ListAPIView):
    """Read-only — the ledger is never edited or deleted through the
    API, only ever appended to (and corrected via reversing entries).
    See services.post_entry / reverse_entry for the only way rows here
    get created. Gated on view_profit — see AccountListView."""
    permission_classes = [RequireViewProfit]
    serializer_class = JournalEntrySerializer
    filterset_fields = ["source_type", "branch"]

    def get_queryset(self):
        return JournalEntry.objects.filter(business_id=self.request.business_id).prefetch_related("lines__account")


class TrialBalanceView(APIView):
    """The classic accounting sanity check: every account and its
    balance, plus whether the whole ledger actually balances
    (total debits should equal total credits across everything ever
    posted — if post_entry is doing its job, this is always true).
    Gated on view_profit — see AccountListView."""
    permission_classes = [RequireViewProfit]

    def get(self, request):
        business = Business.objects.get(pk=request.business_id)
        rows = services.trial_balance(business)
        return Response({"accounts": rows})


class OpeningBalanceView(APIView):
    """A business's starting financial position — recorded once when
    they begin using Truvanta with an already-running business, and
    correctable afterward (see services.record_opening_balance for
    why a correction reverses-and-reposts rather than editing in
    place). Owner/admin only: this sets the business's starting net
    worth, a materially bigger deal than viewing a report, so it gets
    a tighter gate than the view_profit permission used elsewhere in
    this app."""
    permission_classes = [IsOwnerOrAdmin]

    def get(self, request):
        statement = OpeningBalanceStatement.objects.filter(business_id=request.business_id).first()
        if not statement:
            return Response(None)
        return Response(OpeningBalanceStatementSerializer(statement).data)

    def post(self, request):
        business = Business.objects.get(pk=request.business_id)
        serializer = OpeningBalanceStatementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            statement = services.record_opening_balance(
                business=business, user=request.user, as_of_date=data["as_of_date"],
                cash_on_hand=data.get("cash_on_hand", 0), bank_balance=data.get("bank_balance", 0),
                accounts_receivable=data.get("accounts_receivable", 0), inventory_value=data.get("inventory_value", 0),
                fixed_assets=data.get("fixed_assets", 0), accounts_payable=data.get("accounts_payable", 0),
                loans_payable=data.get("loans_payable", 0),
            )
        except ValueError as e:
            raise DRFValidationError({"detail": str(e)})
        return Response(OpeningBalanceStatementSerializer(statement).data, status=201)


class OpeningBalancePDFView(APIView):
    permission_classes = [IsOwnerOrAdmin]

    def get(self, request):
        from django.http import HttpResponse
        from .documents import generate_opening_balance_pdf

        statement = OpeningBalanceStatement.objects.filter(business_id=request.business_id).first()
        if not statement:
            return Response({"detail": "No opening balance has been recorded yet."}, status=404)
        pdf_bytes = generate_opening_balance_pdf(statement)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="opening-statement-{statement.as_of_date}.pdf"'
        return response
