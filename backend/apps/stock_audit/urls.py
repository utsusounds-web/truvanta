from rest_framework.routers import DefaultRouter
from .views import QuickAuditViewSet

router = DefaultRouter()
router.register("quick-audits", QuickAuditViewSet, basename="quick-audit")
urlpatterns = router.urls
