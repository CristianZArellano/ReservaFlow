"""
Django REST Framework Serializers for Reservations
"""

from datetime import date, time

from customers.models import Customer
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from restaurants.models import Restaurant, Table

from .models import Reservation


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model"""

    class Meta:
        model = Customer
        fields = ["id", "first_name", "last_name", "email", "phone"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        """Validate email uniqueness"""
        if self.instance and self.instance.email == value:
            return value

        if Customer.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un cliente con este email.")
        return value


class RestaurantSerializer(serializers.ModelSerializer):
    """Serializer for Restaurant model"""

    class Meta:
        model = Restaurant
        fields = ["id", "name", "address", "phone", "opening_time", "closing_time"]
        read_only_fields = ["id"]


class TableSerializer(serializers.ModelSerializer):
    """Serializer for Table model"""

    restaurant = RestaurantSerializer(read_only=True)

    class Meta:
        model = Table
        fields = ["id", "number", "capacity", "location", "restaurant"]
        read_only_fields = ["id"]


class ReservationSerializer(serializers.ModelSerializer):
    """Main serializer for Reservation with comprehensive validation"""

    # Nested serializers for read operations
    customer = CustomerSerializer(read_only=True)
    restaurant = RestaurantSerializer(read_only=True)
    table = TableSerializer(read_only=True)

    # Write-only fields for creation
    customer_id = serializers.IntegerField(write_only=True)
    restaurant_id = serializers.IntegerField(write_only=True)
    table_id = serializers.IntegerField(write_only=True)

    # Custom fields
    reservation_datetime = serializers.DateTimeField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "customer",
            "restaurant",
            "table",
            "customer_id",
            "restaurant_id",
            "table_id",
            "reservation_date",
            "reservation_time",
            "party_size",
            "status",
            "created_at",
            "updated_at",
            "expires_at",
            "reservation_datetime",
            "is_expired",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "expires_at"]

    def validate_reservation_date(self, value):
        """Enhanced validation for reservation date with timezone awareness"""
        if not isinstance(value, date):
            raise serializers.ValidationError(
                "Fecha de reserva debe ser una fecha válida."
            )

        # Use timezone-aware current date
        now = timezone.now()
        today = now.date()

        if value < today:
            raise serializers.ValidationError(
                "No se pueden hacer reservas en fechas pasadas."
            )

        # For today's reservations, validate against current time when time is available
        if value == today and hasattr(self, "initial_data"):
            reservation_time = self.initial_data.get("reservation_time")
            if reservation_time:
                try:
                    from datetime import time as dt_time

                    if isinstance(reservation_time, str):
                        # Parse time string (HH:MM format)
                        time_parts = reservation_time.split(":")
                        if len(time_parts) == 2:
                            hour, minute = int(time_parts[0]), int(time_parts[1])
                            reservation_time_obj = dt_time(hour, minute)

                            # Allow at least 2 hours advance notice for same-day reservations
                            min_advance_time = (
                                now + timezone.timedelta(hours=2)
                            ).time()
                            if reservation_time_obj < min_advance_time:
                                raise serializers.ValidationError(
                                    f"Las reservas para hoy deben hacerse con al menos 2 horas de anticipación. "
                                    f"Hora mínima disponible: {min_advance_time.strftime('%H:%M')}"
                                )
                except (ValueError, AttributeError):
                    # Invalid time format - let time validation handle it
                    pass

        # Máximo 90 días de anticipación
        max_future_date = today + timezone.timedelta(days=90)
        if value > max_future_date:
            raise serializers.ValidationError(
                "No se pueden hacer reservas con más de 90 días de anticipación."
            )

        return value

    def validate_reservation_time(self, value):
        """Enhanced validation for reservation time with timezone and business rules"""
        if not isinstance(value, time):
            raise serializers.ValidationError(
                "Hora de reserva debe ser una hora válida."
            )

        # Horarios de operación (esto podría venir del restaurante en el futuro)
        opening_time = time(10, 0)  # 10:00 AM
        closing_time = time(22, 0)  # 10:00 PM

        if not (opening_time <= value <= closing_time):
            raise serializers.ValidationError(
                f"Horario de reserva debe ser entre {opening_time.strftime('%H:%M')} y {closing_time.strftime('%H:%M')}."
            )

        # Validate time slots (reservations only allowed at 15-minute intervals)
        if value.minute % 15 != 0:
            raise serializers.ValidationError(
                "Las reservas solo se permiten en intervalos de 15 minutos "
                "(por ejemplo: 12:00, 12:15, 12:30, 12:45)."
            )

        # Validate seconds are zero (no seconds allowed)
        if value.second != 0 or value.microsecond != 0:
            raise serializers.ValidationError(
                "La hora debe especificarse sin segundos (formato HH:MM)."
            )

        return value

    def validate_party_size(self, value):
        """Validate party size is reasonable"""
        if value < 1:
            raise serializers.ValidationError(
                "El número de personas debe ser al menos 1."
            )

        if value > 12:
            raise serializers.ValidationError(
                "El número máximo de personas por reserva es 12."
            )

        return value

    def validate_customer_id(self, value):
        """Validate customer exists"""
        try:
            Customer.objects.get(id=value)
            return value
        except Customer.DoesNotExist:
            raise serializers.ValidationError("Cliente no encontrado.")

    def validate_restaurant_id(self, value):
        """Validate restaurant exists and is active"""
        try:
            Restaurant.objects.get(id=value, is_active=True)
            return value
        except Restaurant.DoesNotExist:
            raise serializers.ValidationError(
                "Restaurante no encontrado o no está activo."
            )

    def validate_table_id(self, value):
        """Validate table exists and is active"""
        try:
            Table.objects.get(id=value, is_active=True)
            return value
        except Table.DoesNotExist:
            raise serializers.ValidationError("Mesa no encontrada o no está activa.")

    def validate(self, attrs):
        """Cross-field validation"""
        # Validate table belongs to restaurant
        if "table_id" in attrs and "restaurant_id" in attrs:
            try:
                table = Table.objects.get(id=attrs["table_id"])
                if table.restaurant_id != attrs["restaurant_id"]:
                    raise serializers.ValidationError(
                        {
                            "table_id": "La mesa no pertenece al restaurante seleccionado."
                        }
                    )
            except Table.DoesNotExist:
                pass  # Will be caught by individual field validation

        # Validate party size fits table capacity
        if "table_id" in attrs and "party_size" in attrs:
            try:
                table = Table.objects.get(id=attrs["table_id"])
                if attrs["party_size"] > table.capacity:
                    raise serializers.ValidationError(
                        {
                            "party_size": f"La mesa {table.number} tiene capacidad para {table.capacity} personas."
                        }
                    )
            except Table.DoesNotExist:
                pass  # Will be caught by individual field validation

        # Enhanced datetime validation with timezone awareness
        if all(k in attrs for k in ["reservation_date", "reservation_time"]):
            # Combine date and time for timezone validation
            reservation_datetime = timezone.datetime.combine(
                attrs["reservation_date"], attrs["reservation_time"]
            )

            # Make timezone-aware
            reservation_datetime = timezone.make_aware(reservation_datetime)
            current_datetime = timezone.now()

            # Validate reservation is not in the past (more precise than date-only check)
            if reservation_datetime <= current_datetime:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            f"La reserva no puede ser en el pasado. "
                            f"Fecha/hora actual: {current_datetime.strftime('%Y-%m-%d %H:%M')}"
                        ]
                    }
                )

            # Validate minimum advance notice (2 hours for same day, 30 minutes for future days)
            time_diff = reservation_datetime - current_datetime
            min_advance = (
                timezone.timedelta(hours=2)
                if reservation_datetime.date() == current_datetime.date()
                else timezone.timedelta(minutes=30)
            )

            if time_diff < min_advance:
                advance_str = (
                    "2 horas"
                    if reservation_datetime.date() == current_datetime.date()
                    else "30 minutos"
                )
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            f"Las reservas deben hacerse con al menos {advance_str} de anticipación."
                        ]
                    }
                )

        # Check for double booking (basic validation - the model will handle the final check)
        if all(
            k in attrs for k in ["table_id", "reservation_date", "reservation_time"]
        ):
            conflicting_reservations = Reservation.objects.filter(
                table_id=attrs["table_id"],
                reservation_date=attrs["reservation_date"],
                reservation_time=attrs["reservation_time"],
                status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED],
            )

            # Exclude current instance if updating
            if self.instance:
                conflicting_reservations = conflicting_reservations.exclude(
                    pk=self.instance.pk
                )

            if conflicting_reservations.exists():
                conflict = conflicting_reservations.first()
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            f"Ya existe una reserva para esta mesa en la fecha y hora especificadas. "
                            f"Reserva existente: {conflict.id.hex[:8]}"
                        ]
                    }
                )

        return attrs

    def create(self, validated_data):
        """Create reservation with proper error handling"""
        try:
            return super().create(validated_data)
        except DjangoValidationError as e:
            # Convert Django validation errors to DRF format
            if hasattr(e, "error_dict"):
                raise serializers.ValidationError(e.error_dict)
            else:
                raise serializers.ValidationError({"non_field_errors": [str(e)]})

    def update(self, instance, validated_data):
        """Update reservation with proper error handling"""
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as e:
            # Convert Django validation errors to DRF format
            if hasattr(e, "error_dict"):
                raise serializers.ValidationError(e.error_dict)
            else:
                raise serializers.ValidationError({"non_field_errors": [str(e)]})


class ReservationCreateSerializer(ReservationSerializer):
    """Specialized serializer for reservation creation"""

    def to_representation(self, instance):
        """Return full representation after creation"""
        return ReservationSerializer(instance, context=self.context).data


class ReservationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for reservation lists"""

    customer_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    table_number = serializers.SerializerMethodField()
    reservation_datetime = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "customer_name",
            "restaurant_name",
            "table_number",
            "reservation_date",
            "reservation_time",
            "reservation_datetime",
            "party_size",
            "status",
            "created_at",
        ]

    def get_customer_name(self, obj):
        return (
            f"{obj.customer.first_name} {obj.customer.last_name}"
            if obj.customer
            else None
        )

    def get_restaurant_name(self, obj):
        return obj.restaurant.name if obj.restaurant else None

    def get_table_number(self, obj):
        return obj.table.number if obj.table else None


class ReservationStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for status-only updates"""

    class Meta:
        model = Reservation
        fields = ["status"]

    def validate_status(self, value):
        """Validate status transitions"""
        if not self.instance:
            return value

        current_status = self.instance.status

        # Define allowed transitions
        allowed_transitions = {
            Reservation.Status.PENDING: [
                Reservation.Status.CONFIRMED,
                Reservation.Status.CANCELLED,
                Reservation.Status.EXPIRED,
            ],
            Reservation.Status.CONFIRMED: [
                Reservation.Status.COMPLETED,
                Reservation.Status.CANCELLED,
                Reservation.Status.NO_SHOW,
            ],
            # Terminal states - no transitions allowed
            Reservation.Status.COMPLETED: [],
            Reservation.Status.CANCELLED: [],
            Reservation.Status.NO_SHOW: [],
            Reservation.Status.EXPIRED: [],
        }

        if value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"No se puede cambiar el estado de '{current_status}' a '{value}'."
            )

        return value
