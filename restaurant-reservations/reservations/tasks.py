# reservations/tasks.py
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Reservation

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def expire_reservation(self, reservation_id):
    """Expira una reserva si no ha sido confirmada antes de expires_at"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)

        # Usar el método is_expired() del modelo
        if reservation.status == "pending" and reservation.is_expired():
            reservation.status = "expired"
            reservation.save(update_fields=["status"])
            logger.info(f"Reserva {reservation_id} expirada automáticamente")
            return {"reservation_id": str(reservation.id), "status": "expired"}

        logger.info(f"Reserva {reservation_id} no necesita expirar")
        return {"reservation_id": str(reservation.id), "status": reservation.status}

    except Reservation.DoesNotExist:
        logger.warning(f"Reserva {reservation_id} no encontrada")
        return {"reservation_id": reservation_id, "error": "not_found"}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_confirmation_email(self, reservation_id):
    """Envía email de confirmación de reserva"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)

        subject = "Confirmación de reserva"
        message = (
            f"Estimado/a {reservation.customer.first_name},\n\n"
            f"Su reserva para {reservation.party_size} personas el "
            f"{reservation.reservation_date} a las {reservation.reservation_time} "
            f"ha sido confirmada.\n\n¡Gracias por reservar con nosotros!"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reservation.customer.email],
            fail_silently=False,
        )

        logger.info(f"Email de confirmación enviado a {reservation.customer.email}")
        return {"reservation_id": str(reservation.id), "status": "email_sent"}

    except Reservation.DoesNotExist:
        logger.error(f"Reserva {reservation_id} no encontrada")
        return {"reservation_id": reservation_id, "error": "not_found"}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_reminder(self, reservation_id, hours_before=24):
    """Envía recordatorio antes de la reserva"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)

        if reservation.status != "confirmed":
            logger.info(
                f"Reserva {reservation_id} no está confirmada, no se envía recordatorio"
            )
            return {"reservation_id": str(reservation.id), "status": "not_confirmed"}

        subject = "Recordatorio de su reserva"
        message = (
            f"Hola {reservation.customer.first_name},\n\n"
            f"Le recordamos que su reserva es el {reservation.reservation_date} "
            f"a las {reservation.reservation_time}.\n"
            f"Mesa {reservation.table.number} para {reservation.party_size} personas.\n\n"
            f"¡Lo esperamos!"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reservation.customer.email],
            fail_silently=False,
        )

        logger.info(f"Recordatorio enviado a {reservation.customer.email}")
        return {"reservation_id": str(reservation.id), "status": "reminder_sent"}

    except Reservation.DoesNotExist:
        logger.error(f"Reserva {reservation_id} no encontrada")
        return {"reservation_id": reservation_id, "error": "not_found"}


@shared_task
def schedule_reminder(reservation_id, hours_before=24):
    """Programa un recordatorio para la reserva"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)

        # Usar reservation_datetime del modelo
        reminder_time = reservation.reservation_datetime - timedelta(hours=hours_before)

        send_reminder.apply_async((reservation_id,), eta=reminder_time)
        logger.info(
            f"Recordatorio programado para reserva {reservation_id} a las {reminder_time}"
        )

        return {
            "reservation_id": str(reservation.id),
            "status": "reminder_scheduled",
            "scheduled_time": str(reminder_time),
        }

    except Reservation.DoesNotExist:
        logger.error(
            f"Reserva {reservation_id} no encontrada al intentar programar recordatorio"
        )
        return {"reservation_id": reservation_id, "error": "not_found"}
