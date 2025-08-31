import logging
import uuid
from datetime import time, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
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
    table = models.ForeignKey("restaurants.Table", on_delete=models.PROTECT)

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

    class Meta:
        # Prevenir dobles reservas para la misma mesa en la misma fecha/hora
        constraints = [
            models.UniqueConstraint(
                fields=["table", "reservation_date", "reservation_time"],
                condition=models.Q(status__in=["pending", "confirmed"]),
                name="unique_active_reservation_per_table_datetime",
            )
        ]
        indexes = [
            models.Index(fields=["table", "reservation_date", "reservation_time"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self):
        return f"Reserva {self.id.hex[:8]} - {self.customer or 'Sin cliente'}"

    def clean(self):
        """Validación personalizada del modelo"""
        super().clean()

        # Validar que no haya conflicto de horarios
        if self.table and self.reservation_date and self.reservation_time:
            self._validate_no_double_booking()

        # Validar fechas lógicas
        self._validate_dates()

        # Validar party size
        self._validate_party_size()

    def _validate_dates(self):
        """Validar que las fechas sean lógicas"""

        # No permitir reservas en el pasado
        if self.reservation_date:
            today = timezone.now().date()
            if self.reservation_date < today:
                raise ValidationError(
                    {
                        "reservation_date": "No se pueden hacer reservas en fechas pasadas."
                    }
                )

            # Límite de reservas futuras (ej: 90 días)
            max_future_date = today + timedelta(days=90)
            if self.reservation_date > max_future_date:
                raise ValidationError(
                    {
                        "reservation_date": "No se pueden hacer reservas con más de 90 días de anticipación."
                    }
                )

        # Validar horarios de operación
        if self.reservation_time:
            opening_time = time(10, 0)  # 10:00 AM
            closing_time = time(22, 0)  # 10:00 PM

            if not (opening_time <= self.reservation_time <= closing_time):
                raise ValidationError(
                    {
                        "reservation_time": f"Horario de reserva debe ser entre {opening_time} y {closing_time}."
                    }
                )

    def _validate_party_size(self):
        """Validar tamaño del grupo"""
        if self.party_size:
            if self.party_size < 1:
                raise ValidationError(
                    {"party_size": "El número de personas debe ser al menos 1."}
                )
            if self.party_size > 12:  # Límite máximo
                raise ValidationError(
                    {"party_size": "El número máximo de personas por reserva es 12."}
                )

            # Validar capacidad de la mesa
            if self.table and hasattr(self.table, "capacity"):
                if self.party_size > self.table.capacity:
                    raise ValidationError(
                        {
                            "party_size": f"La mesa {self.table.number} tiene capacidad para {self.table.capacity} personas."
                        }
                    )

    def _validate_no_double_booking(self):
        """Validar que no existe otra reserva activa para la misma mesa/fecha/hora"""
        conflicting_reservations = Reservation.objects.filter(
            table=self.table,
            reservation_date=self.reservation_date,
            reservation_time=self.reservation_time,
            status__in=[self.Status.PENDING, self.Status.CONFIRMED],
        ).exclude(pk=self.pk)

        if conflicting_reservations.exists():
            reservation = conflicting_reservations.first()
            raise ValidationError(
                {
                    "table": f"La mesa {self.table.number} ya está reservada para {self.reservation_date} a las {self.reservation_time}. "
                    f"Reserva existente: {reservation.id.hex[:8]}"
                }
            )

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

        # Ejecutar validación completa
        self.full_clean()

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

        return timezone.datetime.combine(
            self.reservation_date, self.reservation_time
        ).replace(tzinfo=timezone.get_current_timezone())
