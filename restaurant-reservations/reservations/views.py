# reservations/views.py
import logging
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.core.cache import cache
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework.permissions import IsAuthenticated, AllowAny
from restaurants.services import TableReservationLock, LockAcquisitionError

from .models import Reservation
from .serializers import ReservationSerializer, ReservationCreateSerializer
from .tasks import send_confirmation_email, expire_reservation

logger = logging.getLogger(__name__)


class ReservationRateThrottle(UserRateThrottle):
    """Throttle específico para reservas"""

    scope = "reservation"


class ReservationViewSet(viewsets.ViewSet):
    """ViewSet para manejar reservas con lock distribuido robusto"""

    def get_throttles(self):
        """Aplicar diferentes throttles según la acción"""
        if self.action == "create":
            throttle_classes = [ReservationRateThrottle]
        else:
            throttle_classes = [AnonRateThrottle, UserRateThrottle]
        return [throttle() for throttle in throttle_classes]

    def get_permissions(self):
        """Permisos según acción"""
        # Allow all actions for development
        permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def list(self, request):
        """Listar reservas con serializer DRF"""
        reservations = Reservation.objects.select_related(
            "customer", "restaurant", "table"
        ).all()
        serializer = ReservationSerializer(reservations, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Obtener una reserva específica con serializer DRF"""
        try:
            reservation = Reservation.objects.select_related(
                "customer", "restaurant", "table"
            ).get(pk=pk)
            serializer = ReservationSerializer(reservation)
            return Response(serializer.data)
        except Reservation.DoesNotExist:
            return Response(
                {"error": "Reserva no encontrada"}, status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError:
            return Response(
                {"error": "ID de reserva inválido"}, status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request):
        """Crear reserva con serializer DRF y lock distribuido"""
        # Validar datos con serializer primero
        serializer = ReservationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        table_id = validated_data["table_id"]
        reservation_date = validated_data["reservation_date"]
        reservation_time = validated_data["reservation_time"]

        # Configurar lock con timeout más generoso para alta concurrencia
        lock_timeout = 45  # 45 segundos
        max_retries = 5  # Más intentos

        try:
            # Usar lock distribuido con parámetros robustos
            with TableReservationLock(
                table_id,
                reservation_date,
                reservation_time,
                timeout=lock_timeout,
                max_retries=max_retries,
            ) as lock:
                # Invalidar cache antes de verificar disponibilidad
                cache_key = (
                    f"availability:{table_id}:{reservation_date}:{reservation_time}"
                )
                cache.delete(cache_key)

                with transaction.atomic():
                    # Verificar disponibilidad con select_for_update para evitar race conditions
                    conflicts = (
                        Reservation.objects.select_for_update()
                        .filter(
                            table_id=table_id,
                            reservation_date=reservation_date,
                            reservation_time=reservation_time,
                            status__in=["pending", "confirmed"],
                        )
                        .exists()
                    )

                    if conflicts:
                        return Response(
                            {
                                "error": "Mesa no disponible en esa fecha/hora",
                                "details": "Otra reserva ya existe para este horario",
                            },
                            status=status.HTTP_409_CONFLICT,
                        )

                    # Crear reserva usando serializer (ya validado)
                    try:
                        reservation = serializer.save()

                        # Extender lock para envío de email asíncrono
                        lock.extend_lock(30)

                        # Programar email de confirmación (asíncrono)
                        try:
                            send_confirmation_email.apply_async(
                                args=[str(reservation.id)],
                                countdown=2,  # Pequeño delay para evitar que llegue antes que la respuesta
                            )
                            email_scheduled = True
                        except Exception as e:
                            logger.error(f"Error programando email: {e}")
                            email_scheduled = False

                        # Programar expiración automática si está en pending
                        if reservation.status == "pending" and reservation.expires_at:
                            try:
                                expire_reservation.apply_async(
                                    args=[str(reservation.id)],
                                    eta=reservation.expires_at,
                                )
                            except Exception as e:
                                logger.error(f"Error programando expiración: {e}")

                        # Serialize la reserva creada para respuesta
                        response_serializer = ReservationSerializer(reservation)
                        response_data = response_serializer.data
                        response_data.update(
                            {
                                "message": "Reserva creada exitosamente",
                                "email_scheduled": email_scheduled,
                            }
                        )

                        return Response(
                            response_data,
                            status=status.HTTP_201_CREATED,
                        )

                    except IntegrityError as ie:
                        # Constraint único violado a nivel de BD
                        logger.warning(f"Constraint violation: {ie}")
                        return Response(
                            {
                                "error": "Mesa ya reservada",
                                "details": "Otra reserva fue creada simultáneamente",
                            },
                            status=status.HTTP_409_CONFLICT,
                        )

                    except ValidationError as ve:
                        # Errores de validación del modelo Django
                        from rest_framework import serializers as drf_serializers

                        if hasattr(ve, "message_dict"):
                            # Convert Django ValidationError to DRF format
                            raise drf_serializers.ValidationError(ve.message_dict)
                        else:
                            raise drf_serializers.ValidationError(
                                {"non_field_errors": [str(ve)]}
                            )

                    except drf_serializers.ValidationError:
                        # Re-raise DRF validation errors
                        raise

        except LockAcquisitionError as lae:
            # Error específico de adquisición de lock
            logger.warning(f"Lock acquisition failed: {lae}")
            return Response(
                {
                    "error": "Mesa temporalmente no disponible",
                    "details": "Demasiada concurrencia - intente nuevamente en unos segundos",
                    "retry_after": 5,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        except Exception as e:
            # Error genérico - log detallado para debugging
            logger.error(f"Error inesperado creando reserva: {e}", exc_info=True)
            return Response(
                {
                    "error": "Error interno del servidor",
                    "details": "Por favor contacte al administrador si el problema persiste",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
