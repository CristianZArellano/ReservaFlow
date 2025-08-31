import re
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


def validate_phone_number(value):
    """Validate phone number format"""
    phone_regex = re.compile(r"^\+?[1-9]\d{1,14}$")
    if not phone_regex.match(value.replace("-", "").replace(" ", "")):
        raise ValidationError(
            "Número de teléfono debe tener formato válido (+1234567890)"
        )


class Customer(models.Model):
    # Relación con User de Django (opcional)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Usuario"
    )

    # Información básica
    first_name = models.CharField(
        max_length=100,
        verbose_name="Nombre",
        validators=[
            RegexValidator(
                r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", "Solo letras y espacios permitidos"
            )
        ],
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name="Apellido",
        validators=[
            RegexValidator(
                r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", "Solo letras y espacios permitidos"
            )
        ],
    )
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(
        max_length=20, verbose_name="Teléfono", validators=[validate_phone_number]
    )

    # Información adicional
    birth_date = models.DateField(
        null=True, blank=True, verbose_name="Fecha de nacimiento"
    )
    preferences = models.TextField(blank=True, verbose_name="Preferencias")
    allergies = models.TextField(blank=True, verbose_name="Alergias")

    # Estadísticas (actualizadas automáticamente)
    total_reservations = models.PositiveIntegerField(
        default=0, verbose_name="Total reservas"
    )
    cancelled_reservations = models.PositiveIntegerField(
        default=0, verbose_name="Reservas canceladas"
    )
    no_show_count = models.PositiveIntegerField(
        default=0, verbose_name="No asistencias"
    )

    # Scoring del cliente (0-100)
    customer_score = models.PositiveIntegerField(
        default=100, verbose_name="Puntuación cliente"
    )

    # Metadata
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
            models.Index(fields=["customer_score"]),
            models.Index(fields=["is_active", "created_at"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        """Validación personalizada del modelo"""
        super().clean()

        # Validar nombres no estén vacíos después de strip
        if not self.first_name or not self.first_name.strip():
            raise ValidationError({"first_name": "El nombre no puede estar vacío"})

        if not self.last_name or not self.last_name.strip():
            raise ValidationError({"last_name": "El apellido no puede estar vacío"})

    def save(self, *args, **kwargs):
        # Normalizar nombres
        self.first_name = self.first_name.strip().title()
        self.last_name = self.last_name.strip().title()
        self.email = self.email.lower().strip()

        # Validación completa
        self.full_clean()

        super().save(*args, **kwargs)

    @property
    def full_name(self):
        """Nombre completo del cliente"""
        return f"{self.first_name} {self.last_name}"

    @property
    def reliability_score(self):
        """Puntuación de confiabilidad basada en historial"""
        if self.total_reservations == 0:
            return 100

        completion_rate = (
            (self.total_reservations - self.cancelled_reservations - self.no_show_count)
            / self.total_reservations
        ) * 100
        return max(0, min(100, int(completion_rate)))

    def update_stats(self):
        """Actualizar estadísticas del cliente basadas en reservas"""
        from reservations.models import Reservation

        reservations = Reservation.objects.filter(customer=self)
        self.total_reservations = reservations.count()
        self.cancelled_reservations = reservations.filter(status="cancelled").count()
        self.no_show_count = reservations.filter(status="no_show").count()
        self.customer_score = self.reliability_score
        self.save(
            update_fields=[
                "total_reservations",
                "cancelled_reservations",
                "no_show_count",
                "customer_score",
            ]
        )

    def can_make_reservation(self):
        """Verificar si el cliente puede hacer reservas"""
        return (
            self.is_active and self.customer_score >= 20
        )  # Mínimo score para reservar
