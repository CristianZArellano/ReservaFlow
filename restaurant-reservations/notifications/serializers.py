from rest_framework import serializers
from django.utils import timezone
from .models import Notification, NotificationTemplate, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Notification model"""

    # Nested fields
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_email = serializers.CharField(source="customer.email", read_only=True)
    reservation_id = serializers.UUIDField(
        source="reservation.id", read_only=True, allow_null=True
    )

    # Computed fields
    delivery_time = serializers.DurationField(read_only=True)
    read_time = serializers.DurationField(read_only=True)
    is_due = serializers.BooleanField(read_only=True)
    can_retry = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "customer",
            "customer_name",
            "customer_email",
            "type",
            "channel",
            "subject",
            "message",
            "html_message",
            "priority",
            "status",
            "reservation",
            "reservation_id",
            "metadata",
            "scheduled_for",
            "sent_at",
            "delivered_at",
            "read_at",
            "error_message",
            "retry_count",
            "max_retries",
            "delivery_time",
            "read_time",
            "is_due",
            "can_retry",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "sent_at",
            "delivered_at",
            "read_at",
            "error_message",
            "retry_count",
            "created_at",
            "updated_at",
        ]

    def validate_scheduled_for(self, value):
        """Validate scheduled time is not in the past"""
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                "La fecha programada no puede ser en el pasado"
            )
        return value

    def validate_metadata(self, value):
        """Validate metadata is a valid JSON object"""
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Los metadatos deben ser un objeto JSON válido"
            )
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        # Validate retry count doesn't exceed max retries
        retry_count = attrs.get(
            "retry_count", self.instance.retry_count if self.instance else 0
        )
        max_retries = attrs.get(
            "max_retries", self.instance.max_retries if self.instance else 3
        )

        if retry_count > max_retries:
            raise serializers.ValidationError(
                {
                    "retry_count": f"Los intentos no pueden exceder el máximo ({max_retries})"
                }
            )

        return attrs


class NotificationCreateSerializer(NotificationSerializer):
    """Serializer for creating notifications"""

    class Meta(NotificationSerializer.Meta):
        extra_kwargs = {
            "customer": {"required": True},
            "type": {"required": True},
            "channel": {"required": True},
            "subject": {"required": True},
            "message": {"required": True},
        }


class NotificationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for notification listings"""

    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    reservation_id = serializers.UUIDField(
        source="reservation.id", read_only=True, allow_null=True
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "customer_name",
            "type",
            "channel",
            "subject",
            "priority",
            "status",
            "reservation_id",
            "scheduled_for",
            "sent_at",
            "created_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""

    total_notifications = serializers.IntegerField(read_only=True)
    by_status = serializers.DictField(read_only=True)
    by_type = serializers.DictField(read_only=True)
    by_channel = serializers.DictField(read_only=True)
    delivery_rates = serializers.DictField(read_only=True)
    failed_notifications = serializers.IntegerField(read_only=True)
    pending_notifications = serializers.IntegerField(read_only=True)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for NotificationTemplate model"""

    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "name",
            "type",
            "channel",
            "subject_template",
            "message_template",
            "html_template",
            "is_active",
            "variables",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        """Validate template name is unique"""
        if self.instance:
            existing = NotificationTemplate.objects.filter(name=value).exclude(
                pk=self.instance.pk
            )
        else:
            existing = NotificationTemplate.objects.filter(name=value)

        if existing.exists():
            raise serializers.ValidationError("Ya existe un template con este nombre")

        return value

    def validate_variables(self, value):
        """Validate variables is a list"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Las variables deben ser una lista")

        # Validate each variable is a string
        for var in value:
            if not isinstance(var, str):
                raise serializers.ValidationError("Cada variable debe ser un string")

        return value

    def validate(self, attrs):
        """Validate template combination is unique"""
        type_val = attrs.get("type", self.instance.type if self.instance else None)
        channel_val = attrs.get(
            "channel", self.instance.channel if self.instance else None
        )

        if type_val and channel_val:
            existing = NotificationTemplate.objects.filter(
                type=type_val, channel=channel_val
            )
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise serializers.ValidationError(
                    f"Ya existe un template para {type_val} en canal {channel_val}"
                )

        return attrs


class NotificationTemplateRenderSerializer(serializers.Serializer):
    """Serializer for template rendering requests"""

    context = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        help_text="Context variables for template rendering",
    )

    def validate_context(self, value):
        """Validate context variables"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("El contexto debe ser un objeto")

        # All values should be strings for template rendering
        for key, val in value.items():
            if not isinstance(key, str):
                raise serializers.ValidationError(
                    "Las claves del contexto deben ser strings"
                )

        return value


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model"""

    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "customer",
            "customer_name",
            "reservation_confirmations",
            "reservation_reminders",
            "promotional_emails",
            "feedback_requests",
            "email_enabled",
            "sms_enabled",
            "push_enabled",
            "quiet_hours_start",
            "quiet_hours_end",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        """Validate quiet hours configuration"""
        start_time = attrs.get(
            "quiet_hours_start",
            self.instance.quiet_hours_start if self.instance else None,
        )
        end_time = attrs.get(
            "quiet_hours_end", self.instance.quiet_hours_end if self.instance else None
        )

        # Both or neither should be set
        if (start_time is None) != (end_time is None):
            raise serializers.ValidationError(
                "Debe especificar tanto el inicio como el fin de las horas silenciosas, o ninguno"
            )

        return attrs


class NotificationBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk notification creation"""

    template_id = serializers.IntegerField()
    customer_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=1000,  # Limit bulk operations
    )
    context = serializers.DictField(
        child=serializers.CharField(), required=False, default=dict
    )
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_CHOICES, default="normal"
    )
    scheduled_for = serializers.DateTimeField(required=False)

    def validate_template_id(self, value):
        """Validate template exists and is active"""
        try:
            NotificationTemplate.objects.get(id=value, is_active=True)
            return value
        except NotificationTemplate.DoesNotExist:
            raise serializers.ValidationError("Template no encontrado o inactivo")

    def validate_customer_ids(self, value):
        """Validate all customers exist"""
        from customers.models import Customer

        existing_customers = Customer.objects.filter(id__in=value, is_active=True)
        existing_ids = set(existing_customers.values_list("id", flat=True))
        missing_ids = set(value) - existing_ids

        if missing_ids:
            raise serializers.ValidationError(
                f"Clientes no encontrados o inactivos: {list(missing_ids)}"
            )

        return value

    def validate_scheduled_for(self, value):
        """Validate scheduled time is not in the past"""
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                "La fecha programada no puede ser en el pasado"
            )
        return value


class NotificationMarkAsReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read"""

    notification_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=100
    )

    def validate_notification_ids(self, value):
        """Validate all notifications exist and belong to the customer"""
        customer = self.context.get("customer")
        if not customer:
            raise serializers.ValidationError("Cliente requerido en el contexto")

        notifications = Notification.objects.filter(
            id__in=value, customer=customer, status="delivered"
        )

        existing_ids = set(notifications.values_list("id", flat=True))
        provided_ids = set(value)
        missing_ids = provided_ids - existing_ids

        if missing_ids:
            raise serializers.ValidationError(
                f"Notificaciones no encontradas o no pertenecen al cliente: {list(missing_ids)}"
            )

        return value


class CustomerNotificationSummarySerializer(serializers.Serializer):
    """Serializer for customer notification summary"""

    customer_id = serializers.IntegerField(read_only=True)
    customer_name = serializers.CharField(read_only=True)
    unread_count = serializers.IntegerField(read_only=True)
    total_notifications = serializers.IntegerField(read_only=True)
    recent_notifications = NotificationListSerializer(many=True, read_only=True)
    preferences = NotificationPreferenceSerializer(read_only=True)
