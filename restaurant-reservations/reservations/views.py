# reservations/views.py
from rest_framework import status, viewsets
from rest_framework.response import Response
from restaurants.services import TableReservationLock, check_table_availability

from .models import Reservation


class ReservationViewSet(viewsets.ViewSet):
    """ViewSet para manejar reservas con lock distribuido"""

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

    def create(self, request):
        data = request.data
        table_id = data.get("table_id")
        reservation_date = data.get("reservation_date")
        reservation_time = data.get("reservation_time")

        if not all([table_id, reservation_date, reservation_time]):
            return Response(
                {"error": "Faltan campos requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Usar lock distribuido
            with TableReservationLock(table_id, reservation_date, reservation_time):
                if not check_table_availability(
                    table_id, reservation_date, reservation_time
                ):
                    return Response(
                        {"error": "Mesa no disponible en esa fecha/hora"},
                        status=status.HTTP_409_CONFLICT,
                    )

                reservation = Reservation.objects.create(
                    restaurant_id=data.get("restaurant_id", 1),
                    customer_id=data.get("customer_id", 1),
                    table_id=table_id,
                    reservation_date=reservation_date,
                    reservation_time=reservation_time,
                    party_size=data.get("party_size", 2),
                )

                return Response(
                    {
                        "id": str(reservation.id),
                        "status": reservation.status,
                        "expires_at": reservation.expires_at,
                        "message": "Reserva creada exitosamente",
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Exception as e:
            return Response(
                {"error": f"Mesa está siendo reservada: {str(e)}"},
                status=status.HTTP_423_LOCKED,
            )
