from django.urls import path

from .views import AccountListView, JournalEntryViewSet, TrialBalanceView, OpeningBalanceView, OpeningBalancePDFView

urlpatterns = [
    path("accounts/", AccountListView.as_view(), name="ledger-accounts"),
    path("journal-entries/", JournalEntryViewSet.as_view(), name="ledger-journal-entries"),
    path("trial-balance/", TrialBalanceView.as_view(), name="ledger-trial-balance"),
    path("opening-balance/", OpeningBalanceView.as_view(), name="ledger-opening-balance"),
    path("opening-balance/pdf/", OpeningBalancePDFView.as_view(), name="ledger-opening-balance-pdf"),
]
