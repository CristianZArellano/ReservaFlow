from django.contrib.auth.models import User
from django.db import models


class Customer(models.Model):
    # Relación con User de Django (opcional)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Usuario"
    )

    # Información básica
    first_name = models.CharField(max_length=100, verbose_name="Nombre")
    last_name = models.CharField(max_length=100, verbose_name="Apellido")
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Teléfono")

    # Estadísticas
    total_reservations = models.PositiveIntegerField(default=0)
    cancelled_reservations = models.PositiveIntegerField(default=0)

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
