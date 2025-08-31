# restaurants/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RestaurantViewSet, TableViewSet

# Create router for API endpoints
router = DefaultRouter()
router.register("restaurants", RestaurantViewSet, basename="restaurant")
router.register("tables", TableViewSet, basename="table")

urlpatterns = [
    path("api/", include(router.urls)),
]
