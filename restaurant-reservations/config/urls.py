# config/urls.py
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/reservations/", include("reservations.urls")),
    path("api/restaurants/", include("restaurants.urls")),
    path("api/customers/", include("customers.urls")),
    path("api/notifications/", include("notifications.urls")),
]
