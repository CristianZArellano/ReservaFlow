import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models
from datetime import time


def validate_phone_number(value):
    """Validate restaurant phone number format"""
    phone_regex = re.compile(r"^\+?[1-9]\d{1,14}$")
    cleaned = value.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    if not phone_regex.match(cleaned):
        raise ValidationError("Número de teléfono debe tener formato válido")


class Restaurant(models.Model):
    CUISINE_CHOICES = [
        ("mexican", "Mexicana"),
        ("italian", "Italiana"),
        ("japanese", "Japonesa"),
        ("american", "Americana"),
        ("french", "Francesa"),
        ("chinese", "China"),
        ("indian", "India"),
        ("mediterranean", "Mediterránea"),
        ("fusion", "Fusión"),
        ("other", "Otra"),
    ]

    PRICE_RANGE_CHOICES = [
        ("$", "Económico"),
        ("$$", "Moderado"),
        ("$$$", "Caro"),
        ("$$$$", "Muy Caro"),
    ]

    # Información básica
    name = models.CharField(
        max_length=200,
        verbose_name="Nombre",
        validators=[
            RegexValidator(
                r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-&\.]+$",
                "Caracteres no válidos en el nombre",
            )
        ],
    )
    description = models.TextField(blank=True, verbose_name="Descripción")
    cuisine_type = models.CharField(
        max_length=20,
        choices=CUISINE_CHOICES,
        default="other",
        verbose_name="Tipo de cocina",
    )
    price_range = models.CharField(
        max_length=4,
        choices=PRICE_RANGE_CHOICES,
        default="$$",
        verbose_name="Rango de precios",
    )

    # Contacto y ubicación
    address = models.CharField(max_length=300, verbose_name="Dirección")
    phone = models.CharField(
        max_length=20, verbose_name="Teléfono", validators=[validate_phone_number]
    )
    email = models.EmailField(verbose_name="Email")
    website = models.URLField(blank=True, verbose_name="Sitio web")

    # Horarios de operación
    opening_time = models.TimeField(
        verbose_name="Hora de apertura", default=time(10, 0)
    )
    closing_time = models.TimeField(verbose_name="Hora de cierre", default=time(22, 0))

    # Días de operación
    monday_open = models.BooleanField(default=True, verbose_name="Lunes abierto")
    tuesday_open = models.BooleanField(default=True, verbose_name="Martes abierto")
    wednesday_open = models.BooleanField(default=True, verbose_name="Miércoles abierto")
    thursday_open = models.BooleanField(default=True, verbose_name="Jueves abierto")
    friday_open = models.BooleanField(default=True, verbose_name="Viernes abierto")
    saturday_open = models.BooleanField(default=True, verbose_name="Sábado abierto")
    sunday_open = models.BooleanField(default=False, verbose_name="Domingo abierto")

    # Configuración de reservas
    reservation_duration = models.PositiveIntegerField(
        default=120,
        verbose_name="Duración reserva (minutos)",
        validators=[MinValueValidator(30), MaxValueValidator(480)],
    )
    advance_booking_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Días de anticipación",
        validators=[MinValueValidator(1), MaxValueValidator(365)],
    )
    min_party_size = models.PositiveIntegerField(
        default=1, verbose_name="Mínimo personas"
    )
    max_party_size = models.PositiveIntegerField(
        default=12, verbose_name="Máximo personas"
    )

    # Configuración adicional
    accepts_walk_ins = models.BooleanField(
        default=True, verbose_name="Acepta sin reserva"
    )
    requires_deposit = models.BooleanField(
        default=False, verbose_name="Requiere depósito"
    )
    cancellation_hours = models.PositiveIntegerField(
        default=2,
        verbose_name="Horas para cancelar",
        validators=[MinValueValidator(1), MaxValueValidator(48)],
    )

    # Estadísticas
    total_capacity = models.PositiveIntegerField(
        default=0, verbose_name="Capacidad total"
    )
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    total_reservations = models.PositiveIntegerField(
        default=0, verbose_name="Total reservas"
    )

    # Metadata
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Restaurante"
        verbose_name_plural = "Restaurantes"
        indexes = [
            models.Index(fields=["is_active", "cuisine_type"]),
            models.Index(fields=["price_range"]),
            models.Index(fields=["average_rating"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """Validación personalizada del modelo"""
        super().clean()

        # Validar horarios
        if self.opening_time >= self.closing_time:
            raise ValidationError(
                {
                    "closing_time": "La hora de cierre debe ser posterior a la de apertura"
                }
            )

        # Validar tamaños de grupo
        if self.min_party_size > self.max_party_size:
            raise ValidationError(
                {"max_party_size": "El máximo de personas debe ser mayor al mínimo"}
            )

        # Validar que al menos un día esté abierto
        open_days = [
            self.monday_open,
            self.tuesday_open,
            self.wednesday_open,
            self.thursday_open,
            self.friday_open,
            self.saturday_open,
            self.sunday_open,
        ]
        if not any(open_days):
            raise ValidationError(
                "El restaurante debe estar abierto al menos un día de la semana"
            )

    def save(self, *args, **kwargs):
        # Normalizar datos
        self.name = self.name.strip()
        self.email = self.email.lower().strip()

        # Validación completa
        self.full_clean()

        super().save(*args, **kwargs)

        # Actualizar capacidad total después de guardar
        self.update_total_capacity()

    def update_total_capacity(self):
        """Actualizar capacidad total basada en mesas"""
        total = sum(table.capacity for table in self.tables.filter(is_active=True))
        if total != self.total_capacity:
            Restaurant.objects.filter(pk=self.pk).update(total_capacity=total)

    def is_open_on_day(self, weekday):
        """Verificar si el restaurante está abierto en un día específico (0=lunes, 6=domingo)"""
        day_mapping = [
            self.monday_open,
            self.tuesday_open,
            self.wednesday_open,
            self.thursday_open,
            self.friday_open,
            self.saturday_open,
            self.sunday_open,
        ]
        return day_mapping[weekday] if 0 <= weekday <= 6 else False

    def get_available_times(self, date):
        """Obtener horarios disponibles para una fecha específica"""
        if not self.is_open_on_day(date.weekday()):
            return []

        # Generar slots de tiempo basados en duración de reserva
        times = []
        current_time = self.opening_time
        slot_duration = self.reservation_duration

        while current_time < self.closing_time:
            times.append(current_time)
            # Agregar slot_duration minutos
            total_minutes = current_time.hour * 60 + current_time.minute + slot_duration
            hours, minutes = divmod(total_minutes, 60)
            if hours < 24:  # Evitar overflow
                current_time = time(hours, minutes)
            else:
                break

        return times

    @property
    def operating_days(self):
        """Lista de días que el restaurante está abierto"""
        days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        open_flags = [
            self.monday_open,
            self.tuesday_open,
            self.wednesday_open,
            self.thursday_open,
            self.friday_open,
            self.saturday_open,
            self.sunday_open,
        ]
        return [day for day, is_open in zip(days, open_flags) if is_open]


class Table(models.Model):
    LOCATION_CHOICES = [
        ("indoor", "Interior"),
        ("outdoor", "Terraza"),
        ("bar", "Barra"),
        ("private", "Privado"),
        ("patio", "Patio"),
        ("window", "Ventana"),
    ]

    SHAPE_CHOICES = [
        ("round", "Redonda"),
        ("square", "Cuadrada"),
        ("rectangular", "Rectangular"),
        ("oval", "Oval"),
        ("bar_style", "Tipo Barra"),
    ]

    # Relación con restaurante
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="tables"
    )

    # Información básica de la mesa
    number = models.CharField(
        max_length=10,
        verbose_name="Número",
        validators=[
            RegexValidator(r"^[A-Za-z0-9\-]+$", "Solo letras, números y guiones")
        ],
    )
    capacity = models.PositiveIntegerField(
        verbose_name="Capacidad",
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    min_capacity = models.PositiveIntegerField(
        default=1, verbose_name="Capacidad mínima", validators=[MinValueValidator(1)]
    )

    # Características físicas
    location = models.CharField(
        max_length=10,
        choices=LOCATION_CHOICES,
        default="indoor",
        verbose_name="Ubicación",
    )
    shape = models.CharField(
        max_length=15, choices=SHAPE_CHOICES, default="round", verbose_name="Forma"
    )

    # Características especiales
    has_view = models.BooleanField(default=False, verbose_name="Tiene vista")
    is_accessible = models.BooleanField(default=True, verbose_name="Accesible")
    is_quiet = models.BooleanField(default=False, verbose_name="Zona tranquila")
    has_high_chairs = models.BooleanField(
        default=False, verbose_name="Sillas altas disponibles"
    )

    # Configuración especial
    requires_special_request = models.BooleanField(
        default=False, verbose_name="Requiere solicitud especial"
    )
    special_notes = models.TextField(blank=True, verbose_name="Notas especiales")

    # Metadata
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mesa"
        verbose_name_plural = "Mesas"
        unique_together = ["restaurant", "number"]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["capacity", "location"]),
            models.Index(fields=["number"]),
        ]

    def __str__(self):
        return f"Mesa {self.number} - {self.restaurant.name}"

    def clean(self):
        """Validación personalizada del modelo"""
        super().clean()

        # Validar capacidades
        if self.min_capacity > self.capacity:
            raise ValidationError(
                {"capacity": "La capacidad máxima debe ser mayor o igual a la mínima"}
            )

        # Validar número único por restaurante
        if self.pk:
            existing = Table.objects.filter(
                restaurant=self.restaurant, number=self.number
            ).exclude(pk=self.pk)
        else:
            existing = Table.objects.filter(
                restaurant=self.restaurant, number=self.number
            )

        if existing.exists():
            raise ValidationError(
                {
                    "number": f"Ya existe una mesa con número {self.number} en este restaurante"
                }
            )

    def save(self, *args, **kwargs):
        # Normalizar número
        self.number = self.number.strip().upper()

        # Validación completa
        self.full_clean()

        # Guardar
        super().save(*args, **kwargs)

        # Actualizar capacidad total del restaurante
        self.restaurant.update_total_capacity()

    def is_suitable_for_party(self, party_size):
        """Verificar si la mesa es adecuada para el tamaño del grupo"""
        return self.min_capacity <= party_size <= self.capacity

    def get_reservation_count(self, start_date=None, end_date=None):
        """Obtener número de reservas para esta mesa en un rango de fechas"""
        from reservations.models import Reservation

        queryset = Reservation.objects.filter(table=self)

        if start_date:
            queryset = queryset.filter(reservation_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(reservation_date__lte=end_date)

        return queryset.count()

    def is_available_at_time(self, date, time):
        """Verificar si la mesa está disponible en una fecha y hora específica"""
        from reservations.models import Reservation

        # Verificar si el restaurante está abierto ese día
        if not self.restaurant.is_open_on_day(date.weekday()):
            return False

        # Verificar si hay reservas conflictivas
        conflicts = Reservation.objects.filter(
            table=self,
            reservation_date=date,
            reservation_time=time,
            status__in=["pending", "confirmed"],
        ).exists()

        return not conflicts and self.is_active

    @property
    def features_list(self):
        """Lista de características especiales de la mesa"""
        features = []
        if self.has_view:
            features.append("Vista")
        if self.is_accessible:
            features.append("Accesible")
        if self.is_quiet:
            features.append("Zona tranquila")
        if self.has_high_chairs:
            features.append("Sillas altas")
        if self.requires_special_request:
            features.append("Solicitud especial")
        return features

    @property
    def capacity_range_display(self):
        """Mostrar rango de capacidad en formato legible"""
        if self.min_capacity == self.capacity:
            return f"{self.capacity} personas"
        else:
            return f"{self.min_capacity}-{self.capacity} personas"
