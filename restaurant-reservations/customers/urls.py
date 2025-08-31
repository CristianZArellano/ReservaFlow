# customers/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet

# Create router for API endpoints
router = DefaultRouter()
router.register("", CustomerViewSet, basename="customer")

urlpatterns = [
    path("", include(router.urls)),
]
