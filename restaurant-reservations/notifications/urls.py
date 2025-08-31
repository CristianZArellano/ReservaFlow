# notifications/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet,
    NotificationTemplateViewSet,
    NotificationPreferenceViewSet,
)

# Create router for API endpoints
router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
router.register(
    "templates", NotificationTemplateViewSet, basename="notification-template"
)
router.register(
    "preferences", NotificationPreferenceViewSet, basename="notification-preference"
)

urlpatterns = [
    path("api/", include(router.urls)),
]
