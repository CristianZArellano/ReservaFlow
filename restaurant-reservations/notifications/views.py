import logging
from datetime import datetime
from django.db.models import Count, Q, F
from django.utils import timezone
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django_filters.rest_framework import DjangoFilterBackend

from .models import Notification, NotificationTemplate, NotificationPreference
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    NotificationListSerializer,
    NotificationTemplateSerializer,
    NotificationTemplateRenderSerializer,
    NotificationPreferenceSerializer,
    NotificationBulkCreateSerializer,
    NotificationMarkAsReadSerializer,
)

logger = logging.getLogger(__name__)


class NotificationThrottle(UserRateThrottle):
    """Custom throttling for notification operations"""

    scope = "notification"


class NotificationViewSet(viewsets.ModelViewSet):
    """Complete ViewSet for Notification CRUD operations"""

    queryset = Notification.objects.all()
    filterset_fields = ["type", "channel", "status", "priority", "customer"]
    search_fields = [
        "subject",
        "message",
        "customer__first_name",
        "customer__last_name",
    ]
    ordering_fields = ["created_at", "sent_at", "priority"]
    ordering = ["-created_at"]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return NotificationCreateSerializer
        elif self.action == "list":
            return NotificationListSerializer
        elif self.action == "bulk_create":
            return NotificationBulkCreateSerializer
        elif self.action == "mark_as_read":
            return NotificationMarkAsReadSerializer
        return NotificationSerializer

    def get_throttles(self):
        """Apply different throttles based on action"""
        if self.action in ["create", "bulk_create"]:
            throttle_classes = [NotificationThrottle]
        else:
            throttle_classes = [AnonRateThrottle, UserRateThrottle]
        return [throttle() for throttle in throttle_classes]

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ["list", "retrieve", "stats"]:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Optimize queryset with filters"""
        queryset = Notification.objects.select_related("customer", "reservation")

        # Filter by date range
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date).date()
                queryset = queryset.filter(created_at__date__gte=start_date)
            except ValueError:
                pass

        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date).date()
                queryset = queryset.filter(created_at__date__lte=end_date)
            except ValueError:
                pass

        # Filter by customer if specified
        customer_id = self.request.query_params.get("customer_id")
        if customer_id:
            try:
                queryset = queryset.filter(customer_id=int(customer_id))
            except ValueError:
                pass

        return queryset

    def perform_create(self, serializer):
        """Create notification with logging"""
        try:
            notification = serializer.save()
            logger.info(
                f"Notification created: {notification.type} for {notification.customer.full_name}"
            )
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            raise

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get notification statistics overview"""
        queryset = self.get_queryset()

        # Basic counts
        total = queryset.count()
        by_status = dict(
            queryset.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        by_type = dict(
            queryset.values("type")
            .annotate(count=Count("id"))
            .values_list("type", "count")
        )
        by_channel = dict(
            queryset.values("channel")
            .annotate(count=Count("id"))
            .values_list("channel", "count")
        )

        # Delivery rates
        sent_count = queryset.filter(status__in=["sent", "delivered", "read"]).count()
        delivered_count = queryset.filter(status__in=["delivered", "read"]).count()
        read_count = queryset.filter(status="read").count()

        delivery_rates = {
            "sent_rate": (sent_count / max(total, 1)) * 100,
            "delivery_rate": (delivered_count / max(sent_count, 1)) * 100,
            "read_rate": (read_count / max(delivered_count, 1)) * 100,
        }

        stats = {
            "total_notifications": total,
            "by_status": by_status,
            "by_type": by_type,
            "by_channel": by_channel,
            "delivery_rates": delivery_rates,
            "failed_notifications": by_status.get("failed", 0),
            "pending_notifications": by_status.get("pending", 0),
        }

        return Response(stats)

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """Create multiple notifications from a template"""
        serializer = NotificationBulkCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        template_id = data["template_id"]
        customer_ids = data["customer_ids"]
        context = data.get("context", {})
        priority = data.get("priority", "normal")
        scheduled_for = data.get("scheduled_for")

        try:
            template = NotificationTemplate.objects.get(id=template_id)

            # Render template with context
            rendered = template.render(context)

            # Create notifications for all customers
            notifications = []
            from customers.models import Customer

            customers = Customer.objects.filter(id__in=customer_ids, is_active=True)

            for customer in customers:
                # Check customer preferences
                try:
                    prefs = customer.notification_preferences
                    if not prefs.allows_notification(
                        template.type, template.channel, scheduled_for
                    ):
                        continue
                except NotificationPreference.DoesNotExist:
                    pass  # No preferences set, allow all

                notification = Notification.objects.create(
                    customer=customer,
                    type=template.type,
                    channel=template.channel,
                    subject=rendered["subject"],
                    message=rendered["message"],
                    html_message=rendered["html_message"],
                    priority=priority,
                    scheduled_for=scheduled_for,
                    metadata={"template_id": template_id, "bulk_created": True},
                )
                notifications.append(notification)

            logger.info(
                f"Bulk created {len(notifications)} notifications from template {template_id}"
            )

            return Response(
                {
                    "message": f"Se crearon {len(notifications)} notificaciones exitosamente",
                    "created_count": len(notifications),
                    "skipped_count": len(customer_ids) - len(notifications),
                    "notification_ids": [str(n.id) for n in notifications],
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error in bulk notification creation: {e}")
            return Response(
                {"error": "Error creando notificaciones masivas"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def mark_as_read(self, request):
        """Mark multiple notifications as read"""
        serializer = NotificationMarkAsReadSerializer(
            data=request.data,
            context={
                "customer": request.user.customer
                if hasattr(request.user, "customer")
                else None
            },
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        notification_ids = serializer.validated_data["notification_ids"]

        updated = Notification.objects.filter(
            id__in=notification_ids, status="delivered"
        ).update(status="read", read_at=timezone.now())

        return Response(
            {
                "message": f"Se marcaron {updated} notificaciones como leídas",
                "updated_count": updated,
            }
        )

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get notifications that are due to be sent"""
        now = timezone.now()
        pending = Notification.objects.filter(
            Q(status="pending")
            & (Q(scheduled_for__isnull=True) | Q(scheduled_for__lte=now))
        ).select_related("customer", "reservation")

        serializer = NotificationListSerializer(pending, many=True)
        return Response({"count": pending.count(), "notifications": serializer.data})

    @action(detail=False, methods=["get"])
    def failed(self, request):
        """Get failed notifications that can be retried"""
        failed = Notification.objects.filter(
            status="failed", retry_count__lt=F("max_retries")
        ).select_related("customer", "reservation")

        serializer = NotificationListSerializer(failed, many=True)
        return Response({"count": failed.count(), "notifications": serializer.data})

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Retry a failed notification"""
        notification = self.get_object()

        if not notification.can_retry():
            return Response(
                {"error": "Esta notificación no puede reintentarse"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reset status to pending
        notification.status = "pending"
        notification.error_message = ""
        notification.save(update_fields=["status", "error_message", "updated_at"])

        logger.info(f"Notification {notification.id} marked for retry")

        return Response(
            {
                "message": "Notificación programada para reintento",
                "notification_id": str(notification.id),
                "retry_count": notification.retry_count,
            }
        )

    @action(detail=False, methods=["get"])
    def customer_summary(self, request):
        """Get notification summary for a customer"""
        customer_id = request.query_params.get("customer_id")
        if not customer_id:
            return Response(
                {"error": "customer_id requerido"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from customers.models import Customer

            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response(
                {"error": "Cliente no encontrado"}, status=status.HTTP_404_NOT_FOUND
            )

        notifications = Notification.objects.filter(customer=customer)
        recent = notifications.order_by("-created_at")[:10]

        try:
            preferences = customer.notification_preferences
        except NotificationPreference.DoesNotExist:
            preferences = None

        summary = {
            "customer_id": customer.id,
            "customer_name": customer.full_name,
            "unread_count": notifications.filter(status="delivered").count(),
            "total_notifications": notifications.count(),
            "recent_notifications": NotificationListSerializer(recent, many=True).data,
            "preferences": NotificationPreferenceSerializer(preferences).data
            if preferences
            else None,
        }

        return Response(summary)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notification templates"""

    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    filterset_fields = ["type", "channel", "is_active"]
    search_fields = ["name", "subject_template", "message_template"]
    ordering = ["name"]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def render(self, request, pk=None):
        """Render template with provided context"""
        template = self.get_object()
        serializer = NotificationTemplateRenderSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        context = serializer.validated_data.get("context", {})
        rendered = template.render(context)

        return Response(
            {
                "template_id": template.id,
                "template_name": template.name,
                "rendered": rendered,
                "context_used": context,
            }
        )

    @action(detail=False, methods=["get"])
    def by_type(self, request):
        """Get templates grouped by type"""
        templates = NotificationTemplate.objects.filter(is_active=True)
        grouped = {}

        for template in templates:
            if template.type not in grouped:
                grouped[template.type] = []
            grouped[template.type].append(NotificationTemplateSerializer(template).data)

        return Response(grouped)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate a template with a new name"""
        original = self.get_object()
        new_name = request.data.get("name")

        if not new_name:
            return Response(
                {"error": "name requerido"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create duplicate
        duplicate = NotificationTemplate.objects.create(
            name=new_name,
            type=original.type,
            channel=original.channel,
            subject_template=original.subject_template,
            message_template=original.message_template,
            html_template=original.html_template,
            variables=original.variables,
        )

        serializer = NotificationTemplateSerializer(duplicate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing customer notification preferences"""

    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    filterset_fields = ["customer", "email_enabled", "sms_enabled", "push_enabled"]

    filter_backends = [DjangoFilterBackend]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by customer if specified"""
        queryset = NotificationPreference.objects.select_related("customer")

        customer_id = self.request.query_params.get("customer_id")
        if customer_id:
            try:
                queryset = queryset.filter(customer_id=int(customer_id))
            except ValueError:
                pass

        return queryset

    @action(detail=True, methods=["post"])
    def test_preferences(self, request, pk=None):
        """Test if preferences allow a specific notification"""
        preferences = self.get_object()

        notification_type = request.data.get("notification_type")
        channel = request.data.get("channel")
        send_time_str = request.data.get("send_time")

        if not all([notification_type, channel]):
            return Response(
                {"error": "notification_type y channel requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        send_time = None
        if send_time_str:
            try:
                send_time = datetime.fromisoformat(send_time_str)
            except ValueError:
                return Response(
                    {"error": "Formato de send_time inválido. Use ISO format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        allowed = preferences.allows_notification(notification_type, channel, send_time)

        return Response(
            {
                "customer": preferences.customer.full_name,
                "notification_type": notification_type,
                "channel": channel,
                "send_time": send_time.isoformat() if send_time else None,
                "allowed": allowed,
                "preferences": NotificationPreferenceSerializer(preferences).data,
            }
        )

    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """Bulk update preferences for multiple customers"""
        customer_ids = request.data.get("customer_ids", [])
        preferences_data = request.data.get("preferences", {})

        if not customer_ids or not preferences_data:
            return Response(
                {"error": "customer_ids y preferences requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_count = NotificationPreference.objects.filter(
            customer_id__in=customer_ids
        ).update(**preferences_data)

        return Response(
            {
                "message": f"Preferencias actualizadas para {updated_count} clientes",
                "updated_count": updated_count,
            }
        )
