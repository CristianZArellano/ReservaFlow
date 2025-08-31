# reservations/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ReservationViewSet

# Create router for API endpoints
router = DefaultRouter()
router.register("", ReservationViewSet, basename="reservation")

urlpatterns = [
    path('api/', include(router.urls)),
]
