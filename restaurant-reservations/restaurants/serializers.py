from datetime import time, datetime
from rest_framework import serializers
from .models import Restaurant, Table


class RestaurantSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Restaurant model"""

    # Computed fields
    operating_days = serializers.ListField(read_only=True)
    available_times = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "description",
            "cuisine_type",
            "price_range",
            "address",
            "phone",
            "email",
            "website",
            "opening_time",
            "closing_time",
            "monday_open",
            "tuesday_open",
            "wednesday_open",
            "thursday_open",
            "friday_open",
            "saturday_open",
            "sunday_open",
            "operating_days",
            "reservation_duration",
            "advance_booking_days",
            "min_party_size",
            "max_party_size",
            "accepts_walk_ins",
            "requires_deposit",
            "cancellation_hours",
            "total_capacity",
            "average_rating",
            "total_reservations",
            "is_active",
            "created_at",
            "updated_at",
            "available_times",
        ]
        read_only_fields = [
            "id",
            "total_capacity",
            "total_reservations",
            "created_at",
            "updated_at",
        ]

    def get_available_times(self, obj):
        """Get available time slots for today (or next available day)"""
        # For API response efficiency, return times for today if open, else next open day
        today = datetime.now().date()
        if obj.is_open_on_day(today.weekday()):
            times = obj.get_available_times(today)
            return [t.strftime("%H:%M") for t in times]

        # Find next open day
        for i in range(1, 8):  # Check next 7 days
            next_day = today + datetime.timedelta(days=i)
            if obj.is_open_on_day(next_day.weekday()):
                times = obj.get_available_times(next_day)
                return {
                    "date": next_day.isoformat(),
                    "times": [t.strftime("%H:%M") for t in times],
                }

        return []

    def validate_opening_time(self, value):
        """Validate opening time is reasonable"""
        if value < time(6, 0) or value > time(12, 0):
            raise serializers.ValidationError(
                "Hora de apertura debe estar entre 6:00 AM y 12:00 PM"
            )
        return value

    def validate_closing_time(self, value):
        """Validate closing time is reasonable"""
        if value < time(14, 0) or value > time(23, 59):
            raise serializers.ValidationError(
                "Hora de cierre debe estar entre 2:00 PM y 11:59 PM"
            )
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        # Validate operating hours
        opening = attrs.get(
            "opening_time", self.instance.opening_time if self.instance else None
        )
        closing = attrs.get(
            "closing_time", self.instance.closing_time if self.instance else None
        )

        if opening and closing and opening >= closing:
            raise serializers.ValidationError(
                {
                    "closing_time": "La hora de cierre debe ser posterior a la de apertura"
                }
            )

        # Validate party sizes
        min_party = attrs.get(
            "min_party_size", self.instance.min_party_size if self.instance else None
        )
        max_party = attrs.get(
            "max_party_size", self.instance.max_party_size if self.instance else None
        )

        if min_party and max_party and min_party > max_party:
            raise serializers.ValidationError(
                {"max_party_size": "El máximo de personas debe ser mayor al mínimo"}
            )

        # Validate at least one day is open
        days_open = [
            attrs.get(
                "monday_open", self.instance.monday_open if self.instance else True
            ),
            attrs.get(
                "tuesday_open", self.instance.tuesday_open if self.instance else True
            ),
            attrs.get(
                "wednesday_open",
                self.instance.wednesday_open if self.instance else True,
            ),
            attrs.get(
                "thursday_open", self.instance.thursday_open if self.instance else True
            ),
            attrs.get(
                "friday_open", self.instance.friday_open if self.instance else True
            ),
            attrs.get(
                "saturday_open", self.instance.saturday_open if self.instance else True
            ),
            attrs.get(
                "sunday_open", self.instance.sunday_open if self.instance else False
            ),
        ]

        if not any(days_open):
            raise serializers.ValidationError(
                "El restaurante debe estar abierto al menos un día de la semana"
            )

        return attrs


class RestaurantCreateSerializer(RestaurantSerializer):
    """Serializer for restaurant creation with required fields"""

    class Meta(RestaurantSerializer.Meta):
        extra_kwargs = {
            "name": {"required": True},
            "address": {"required": True},
            "phone": {"required": True},
            "email": {"required": True},
        }


class RestaurantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for restaurant listings"""

    operating_days = serializers.ListField(read_only=True)

    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "cuisine_type",
            "price_range",
            "address",
            "phone",
            "opening_time",
            "closing_time",
            "operating_days",
            "total_capacity",
            "average_rating",
            "accepts_walk_ins",
            "is_active",
        ]
        read_only_fields = "__all__"


class TableSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Table model"""

    # Nested restaurant info (read-only)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    # Computed fields
    features_list = serializers.ListField(read_only=True)
    capacity_range_display = serializers.CharField(read_only=True)

    class Meta:
        model = Table
        fields = [
            "id",
            "restaurant",
            "restaurant_name",
            "number",
            "capacity",
            "min_capacity",
            "location",
            "shape",
            "has_view",
            "is_accessible",
            "is_quiet",
            "has_high_chairs",
            "requires_special_request",
            "special_notes",
            "features_list",
            "capacity_range_display",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_capacity(self, value):
        """Validate table capacity is reasonable"""
        if value < 1:
            raise serializers.ValidationError("La capacidad debe ser al menos 1")
        if value > 20:
            raise serializers.ValidationError("La capacidad máxima es 20 personas")
        return value

    def validate_min_capacity(self, value):
        """Validate minimum capacity"""
        if value < 1:
            raise serializers.ValidationError("La capacidad mínima debe ser al menos 1")
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        min_cap = attrs.get(
            "min_capacity", self.instance.min_capacity if self.instance else 1
        )
        max_cap = attrs.get(
            "capacity", self.instance.capacity if self.instance else None
        )

        if min_cap and max_cap and min_cap > max_cap:
            raise serializers.ValidationError(
                {"capacity": "La capacidad máxima debe ser mayor o igual a la mínima"}
            )

        # Validate unique number per restaurant
        restaurant = attrs.get(
            "restaurant", self.instance.restaurant if self.instance else None
        )
        number = attrs.get("number", self.instance.number if self.instance else None)

        if restaurant and number:
            existing = Table.objects.filter(
                restaurant=restaurant, number=number.upper()
            )
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise serializers.ValidationError(
                    {
                        "number": f"Ya existe una mesa con número {number} en este restaurante"
                    }
                )

        return attrs


class TableCreateSerializer(TableSerializer):
    """Serializer for table creation with required fields"""

    class Meta(TableSerializer.Meta):
        extra_kwargs = {
            "restaurant": {"required": True},
            "number": {"required": True},
            "capacity": {"required": True},
        }


class TableAvailabilitySerializer(serializers.Serializer):
    """Serializer for checking table availability"""

    date = serializers.DateField()
    time = serializers.TimeField()
    party_size = serializers.IntegerField(min_value=1, max_value=20)
    location_preference = serializers.ChoiceField(
        choices=Table.LOCATION_CHOICES, required=False, allow_blank=True
    )
    requires_accessibility = serializers.BooleanField(default=False)
    prefers_quiet = serializers.BooleanField(default=False)

    def validate_date(self, value):
        """Validate date is not in the past"""
        from datetime import date

        if value < date.today():
            raise serializers.ValidationError("La fecha no puede ser en el pasado")
        return value


class RestaurantStatsSerializer(serializers.ModelSerializer):
    """Serializer for restaurant statistics"""

    operating_days = serializers.ListField(read_only=True)
    table_count = serializers.SerializerMethodField()
    occupancy_rate = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "cuisine_type",
            "total_capacity",
            "table_count",
            "total_reservations",
            "average_rating",
            "operating_days",
            "occupancy_rate",
            "is_active",
        ]
        read_only_fields = "__all__"

    def get_table_count(self, obj):
        """Get number of active tables"""
        return obj.tables.filter(is_active=True).count()

    def get_occupancy_rate(self, obj):
        """Calculate occupancy rate for the last 30 days"""
        from datetime import date, timedelta
        from reservations.models import Reservation

        thirty_days_ago = date.today() - timedelta(days=30)

        total_slots = obj.total_capacity * 30  # Simplified calculation
        if total_slots == 0:
            return 0

        confirmed_reservations = Reservation.objects.filter(
            restaurant=obj, reservation_date__gte=thirty_days_ago, status="confirmed"
        ).count()

        return min(100, (confirmed_reservations / max(total_slots, 1)) * 100)


class RestaurantWithTablesSerializer(RestaurantSerializer):
    """Restaurant serializer with nested tables"""

    tables = TableSerializer(many=True, read_only=True)
    active_tables = serializers.SerializerMethodField()

    class Meta(RestaurantSerializer.Meta):
        fields = RestaurantSerializer.Meta.fields + ["tables", "active_tables"]

    def get_active_tables(self, obj):
        """Get only active tables"""
        active_tables = obj.tables.filter(is_active=True)
        return TableSerializer(active_tables, many=True).data


class TableAvailabilityResponseSerializer(serializers.Serializer):
    """Response serializer for table availability check"""

    available_tables = TableSerializer(many=True, read_only=True)
    suggested_alternatives = serializers.SerializerMethodField()
    restaurant_is_open = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)

    def get_suggested_alternatives(self, obj):
        """Get suggested alternative times/dates if no tables available"""
        # This would be populated by the view with alternative suggestions
        return obj.get("suggested_alternatives", [])


class RestaurantSearchSerializer(serializers.Serializer):
    """Serializer for restaurant search parameters"""

    cuisine_type = serializers.ChoiceField(
        choices=Restaurant.CUISINE_CHOICES, required=False, allow_blank=True
    )
    price_range = serializers.ChoiceField(
        choices=Restaurant.PRICE_RANGE_CHOICES, required=False, allow_blank=True
    )
    min_capacity = serializers.IntegerField(min_value=1, required=False)
    location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    accepts_walk_ins = serializers.BooleanField(required=False)
    min_rating = serializers.DecimalField(
        max_digits=3, decimal_places=2, min_value=0, max_value=5, required=False
    )
