import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Notification(models.Model):
    TYPE_CHOICES = [
        ("reservation_confirmation", "Confirmación de Reserva"),
        ("reservation_reminder", "Recordatorio de Reserva"),
        ("reservation_cancelled", "Reserva Cancelada"),
        ("reservation_modified", "Reserva Modificada"),
        ("customer_welcome", "Bienvenida Cliente"),
        ("promotion", "Promoción"),
        ("system_alert", "Alerta del Sistema"),
        ("feedback_request", "Solicitud de Feedback"),
    ]

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("push", "Push Notification"),
        ("in_app", "Notificación In-App"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("sent", "Enviada"),
        ("delivered", "Entregada"),
        ("failed", "Fallida"),
        ("read", "Leída"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Baja"),
        ("normal", "Normal"),
        ("high", "Alta"),
        ("urgent", "Urgente"),
    ]

    # Identificación
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Destinatario
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Cliente",
    )

    # Contenido
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name="Tipo")
    channel = models.CharField(
        max_length=10, choices=CHANNEL_CHOICES, verbose_name="Canal"
    )
    subject = models.CharField(max_length=200, verbose_name="Asunto")
    message = models.TextField(verbose_name="Mensaje")
    html_message = models.TextField(blank=True, verbose_name="Mensaje HTML")

    # Metadatos
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="normal",
        verbose_name="Prioridad",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending", verbose_name="Estado"
    )

    # Relación opcional con reserva
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="Reserva",
    )

    # Datos adicionales (JSON)
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadatos")

    # Control de envío
    scheduled_for = models.DateTimeField(
        null=True, blank=True, verbose_name="Programada para"
    )
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Enviada en")
    delivered_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Entregada en"
    )
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Leída en")

    # Información de error
    error_message = models.TextField(blank=True, verbose_name="Mensaje de error")
    retry_count = models.PositiveIntegerField(
        default=0, verbose_name="Intentos de reenvío"
    )
    max_retries = models.PositiveIntegerField(default=3, verbose_name="Máximo intentos")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["type", "channel"]),
            models.Index(fields=["scheduled_for"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["reservation"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_type_display()} - {self.customer.full_name} ({self.status})"

    def clean(self):
        """Validación personalizada del modelo"""
        super().clean()

        # Validar que scheduled_for no sea en el pasado
        if self.scheduled_for and self.scheduled_for <= timezone.now():
            raise ValidationError(
                {"scheduled_for": "La fecha programada no puede ser en el pasado"}
            )

        # Validar retry_count no exceda max_retries
        if self.retry_count > self.max_retries:
            raise ValidationError(
                {
                    "retry_count": f"Los intentos de reenvío no pueden exceder el máximo ({self.max_retries})"
                }
            )

    def save(self, *args, **kwargs):
        # Validación completa
        self.full_clean()

        # Auto-set sent_at when status changes to sent
        if self.status == "sent" and not self.sent_at:
            self.sent_at = timezone.now()

        # Auto-set delivered_at when status changes to delivered
        if self.status == "delivered" and not self.delivered_at:
            self.delivered_at = timezone.now()

        # Auto-set read_at when status changes to read
        if self.status == "read" and not self.read_at:
            self.read_at = timezone.now()

        super().save(*args, **kwargs)

    def mark_as_sent(self):
        """Marcar notificación como enviada"""
        self.status = "sent"
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at", "updated_at"])

    def mark_as_delivered(self):
        """Marcar notificación como entregada"""
        self.status = "delivered"
        self.delivered_at = timezone.now()
        self.save(update_fields=["status", "delivered_at", "updated_at"])

    def mark_as_read(self):
        """Marcar notificación como leída"""
        self.status = "read"
        self.read_at = timezone.now()
        self.save(update_fields=["status", "read_at", "updated_at"])

    def mark_as_failed(self, error_msg=""):
        """Marcar notificación como fallida"""
        self.status = "failed"
        self.error_message = error_msg
        self.retry_count += 1
        self.save(
            update_fields=["status", "error_message", "retry_count", "updated_at"]
        )

    def can_retry(self):
        """Verificar si la notificación puede reintentarse"""
        return (
            self.status == "failed"
            and self.retry_count < self.max_retries
            and self.priority in ["high", "urgent"]
        )

    def is_due(self):
        """Verificar si la notificación está programada para enviarse ahora"""
        if not self.scheduled_for:
            return self.status == "pending"
        return self.status == "pending" and self.scheduled_for <= timezone.now()

    @property
    def delivery_time(self):
        """Tiempo transcurrido desde creación hasta entrega"""
        if self.delivered_at:
            return self.delivered_at - self.created_at
        return None

    @property
    def read_time(self):
        """Tiempo transcurrido desde entrega hasta lectura"""
        if self.read_at and self.delivered_at:
            return self.read_at - self.delivered_at
        return None


class NotificationTemplate(models.Model):
    """Template for notification messages"""

    TYPE_CHOICES = Notification.TYPE_CHOICES
    CHANNEL_CHOICES = Notification.CHANNEL_CHOICES

    # Identificación
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name="Tipo")
    channel = models.CharField(
        max_length=10, choices=CHANNEL_CHOICES, verbose_name="Canal"
    )

    # Contenido del template
    subject_template = models.CharField(
        max_length=200, verbose_name="Template del asunto"
    )
    message_template = models.TextField(verbose_name="Template del mensaje")
    html_template = models.TextField(blank=True, verbose_name="Template HTML")

    # Configuración
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    variables = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Variables disponibles",
        help_text="Lista de variables que puede usar este template",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Template de Notificación"
        verbose_name_plural = "Templates de Notificación"
        unique_together = ["type", "channel"]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()} - {self.get_channel_display()})"

    def render(self, context=None):
        """Renderizar el template con el contexto proporcionado"""
        if not context:
            context = {}

        # Simple template rendering (could be enhanced with Django templates)
        subject = self.subject_template
        message = self.message_template
        html_message = self.html_template

        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            message = message.replace(placeholder, str(value))
            if html_message:
                html_message = html_message.replace(placeholder, str(value))

        return {"subject": subject, "message": message, "html_message": html_message}


class NotificationPreference(models.Model):
    """Customer notification preferences"""

    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        verbose_name="Cliente",
    )

    # Preferencias por tipo de notificación
    reservation_confirmations = models.BooleanField(
        default=True, verbose_name="Confirmaciones de reserva"
    )
    reservation_reminders = models.BooleanField(
        default=True, verbose_name="Recordatorios de reserva"
    )
    promotional_emails = models.BooleanField(
        default=True, verbose_name="Emails promocionales"
    )
    feedback_requests = models.BooleanField(
        default=True, verbose_name="Solicitudes de feedback"
    )

    # Preferencias por canal
    email_enabled = models.BooleanField(default=True, verbose_name="Email habilitado")
    sms_enabled = models.BooleanField(default=False, verbose_name="SMS habilitado")
    push_enabled = models.BooleanField(default=True, verbose_name="Push habilitado")

    # Configuración de horarios
    quiet_hours_start = models.TimeField(
        null=True, blank=True, verbose_name="Inicio horas silencio"
    )
    quiet_hours_end = models.TimeField(
        null=True, blank=True, verbose_name="Fin horas silencio"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferencia de Notificación"
        verbose_name_plural = "Preferencias de Notificación"

    def __str__(self):
        return f"Preferencias de {self.customer.full_name}"

    def allows_notification(self, notification_type, channel, send_time=None):
        """Verificar si el cliente permite un tipo específico de notificación"""
        # Verificar preferencias por tipo
        type_mapping = {
            "reservation_confirmation": self.reservation_confirmations,
            "reservation_reminder": self.reservation_reminders,
            "promotion": self.promotional_emails,
            "feedback_request": self.feedback_requests,
        }

        if notification_type in type_mapping and not type_mapping[notification_type]:
            return False

        # Verificar preferencias por canal
        channel_mapping = {
            "email": self.email_enabled,
            "sms": self.sms_enabled,
            "push": self.push_enabled,
        }

        if channel in channel_mapping and not channel_mapping[channel]:
            return False

        # Verificar horas silenciosas
        if send_time and self.quiet_hours_start and self.quiet_hours_end:
            send_time_only = send_time.time()
            if self.quiet_hours_start <= self.quiet_hours_end:
                # Mismo día
                if self.quiet_hours_start <= send_time_only <= self.quiet_hours_end:
                    return False
            else:
                # Atraviesa medianoche
                if (
                    send_time_only >= self.quiet_hours_start
                    or send_time_only <= self.quiet_hours_end
                ):
                    return False

        return True
