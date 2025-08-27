import uuid

from django.db import models


class Reservation(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pendiente"),  # Reserva temporal (15 min para confirmar)
        ("confirmed", "Confirmada"),  # Confirmada y pagada
        ("completed", "Completada"),  # Cliente terminó
        ("cancelled", "Cancelada"),  # Cancelada por el cliente
        ("no_show", "No asistió"),  # Cliente no llegó
        ("expired", "Expirada"),  # No confirmada a tiempo
    ]

    # ID único para la reserva
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relaciones
    restaurant = models.ForeignKey("restaurants.Restaurant", on_delete=models.CASCADE)
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE)
    table = models.ForeignKey("restaurants.Table", on_delete=models.CASCADE)

    # Información de la reserva
    reservation_date = models.DateField(verbose_name="Fecha")
    reservation_time = models.TimeField(verbose_name="Hora")
    party_size = models.PositiveIntegerField(verbose_name="Personas")

    # Estado y control
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Reserva {self.id.hex[:8]} - {self.customer}"
