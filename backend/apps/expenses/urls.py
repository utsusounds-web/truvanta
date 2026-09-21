from rest_framework.routers import DefaultRouter
from .views import ExpenseCategoryViewSet, ExpenseViewSet, OwnerWithdrawalViewSet

router = DefaultRouter()
router.register("expense-categories", ExpenseCategoryViewSet, basename="expense-category")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("owner-withdrawals", OwnerWithdrawalViewSet, basename="owner-withdrawal")
urlpatterns = router.urls
