# reservations/urls.py
from rest_framework.routers import DefaultRouter

from .views import ReservationViewSet

router = DefaultRouter()
# con '' la ruta base será directamente /reservations/
router.register("", ReservationViewSet, basename="reservation")

urlpatterns = router.urls
