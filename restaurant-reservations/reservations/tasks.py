from celery import shared_task

from .models import Reservation


@shared_task
def expire_reservation(reservation_id):
    """Expira una reserva si no ha sido confirmada"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)

        # Solo expirar si sigue pendiente
        if reservation.status == "pending":
            reservation.status = "expired"
            reservation.save()
            print(f"Reserva {reservation_id} expirada")
            return f"Reserva {reservation_id} expirada"
        else:
            print(f"Reserva {reservation_id} ya fue procesada")
            return f"Reserva {reservation_id} ya fue procesada"

    except Reservation.DoesNotExist:
        print(f"Reserva {reservation_id} no encontrada")
        return f"Reserva {reservation_id} no encontrada"


@shared_task
def send_confirmation_email(reservation_id):
    """Envía email de confirmación de reserva"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)

        # Simular envío de email
        print(f"Enviando email a {reservation.customer.email}")
        print(f"Reserva para {reservation.party_size} personas")
        print(
            f"Fecha: {reservation.reservation_date} a las {reservation.reservation_time}"
        )

        return f"Email enviado para reserva {reservation_id}"

    except Reservation.DoesNotExist:
        return f"Reserva {reservation_id} no encontrada"
