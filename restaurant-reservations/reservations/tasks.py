# reservations/tasks.py
import logging
import smtplib
import socket
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend
from django.db import transaction, OperationalError

from .models import Reservation

logger = logging.getLogger(__name__)

# Definir excepciones específicas para retry
SMTP_RETRY_EXCEPTIONS = (
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPConnectError, 
    smtplib.SMTPRecipientsRefused,
    smtplib.SMTPDataError,
    socket.timeout,
    socket.gaierror,
    ConnectionError,
    OSError
)

DATABASE_RETRY_EXCEPTIONS = (
    OperationalError,
)


@shared_task(bind=True, autoretry_for=DATABASE_RETRY_EXCEPTIONS, retry_backoff=True, max_retries=3)
def expire_reservation(self, reservation_id):
    """Expira una reserva si no ha sido confirmada antes de expires_at"""
    try:
        with transaction.atomic():
            # Usar select_for_update para evitar race conditions
            reservation = Reservation.objects.select_for_update().get(id=reservation_id)

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
    
    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en expire_reservation: {exc}")
        # Incrementar delay basado en el número de retry
        countdown = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)


@shared_task(
    bind=True, 
    autoretry_for=SMTP_RETRY_EXCEPTIONS,
    retry_backoff=True, 
    max_retries=5,
    default_retry_delay=60,  # 1 minuto base
    retry_backoff_max=600    # Máximo 10 minutos
)
def send_confirmation_email(self, reservation_id):
    """Envía email de confirmación de reserva con retry inteligente"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)

        subject = "Confirmación de reserva"
        message = (
            f"Estimado/a {reservation.customer.first_name},\n\n"
            f"Su reserva para {reservation.party_size} personas el "
            f"{reservation.reservation_date} a las {reservation.reservation_time} "
            f"ha sido confirmada.\n\n¡Gracias por reservar con nosotros!"
        )

        # Usar backend SMTP con timeout específico
        backend = EmailBackend(
            host=getattr(settings, 'EMAIL_HOST', 'localhost'),
            port=getattr(settings, 'EMAIL_PORT', 587),
            username=getattr(settings, 'EMAIL_HOST_USER', ''),
            password=getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
            use_tls=getattr(settings, 'EMAIL_USE_TLS', True),
            timeout=30,  # Timeout de 30 segundos
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reservation.customer.email],
            fail_silently=False,
            connection=backend,
        )

        logger.info(f"Email de confirmación enviado a {reservation.customer.email}")
        return {"reservation_id": str(reservation.id), "status": "email_sent"}

    except Reservation.DoesNotExist:
        logger.error(f"Reserva {reservation_id} no encontrada")
        return {"reservation_id": reservation_id, "error": "not_found"}
    
    except SMTP_RETRY_EXCEPTIONS as exc:
        # Log del tipo específico de error
        error_type = type(exc).__name__
        logger.warning(f"Error SMTP ({error_type}) en send_confirmation_email: {exc}")
        
        # Estrategia de retry diferenciada por tipo de error
        if isinstance(exc, (smtplib.SMTPServerDisconnected, ConnectionError)):
            # Errores de conexión - retry más rápido
            countdown = min(30 * (2 ** self.request.retries), 300)  # Max 5 min
        elif isinstance(exc, smtplib.SMTPRecipientsRefused):
            # Error de destinatario - probablemente no vale la pena retry
            logger.error(f"Destinatario inválido para reserva {reservation_id}")
            return {"reservation_id": reservation_id, "error": "invalid_recipient"}
        else:
            # Otros errores SMTP - retry con backoff normal
            countdown = min(60 * (2 ** self.request.retries), 600)  # Max 10 min
            
        raise self.retry(exc=exc, countdown=countdown, max_retries=5)
    
    except Exception as exc:
        # Errores no recuperables
        logger.error(f"Error no recuperable en send_confirmation_email: {exc}")
        return {"reservation_id": reservation_id, "error": "permanent_failure"}


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
