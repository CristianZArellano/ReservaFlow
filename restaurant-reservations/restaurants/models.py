from django.db import models


class Restaurant(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre")
    description = models.TextField(blank=True, verbose_name="Descripción")
    address = models.CharField(max_length=300, verbose_name="Dirección")
    phone = models.CharField(max_length=20, verbose_name="Teléfono")
    email = models.EmailField(verbose_name="Email")

    # Horarios de operación
    opening_time = models.TimeField(verbose_name="Hora de apertura")
    closing_time = models.TimeField(verbose_name="Hora de cierre")

    # Configuración de reservas
    reservation_duration = models.PositiveIntegerField(
        default=120, verbose_name="Duración reserva (minutos)"
    )
    advance_booking_days = models.PositiveIntegerField(
        default=30, verbose_name="Días de anticipación"
    )

    # Metadata
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Restaurante"
        verbose_name_plural = "Restaurantes"

    def __str__(self):
        return self.name


class Table(models.Model):
    LOCATION_CHOICES = [
        ("indoor", "Interior"),
        ("outdoor", "Terraza"),
        ("bar", "Barra"),
    ]

    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="tables"
    )
    number = models.CharField(max_length=10, verbose_name="Número")
    capacity = models.PositiveIntegerField(verbose_name="Capacidad")
    location = models.CharField(
        max_length=10, choices=LOCATION_CHOICES, default="indoor"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Mesa {self.number} - {self.restaurant.name}"
