import logging
from django.db.models import Q, Avg
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django_filters.rest_framework import DjangoFilterBackend

from .models import Customer
from .serializers import (
    CustomerSerializer,
    CustomerCreateSerializer,
    CustomerUpdateSerializer,
    CustomerStatsSerializer,
    CustomerReservationHistorySerializer,
)

logger = logging.getLogger(__name__)


class CustomerThrottle(UserRateThrottle):
    """Custom throttling for customer operations"""

    scope = "customer"


class CustomerViewSet(viewsets.ModelViewSet):
    """Complete ViewSet for Customer CRUD operations"""

    queryset = Customer.objects.all()
    filterset_fields = ["is_active", "customer_score"]
    search_fields = ["first_name", "last_name", "email", "phone"]
    ordering_fields = ["created_at", "customer_score", "total_reservations"]
    ordering = ["-created_at"]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return CustomerCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return CustomerUpdateSerializer
        elif self.action == "stats":
            return CustomerStatsSerializer
        return CustomerSerializer

    def get_throttles(self):
        """Apply different throttles based on action"""
        if self.action == "create":
            throttle_classes = [CustomerThrottle]
        else:
            throttle_classes = [AnonRateThrottle, UserRateThrottle]
        return [throttle() for throttle in throttle_classes]

    def get_permissions(self):
        """Set permissions based on action"""
        # Allow all actions for development
        permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Optimize queryset with select_related"""
        queryset = Customer.objects.select_related("user")

        # Filter by score range if provided
        min_score = self.request.query_params.get("min_score")
        if min_score:
            try:
                queryset = queryset.filter(customer_score__gte=int(min_score))
            except ValueError:
                pass

        return queryset

    def perform_create(self, serializer):
        """Create customer with enhanced logging"""
        try:
            customer = serializer.save()
            logger.info(
                f"New customer created: {customer.full_name} ({customer.email})"
            )
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            raise

    def perform_update(self, serializer):
        """Update customer with stat refresh"""
        old_customer = self.get_object()
        customer = serializer.save()

        # Log significant changes
        if old_customer.is_active != customer.is_active:
            status_msg = "activated" if customer.is_active else "deactivated"
            logger.info(f"Customer {customer.full_name} {status_msg}")

        # Refresh statistics if needed
        if customer.total_reservations > 0:
            customer.update_stats()

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get customer statistics overview"""
        queryset = self.get_queryset()

        stats = {
            "total_customers": queryset.count(),
            "active_customers": queryset.filter(is_active=True).count(),
            "high_score_customers": queryset.filter(customer_score__gte=80).count(),
            "low_score_customers": queryset.filter(customer_score__lt=50).count(),
            "customers_with_reservations": queryset.filter(
                total_reservations__gt=0
            ).count(),
            "average_score": queryset.aggregate(avg_score=Avg("customer_score"))[
                "avg_score"
            ]
            or 0,
        }

        return Response(stats)

    @action(detail=True, methods=["get"])
    def reservation_history(self, request, pk=None):
        """Get detailed reservation history for a customer"""
        customer = self.get_object()
        serializer = CustomerReservationHistorySerializer(customer)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def refresh_stats(self, request, pk=None):
        """Manually refresh customer statistics"""
        customer = self.get_object()

        try:
            customer.update_stats()
            return Response(
                {
                    "message": "Estadísticas actualizadas exitosamente",
                    "total_reservations": customer.total_reservations,
                    "customer_score": customer.customer_score,
                    "reliability_score": customer.reliability_score,
                }
            )
        except Exception as e:
            logger.error(f"Error refreshing stats for customer {customer.id}: {e}")
            return Response(
                {"error": "Error actualizando estadísticas"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        """Toggle customer active status with validation"""
        customer = self.get_object()

        # Prevent reactivation of customers with very low scores
        if not customer.is_active and customer.customer_score < 20:
            return Response(
                {
                    "error": "No se puede reactivar cliente con puntuación menor a 20",
                    "current_score": customer.customer_score,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer.is_active = not customer.is_active
        customer.save()

        action_msg = "activado" if customer.is_active else "desactivado"
        logger.info(f"Customer {customer.full_name} {action_msg}")

        return Response(
            {
                "message": f"Cliente {action_msg} exitosamente",
                "is_active": customer.is_active,
                "can_make_reservation": customer.can_make_reservation(),
            }
        )

    @action(detail=False, methods=["get"])
    def search_by_phone(self, request):
        """Search customer by phone number"""
        phone = request.query_params.get("phone")
        if not phone:
            return Response(
                {"error": "Parámetro phone requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Clean phone for search
        cleaned_phone = (
            phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        )

        customers = Customer.objects.filter(
            Q(phone__icontains=cleaned_phone) | Q(phone__icontains=phone)
        )

        serializer = CustomerStatsSerializer(customers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def reliable_customers(self, request):
        """Get customers with high reliability scores"""
        min_score = int(request.query_params.get("min_score", 80))
        min_reservations = int(request.query_params.get("min_reservations", 5))

        customers = Customer.objects.filter(
            customer_score__gte=min_score,
            total_reservations__gte=min_reservations,
            is_active=True,
        ).order_by("-customer_score")

        serializer = CustomerStatsSerializer(customers, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Soft delete: deactivate instead of deleting"""
        customer = self.get_object()

        # Check if customer has active reservations
        from reservations.models import Reservation

        active_reservations = Reservation.objects.filter(
            customer=customer, status__in=["pending", "confirmed"]
        ).count()

        if active_reservations > 0:
            return Response(
                {
                    "error": f"No se puede eliminar cliente con {active_reservations} reservas activas",
                    "suggestion": "Cancele las reservas activas primero o use toggle_active para desactivar",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Soft delete by deactivating
        customer.is_active = False
        customer.save()

        logger.info(f"Customer {customer.full_name} soft deleted (deactivated)")

        return Response(
            {
                "message": "Cliente desactivado exitosamente",
                "note": "Los datos se conservan para referencias históricas",
            }
        )
