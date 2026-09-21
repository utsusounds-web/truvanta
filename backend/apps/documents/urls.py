from rest_framework.routers import DefaultRouter
from .views import VaultDocumentViewSet

router = DefaultRouter()
router.register("documents", VaultDocumentViewSet, basename="document")
urlpatterns = router.urls
