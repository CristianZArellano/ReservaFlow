import logging
from datetime import date, timedelta
from django.db.models import Q, Count, Avg
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django_filters.rest_framework import DjangoFilterBackend

from .models import Restaurant, Table
from .serializers import (
    RestaurantSerializer,
    RestaurantCreateSerializer,
    RestaurantListSerializer,
    RestaurantStatsSerializer,
    RestaurantWithTablesSerializer,
    TableSerializer,
    TableCreateSerializer,
    TableAvailabilitySerializer,
    RestaurantSearchSerializer,
)

logger = logging.getLogger(__name__)


class RestaurantThrottle(UserRateThrottle):
    """Custom throttling for restaurant operations"""

    scope = "restaurant"


class RestaurantViewSet(viewsets.ModelViewSet):
    """Complete ViewSet for Restaurant CRUD operations"""

    queryset = Restaurant.objects.all()
    filterset_fields = ["is_active", "cuisine_type", "price_range", "accepts_walk_ins"]
    search_fields = ["name", "description", "address", "cuisine_type"]
    ordering_fields = ["created_at", "name", "average_rating", "total_capacity"]
    ordering = ["name"]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return RestaurantCreateSerializer
        elif self.action == "list":
            return RestaurantListSerializer
        elif self.action == "stats":
            return RestaurantStatsSerializer
        elif self.action == "with_tables":
            return RestaurantWithTablesSerializer
        return RestaurantSerializer

    def get_throttles(self):
        """Apply different throttles based on action"""
        if self.action == "create":
            throttle_classes = [RestaurantThrottle]
        else:
            throttle_classes = [AnonRateThrottle, UserRateThrottle]
        return [throttle() for throttle in throttle_classes]

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ["list", "retrieve", "search", "available_tables", "stats"]:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Optimize queryset and apply filters"""
        queryset = Restaurant.objects.all()

        # Apply custom filters
        cuisine = self.request.query_params.get("cuisine")
        if cuisine:
            queryset = queryset.filter(cuisine_type=cuisine)

        min_rating = self.request.query_params.get("min_rating")
        if min_rating:
            try:
                queryset = queryset.filter(average_rating__gte=float(min_rating))
            except ValueError:
                pass

        # Filter by capacity
        min_capacity = self.request.query_params.get("min_capacity")
        if min_capacity:
            try:
                queryset = queryset.filter(total_capacity__gte=int(min_capacity))
            except ValueError:
                pass

        return queryset

    def perform_create(self, serializer):
        """Create restaurant with enhanced logging"""
        try:
            restaurant = serializer.save()
            logger.info(f"New restaurant created: {restaurant.name}")
        except Exception as e:
            logger.error(f"Error creating restaurant: {e}")
            raise

    def perform_update(self, serializer):
        """Update restaurant with capacity refresh"""
        restaurant = serializer.save()
        restaurant.update_total_capacity()
        logger.info(f"Restaurant updated: {restaurant.name}")

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get restaurant statistics overview"""
        queryset = self.get_queryset()

        stats = {
            "total_restaurants": queryset.count(),
            "active_restaurants": queryset.filter(is_active=True).count(),
            "by_cuisine": dict(
                queryset.values("cuisine_type")
                .annotate(count=Count("id"))
                .values_list("cuisine_type", "count")
            ),
            "by_price_range": dict(
                queryset.values("price_range")
                .annotate(count=Count("id"))
                .values_list("price_range", "count")
            ),
            "average_capacity": queryset.aggregate(avg_capacity=Avg("total_capacity"))[
                "avg_capacity"
            ]
            or 0,
            "average_rating": queryset.aggregate(avg_rating=Avg("average_rating"))[
                "avg_rating"
            ]
            or 0,
            "accepts_walk_ins": queryset.filter(accepts_walk_ins=True).count(),
        }

        return Response(stats)

    @action(detail=True, methods=["get"])
    def with_tables(self, request, pk=None):
        """Get restaurant with all its tables"""
        restaurant = self.get_object()
        serializer = RestaurantWithTablesSerializer(restaurant)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def available_tables(self, request, pk=None):
        """Check table availability for a specific date and time"""
        restaurant = self.get_object()

        # Validate query parameters
        serializer = TableAvailabilitySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        check_date = data["date"]
        check_time = data["time"]
        party_size = data["party_size"]
        location_preference = data.get("location_preference")
        requires_accessibility = data.get("requires_accessibility", False)
        prefers_quiet = data.get("prefers_quiet", False)

        # Check if restaurant is open on that day
        if not restaurant.is_open_on_day(check_date.weekday()):
            return Response(
                {
                    "available_tables": [],
                    "restaurant_is_open": False,
                    "message": f"El restaurante está cerrado los {['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábados', 'domingos'][check_date.weekday()]}",
                }
            )

        # Check if time is within operating hours
        if not (restaurant.opening_time <= check_time <= restaurant.closing_time):
            return Response(
                {
                    "available_tables": [],
                    "restaurant_is_open": False,
                    "message": f"Horario fuera del rango de operación ({restaurant.opening_time} - {restaurant.closing_time})",
                }
            )

        # Find suitable tables
        suitable_tables = restaurant.tables.filter(
            is_active=True, min_capacity__lte=party_size, capacity__gte=party_size
        )

        # Apply preferences
        if location_preference:
            suitable_tables = suitable_tables.filter(location=location_preference)

        if requires_accessibility:
            suitable_tables = suitable_tables.filter(is_accessible=True)

        if prefers_quiet:
            suitable_tables = suitable_tables.filter(is_quiet=True)

        # Check availability for each table
        available_tables = []
        for table in suitable_tables:
            if table.is_available_at_time(check_date, check_time):
                available_tables.append(table)

        # Generate suggestions if no tables available
        suggestions = []
        if not available_tables:
            # Suggest alternative times (±2 hours)
            for time_offset in [-120, -60, 60, 120]:  # minutes
                alt_time_minutes = (
                    check_time.hour * 60 + check_time.minute + time_offset
                )
                if 0 <= alt_time_minutes < 24 * 60:
                    alt_hours, alt_minutes = divmod(alt_time_minutes, 60)
                    alt_time = check_time.replace(hour=alt_hours, minute=alt_minutes)

                    if restaurant.opening_time <= alt_time <= restaurant.closing_time:
                        alt_available = sum(
                            1
                            for table in suitable_tables
                            if table.is_available_at_time(check_date, alt_time)
                        )
                        if alt_available > 0:
                            suggestions.append(
                                {
                                    "date": check_date.isoformat(),
                                    "time": alt_time.strftime("%H:%M"),
                                    "available_tables": alt_available,
                                }
                            )

        response_data = {
            "available_tables": TableSerializer(available_tables, many=True).data,
            "restaurant_is_open": True,
            "message": f"Se encontraron {len(available_tables)} mesas disponibles"
            if available_tables
            else "No hay mesas disponibles para ese horario",
            "suggested_alternatives": suggestions[:3],  # Limit to 3 suggestions
        }

        return Response(response_data)

    @action(detail=True, methods=["post"])
    def update_capacity(self, request, pk=None):
        """Manually refresh restaurant total capacity"""
        restaurant = self.get_object()

        old_capacity = restaurant.total_capacity
        restaurant.update_total_capacity()
        restaurant.refresh_from_db()

        return Response(
            {
                "message": "Capacidad actualizada exitosamente",
                "old_capacity": old_capacity,
                "new_capacity": restaurant.total_capacity,
                "active_tables": restaurant.tables.filter(is_active=True).count(),
            }
        )

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Advanced restaurant search with filters"""
        serializer = RestaurantSearchSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        filters = serializer.validated_data
        queryset = Restaurant.objects.filter(is_active=True)

        # Apply filters
        if filters.get("cuisine_type"):
            queryset = queryset.filter(cuisine_type=filters["cuisine_type"])

        if filters.get("price_range"):
            queryset = queryset.filter(price_range=filters["price_range"])

        if filters.get("min_capacity"):
            queryset = queryset.filter(total_capacity__gte=filters["min_capacity"])

        if filters.get("accepts_walk_ins") is not None:
            queryset = queryset.filter(accepts_walk_ins=filters["accepts_walk_ins"])

        if filters.get("min_rating"):
            queryset = queryset.filter(average_rating__gte=filters["min_rating"])

        if filters.get("location"):
            queryset = queryset.filter(
                Q(address__icontains=filters["location"])
                | Q(name__icontains=filters["location"])
            )

        # Order by rating and capacity
        queryset = queryset.order_by("-average_rating", "-total_capacity")

        serializer = RestaurantListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        """Toggle restaurant active status"""
        restaurant = self.get_object()

        restaurant.is_active = not restaurant.is_active
        restaurant.save()

        action_msg = "activado" if restaurant.is_active else "desactivado"
        logger.info(f"Restaurant {restaurant.name} {action_msg}")

        return Response(
            {
                "message": f"Restaurante {action_msg} exitosamente",
                "is_active": restaurant.is_active,
            }
        )


class TableViewSet(viewsets.ModelViewSet):
    """Complete ViewSet for Table CRUD operations"""

    queryset = Table.objects.all()
    filterset_fields = ["restaurant", "is_active", "location", "capacity"]
    search_fields = ["number", "special_notes"]
    ordering_fields = ["number", "capacity", "created_at"]
    ordering = ["restaurant", "number"]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return TableCreateSerializer
        return TableSerializer

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ["list", "retrieve"]:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Optimize queryset with select_related"""
        queryset = Table.objects.select_related("restaurant")

        # Filter by restaurant if specified
        restaurant_id = self.request.query_params.get("restaurant_id")
        if restaurant_id:
            try:
                queryset = queryset.filter(restaurant_id=int(restaurant_id))
            except ValueError:
                pass

        # Filter by capacity range
        min_capacity = self.request.query_params.get("min_capacity")
        max_capacity = self.request.query_params.get("max_capacity")

        if min_capacity:
            try:
                queryset = queryset.filter(capacity__gte=int(min_capacity))
            except ValueError:
                pass

        if max_capacity:
            try:
                queryset = queryset.filter(capacity__lte=int(max_capacity))
            except ValueError:
                pass

        return queryset

    def perform_create(self, serializer):
        """Create table with enhanced logging"""
        try:
            table = serializer.save()
            logger.info(f"New table created: {table.number} at {table.restaurant.name}")
            # Update restaurant capacity
            table.restaurant.update_total_capacity()
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            raise

    def perform_update(self, serializer):
        """Update table with capacity refresh"""
        table = serializer.save()
        table.restaurant.update_total_capacity()
        logger.info(f"Table updated: {table.number} at {table.restaurant.name}")

    def perform_destroy(self, instance):
        """Soft delete table by deactivating"""
        instance.is_active = False
        instance.save()
        instance.restaurant.update_total_capacity()
        logger.info(
            f"Table {instance.number} at {instance.restaurant.name} deactivated"
        )

    @action(detail=True, methods=["get"])
    def availability(self, request, pk=None):
        """Check availability for a specific table over a date range"""
        table = self.get_object()

        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if not start_date_str:
            start_date = date.today()
        else:
            try:
                start_date = date.fromisoformat(start_date_str)
            except ValueError:
                return Response(
                    {"error": "Invalid start_date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not end_date_str:
            end_date = start_date + timedelta(days=7)
        else:
            try:
                end_date = date.fromisoformat(end_date_str)
            except ValueError:
                return Response(
                    {"error": "Invalid end_date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Generate availability data
        availability = []
        current_date = start_date

        while current_date <= end_date:
            day_availability = {
                "date": current_date.isoformat(),
                "is_restaurant_open": table.restaurant.is_open_on_day(
                    current_date.weekday()
                ),
                "available_times": [],
            }

            if day_availability["is_restaurant_open"]:
                available_times = table.restaurant.get_available_times(current_date)
                for time_slot in available_times:
                    is_available = table.is_available_at_time(current_date, time_slot)
                    day_availability["available_times"].append(
                        {"time": time_slot.strftime("%H:%M"), "available": is_available}
                    )

            availability.append(day_availability)
            current_date += timedelta(days=1)

        return Response(
            {"table": TableSerializer(table).data, "availability": availability}
        )

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        """Toggle table active status"""
        table = self.get_object()

        # Check for active reservations
        from reservations.models import Reservation

        active_reservations = Reservation.objects.filter(
            table=table, status__in=["pending", "confirmed"]
        ).count()

        if not table.is_active and active_reservations > 0:
            return Response(
                {
                    "error": f"No se puede desactivar mesa con {active_reservations} reservas activas",
                    "suggestion": "Cancele las reservas activas primero",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        table.is_active = not table.is_active
        table.save()

        # Update restaurant capacity
        table.restaurant.update_total_capacity()

        action_msg = "activada" if table.is_active else "desactivada"
        logger.info(f"Table {table.number} at {table.restaurant.name} {action_msg}")

        return Response(
            {"message": f"Mesa {action_msg} exitosamente", "is_active": table.is_active}
        )
