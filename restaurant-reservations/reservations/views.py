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
from .tasks import send_confirmation_email, expire_reservation

logger = logging.getLogger(__name__)


class ReservationRateThrottle(UserRateThrottle):
    """Throttle específico para reservas"""
    scope = 'reservation'


class ReservationViewSet(viewsets.ViewSet):
    """ViewSet para manejar reservas con lock distribuido robusto"""
    
    def get_throttles(self):
        """Aplicar diferentes throttles según la acción"""
        if self.action == 'create':
            throttle_classes = [ReservationRateThrottle]
        else:
            throttle_classes = [AnonRateThrottle, UserRateThrottle]
        return [throttle() for throttle in throttle_classes]
    
    def get_permissions(self):
        """Permisos según acción"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def list(self, request):
        """Listar reservas"""
        reservations = Reservation.objects.all()
        return Response(
            [
                {
                    "id": str(r.id),
                    "status": r.status,
                    "reservation_date": r.reservation_date,
                    "reservation_time": r.reservation_time,
                }
                for r in reservations
            ]
        )

    def retrieve(self, request, pk=None):
        """Obtener una reserva específica"""
        try:
            reservation = Reservation.objects.get(pk=pk)
            return Response(
                {
                    "id": str(reservation.id),
                    "status": reservation.status,
                    "expires_at": reservation.expires_at,
                }
            )
        except Reservation.DoesNotExist:
            return Response(
                {"error": "Reserva no encontrada"}, status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError:
            return Response(
                {"error": "ID de reserva inválido"}, status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request):
        """Crear reserva con manejo robusto de errores"""
        data = request.data
        table_id = data.get("table_id")
        reservation_date = data.get("reservation_date")
        reservation_time = data.get("reservation_time")

        if not all([table_id, reservation_date, reservation_time]):
            return Response(
                {"error": "Faltan campos requeridos: table_id, reservation_date, reservation_time"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Configurar lock con timeout más generoso para alta concurrencia
        lock_timeout = 45  # 45 segundos
        max_retries = 5    # Más intentos
        
        try:
            # Usar lock distribuido con parámetros robustos
            with TableReservationLock(
                table_id, 
                reservation_date, 
                reservation_time,
                timeout=lock_timeout,
                max_retries=max_retries
            ) as lock:
                
                # Invalidar cache antes de verificar disponibilidad
                cache_key = f"availability:{table_id}:{reservation_date}:{reservation_time}"
                cache.delete(cache_key)
                
                with transaction.atomic():
                    # Verificar disponibilidad con select_for_update para evitar race conditions
                    conflicts = Reservation.objects.select_for_update().filter(
                        table_id=table_id,
                        reservation_date=reservation_date,
                        reservation_time=reservation_time,
                        status__in=["pending", "confirmed"],
                    ).exists()
                    
                    if conflicts:
                        return Response(
                            {
                                "error": "Mesa no disponible en esa fecha/hora",
                                "details": "Otra reserva ya existe para este horario"
                            },
                            status=status.HTTP_409_CONFLICT,
                        )

                    # Crear reserva con validación
                    try:
                        reservation = Reservation.objects.create(
                            restaurant_id=data.get("restaurant_id", 1),
                            customer_id=data.get("customer_id", 1),
                            table_id=table_id,
                            reservation_date=reservation_date,
                            reservation_time=reservation_time,
                            party_size=data.get("party_size", 2),
                        )
                        
                        # Extender lock para envío de email asíncrono
                        lock.extend_lock(30)
                        
                        # Programar email de confirmación (asíncrono)
                        try:
                            send_confirmation_email.apply_async(
                                args=[str(reservation.id)],
                                countdown=2  # Pequeño delay para evitar que llegue antes que la respuesta
                            )
                            email_scheduled = True
                        except Exception as e:
                            logger.error(f"Error programando email: {e}")
                            email_scheduled = False
                        
                        # Programar expiración automática si está en pending
                        if reservation.status == 'pending' and reservation.expires_at:
                            try:
                                expire_reservation.apply_async(
                                    args=[str(reservation.id)],
                                    eta=reservation.expires_at
                                )
                            except Exception as e:
                                logger.error(f"Error programando expiración: {e}")

                        return Response(
                            {
                                "id": str(reservation.id),
                                "status": reservation.status,
                                "expires_at": reservation.expires_at,
                                "message": "Reserva creada exitosamente",
                                "email_scheduled": email_scheduled
                            },
                            status=status.HTTP_201_CREATED,
                        )

                    except IntegrityError as ie:
                        # Constraint único violado a nivel de BD
                        logger.warning(f"Constraint violation: {ie}")
                        return Response(
                            {
                                "error": "Mesa ya reservada",
                                "details": "Otra reserva fue creada simultáneamente"
                            },
                            status=status.HTTP_409_CONFLICT,
                        )
                    
                    except ValidationError as ve:
                        # Errores de validación del modelo
                        error_messages = []
                        if hasattr(ve, 'message_dict'):
                            for field, messages in ve.message_dict.items():
                                for message in messages:
                                    error_messages.append(f"{field}: {message}")
                        else:
                            error_messages.append(str(ve))
                        
                        return Response(
                            {"error": "Validación fallida", "details": error_messages},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

        except LockAcquisitionError as lae:
            # Error específico de adquisición de lock
            logger.warning(f"Lock acquisition failed: {lae}")
            return Response(
                {
                    "error": "Mesa temporalmente no disponible",
                    "details": "Demasiada concurrencia - intente nuevamente en unos segundos",
                    "retry_after": 5
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        
        except Exception as e:
            # Error genérico - log detallado para debugging
            logger.error(f"Error inesperado creando reserva: {e}", exc_info=True)
            return Response(
                {
                    "error": "Error interno del servidor",
                    "details": "Por favor contacte al administrador si el problema persiste"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
