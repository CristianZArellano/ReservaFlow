from datetime import date
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Customer


class UserSerializer(serializers.ModelSerializer):
    """Serializer for Django User model"""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


class CustomerSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Customer model"""

    # Nested serializer for User (read-only)
    user = UserSerializer(read_only=True)

    # Computed fields
    full_name = serializers.CharField(read_only=True)
    reliability_score = serializers.IntegerField(read_only=True)
    can_make_reservation = serializers.BooleanField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "user",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "birth_date",
            "preferences",
            "allergies",
            "total_reservations",
            "cancelled_reservations",
            "no_show_count",
            "customer_score",
            "reliability_score",
            "is_active",
            "can_make_reservation",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_reservations",
            "cancelled_reservations",
            "no_show_count",
            "customer_score",
            "created_at",
            "updated_at",
        ]

    def validate_birth_date(self, value):
        """Validate birth date is reasonable"""
        if value:
            today = date.today()
            age = (
                today.year
                - value.year
                - ((today.month, today.day) < (value.month, value.day))
            )

            if value > today:
                raise serializers.ValidationError(
                    "La fecha de nacimiento no puede ser en el futuro."
                )

            if age < 16:
                raise serializers.ValidationError(
                    "Los menores de 16 años no pueden hacer reservas."
                )

            if age > 120:
                raise serializers.ValidationError("Fecha de nacimiento no válida.")

        return value

    def validate_email(self, value):
        """Validate email uniqueness"""
        # Check if email is being changed and if it already exists
        if self.instance and self.instance.email != value:
            if Customer.objects.filter(email=value).exists():
                raise serializers.ValidationError("Este email ya está registrado.")
        elif not self.instance and Customer.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email ya está registrado.")

        return value.lower().strip()

    def validate_phone(self, value):
        """Enhanced phone validation"""
        # Basic cleanup
        cleaned_phone = (
            value.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        )

        # Length validation
        if len(cleaned_phone) < 7 or len(cleaned_phone) > 15:
            raise serializers.ValidationError(
                "El teléfono debe tener entre 7 y 15 dígitos."
            )

        return value

    def validate(self, attrs):
        """Cross-field validation"""
        # Check if customer is trying to reactivate with poor score
        if attrs.get("is_active") and self.instance:
            if not self.instance.is_active and self.instance.customer_score < 20:
                raise serializers.ValidationError(
                    {
                        "is_active": "No se puede reactivar clientes con puntuación menor a 20."
                    }
                )

        return attrs


class CustomerCreateSerializer(CustomerSerializer):
    """Serializer for customer creation with required fields"""

    user_id = serializers.IntegerField(write_only=True, required=False)

    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + ["user_id"]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
            "phone": {"required": True},
        }

    def validate_user_id(self, value):
        """Validate user exists and is not already linked"""
        if value:
            try:
                user = User.objects.get(id=value)
                if hasattr(user, "customer"):
                    raise serializers.ValidationError(
                        "Este usuario ya está asociado a otro cliente."
                    )
                return value
            except User.DoesNotExist:
                raise serializers.ValidationError("Usuario no encontrado.")
        return value

    def create(self, validated_data):
        """Create customer with optional user association"""
        user_id = validated_data.pop("user_id", None)
        customer = Customer.objects.create(**validated_data)

        if user_id:
            user = User.objects.get(id=user_id)
            customer.user = user
            customer.save()

        return customer


class CustomerUpdateSerializer(CustomerSerializer):
    """Serializer for customer updates with optional fields"""

    class Meta(CustomerSerializer.Meta):
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
            "email": {"required": False},
            "phone": {"required": False},
        }


class CustomerStatsSerializer(serializers.ModelSerializer):
    """Lightweight serializer for customer statistics"""

    full_name = serializers.CharField(read_only=True)
    reliability_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "full_name",
            "email",
            "total_reservations",
            "cancelled_reservations",
            "no_show_count",
            "customer_score",
            "reliability_score",
            "is_active",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class CustomerReservationHistorySerializer(serializers.Serializer):
    """Serializer for customer reservation history with statistics"""

    customer = CustomerSerializer(read_only=True)
    reservations = serializers.SerializerMethodField()
    statistics = serializers.SerializerMethodField()

    def get_reservations(self, obj):
        """Get customer's reservation history"""
        from reservations.serializers import ReservationSerializer

        reservations = obj.reservation_set.all().order_by("-created_at")[:20]  # Last 20
        return ReservationSerializer(reservations, many=True).data

    def get_statistics(self, obj):
        """Get detailed statistics"""
        return {
            "total_reservations": obj.total_reservations,
            "cancelled_rate": (
                obj.cancelled_reservations / max(obj.total_reservations, 1)
            )
            * 100,
            "no_show_rate": (obj.no_show_count / max(obj.total_reservations, 1)) * 100,
            "completion_rate": obj.reliability_score,
            "customer_score": obj.customer_score,
            "can_make_reservation": obj.can_make_reservation(),
            "member_since": obj.created_at,
        }
