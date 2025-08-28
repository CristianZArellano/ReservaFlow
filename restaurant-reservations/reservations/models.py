import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        CONFIRMED = "confirmed", "Confirmada"
        COMPLETED = "completed", "Completada"
        CANCELLED = "cancelled", "Cancelada"
        NO_SHOW = "no_show", "No asistió"
        EXPIRED = "expired", "Expirada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relaciones
    restaurant = models.ForeignKey("restaurants.Restaurant", on_delete=models.CASCADE)
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE)
    table = models.ForeignKey("restaurants.Table", on_delete=models.CASCADE)

    # Info de la reserva
    reservation_date = models.DateField("Fecha")
    reservation_time = models.TimeField("Hora")
    party_size = models.PositiveIntegerField("Personas")

    # Estado
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Reserva {self.id.hex[:8]} - {self.customer or 'Sin cliente'}"

    def is_expired(self) -> bool:
        """Devuelve True si la reserva ya venció."""
        return self.expires_at and timezone.now() >= self.expires_at

    def schedule_expiration(self):
        """Programa la expiración automática de la reserva."""
        if self.status == self.Status.PENDING and self.expires_at:
            try:
                from .tasks import expire_reservation

                expire_reservation.apply_async(args=[str(self.id)], eta=self.expires_at)
                logger.info(
                    "Expiración programada para reserva %s a las %s",
                    self.id,
                    self.expires_at,
                )
            except Exception as e:
                logger.error(
                    "Error programando expiración de reserva %s: %s", self.id, str(e)
                )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None

        # Obtener estado anterior si no es nueva
        if not is_new:
            old_status = (
                Reservation.objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

        # Establecer expires_at solo si es nueva y está pendiente
        if self.status == self.Status.PENDING and not self.expires_at:
            timeout = getattr(settings, "RESERVATION_PENDING_TIMEOUT", 15)
            self.expires_at = timezone.now() + timedelta(minutes=timeout)

        super().save(*args, **kwargs)

        # Programar expiración después de guardar si está pendiente
        if self.status == self.Status.PENDING:
            self.schedule_expiration()

        # Programar recordatorio si cambió de pending a confirmed
        if old_status == self.Status.PENDING and self.status == self.Status.CONFIRMED:
            try:
                from .tasks import schedule_reminder

                schedule_reminder.delay(str(self.id), hours_before=24)
                logger.info("Recordatorio programado para reserva %s", self.id)
            except Exception as e:
                logger.error(
                    "Error programando recordatorio para reserva %s: %s",
                    self.id,
                    str(e),
                )

    @property
    def reservation_datetime(self):
        """Datetime completo de la reserva"""
        from django.utils import timezone as tz

        return tz.datetime.combine(
            self.reservation_date, self.reservation_time
        ).replace(tzinfo=tz.get_current_timezone())
