# notifications/tasks.py
import logging
import smtplib
import socket
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend
from django.db import transaction, OperationalError
from django.template import Template, Context
from django.utils import timezone

from .models import Notification, NotificationTemplate

logger = logging.getLogger(__name__)


@shared_task
def process_notification_queue():
    """Alias para process_pending_notifications para compatibilidad con tests"""
    return process_pending_notifications.apply()


@shared_task
def send_bulk_notifications(notification_data_list):
    """Envía notificaciones en lote - alias para bulk_create_notifications"""
    results = []
    for data in notification_data_list:
        template_code = data.get('template_code')
        customer_id = data.get('customer_id')
        context_data = data.get('context_data')
        scheduled_for = data.get('scheduled_for')
        
        result = create_notification_from_template.apply_async(
            (template_code, customer_id, context_data, scheduled_for)
        )
        results.append({
            'customer_id': customer_id,
            'task_id': result.id,
            'template_code': template_code
        })
    
    return {
        'processed_count': len(results),
        'results': results,
        'status': 'queued'
    }


@shared_task
def generate_notification_report(start_date=None, end_date=None):
    """Genera reporte de notificaciones para un periodo"""
    from django.db.models import Count, Q
    
    queryset = Notification.objects.all()
    
    if start_date:
        queryset = queryset.filter(created_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__lte=end_date)
    
    # Estadísticas por estado
    status_stats = queryset.aggregate(
        total=Count('id'),
        sent=Count('id', filter=Q(status=Notification.Status.SENT)),
        failed=Count('id', filter=Q(status=Notification.Status.FAILED)),
        pending=Count('id', filter=Q(status=Notification.Status.PENDING))
    )
    
    # Estadísticas por canal
    channel_stats = queryset.values('channel').annotate(
        count=Count('id')
    ).order_by('channel')
    
    # Estadísticas por tipo
    type_stats = queryset.values('notification_type').annotate(
        count=Count('id')
    ).order_by('notification_type')
    
    return {
        'period': {
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None
        },
        'status_stats': status_stats,
        'channel_stats': list(channel_stats),
        'type_stats': list(type_stats),
        'generated_at': timezone.now().isoformat()
    }


# Definir excepciones específicas para retry
SMTP_RETRY_EXCEPTIONS = (
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPConnectError,
    smtplib.SMTPRecipientsRefused,
    smtplib.SMTPDataError,
    socket.timeout,
    socket.gaierror,
    ConnectionError,
    OSError,
)

DATABASE_RETRY_EXCEPTIONS = (OperationalError,)


@shared_task(
    bind=True,
    autoretry_for=SMTP_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=5,
    default_retry_delay=60,
    retry_backoff_max=600,
)
def send_notification_task(self, notification_id):
    """Envía una notificación específica con retry inteligente"""
    try:
        with transaction.atomic():
            notification = Notification.objects.select_for_update().get(
                id=notification_id
            )

            if notification.status != Notification.Status.PENDING:
                logger.info(
                    f"Notificación {notification_id} ya no está pendiente: {notification.status}"
                )
                return {
                    "notification_id": str(notification.id),
                    "status": notification.status,
                }

            # Marcar como enviando
            notification.status = Notification.Status.SENDING
            notification.save(update_fields=["status"])

        # Verificar preferencias del cliente
        if notification.customer:
            prefs = getattr(notification.customer, "notification_preferences", None)
            if prefs and not prefs.allows_notification(
                notification.notification_type, notification.channel, timezone.now()
            ):
                notification.status = Notification.Status.BLOCKED
                notification.error_message = "Bloqueado por preferencias del cliente"
                notification.save(update_fields=["status", "error_message"])
                logger.info(
                    f"Notificación {notification_id} bloqueada por preferencias"
                )
                return {"notification_id": str(notification.id), "status": "blocked"}

        # Enviar según el canal
        success = False
        error_msg = None

        if notification.channel == Notification.Channel.EMAIL:
            success, error_msg = _send_email_notification(notification)
        elif notification.channel == Notification.Channel.SMS:
            success, error_msg = _send_sms_notification(notification)
        elif notification.channel == Notification.Channel.PUSH:
            success, error_msg = _send_push_notification(notification)
        else:
            error_msg = f"Canal no soportado: {notification.channel}"

        # Actualizar estado
        with transaction.atomic():
            notification = Notification.objects.select_for_update().get(
                id=notification_id
            )
            if success:
                notification.status = Notification.Status.SENT
                notification.sent_at = timezone.now()
                notification.error_message = None
            else:
                notification.status = Notification.Status.FAILED
                notification.error_message = error_msg

            notification.save(update_fields=["status", "sent_at", "error_message"])

        status = "sent" if success else "failed"
        logger.info(f"Notificación {notification_id} {status}")

        return {
            "notification_id": str(notification.id),
            "status": status,
            "error": error_msg if not success else None,
        }

    except Notification.DoesNotExist:
        logger.error(f"Notificación {notification_id} no encontrada")
        return {"notification_id": notification_id, "error": "not_found"}

    except SMTP_RETRY_EXCEPTIONS as exc:
        error_type = type(exc).__name__
        logger.warning(f"Error SMTP ({error_type}) en send_notification_task: {exc}")

        # Marcar como pendiente para retry
        try:
            with transaction.atomic():
                notification = Notification.objects.select_for_update().get(
                    id=notification_id
                )
                notification.status = Notification.Status.PENDING
                notification.retry_count += 1
                notification.save(update_fields=["status", "retry_count"])
        except Exception:
            pass

        # Estrategia de retry diferenciada
        if isinstance(exc, (smtplib.SMTPServerDisconnected, ConnectionError)):
            countdown = min(30 * (2**self.request.retries), 300)
        elif isinstance(exc, smtplib.SMTPRecipientsRefused):
            logger.error(f"Destinatario inválido para notificación {notification_id}")
            return {"notification_id": notification_id, "error": "invalid_recipient"}
        else:
            countdown = min(60 * (2**self.request.retries), 600)

        raise self.retry(exc=exc, countdown=countdown, max_retries=5)

    except Exception as exc:
        logger.error(f"Error no recuperable en send_notification_task: {exc}")
        try:
            with transaction.atomic():
                notification = Notification.objects.select_for_update().get(
                    id=notification_id
                )
                notification.status = Notification.Status.FAILED
                notification.error_message = str(exc)
                notification.save(update_fields=["status", "error_message"])
        except Exception:
            pass

        return {"notification_id": notification_id, "error": "permanent_failure"}


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def process_pending_notifications(self):
    """Procesa todas las notificaciones pendientes"""
    try:
        # Obtener notificaciones pendientes que no están siendo procesadas
        pending_notifications = Notification.objects.filter(
            status=Notification.Status.PENDING,
            scheduled_for__lte=timezone.now(),
            retry_count__lt=5,  # Limitar reintentos
        ).select_related("customer", "template")[:100]  # Procesar máximo 100 por lote

        if not pending_notifications:
            logger.debug("No hay notificaciones pendientes para procesar")
            return {"processed": 0, "status": "no_pending"}

        processed_count = 0
        for notification in pending_notifications:
            # Enviar cada notificación de forma asíncrona
            send_notification_task.apply_async((notification.id,))
            processed_count += 1

        logger.info(f"Enviadas {processed_count} notificaciones para procesamiento")
        return {"processed": processed_count, "status": "queued"}

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(
            f"Error de base de datos en process_pending_notifications: {exc}"
        )
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error no recuperable en process_pending_notifications: {exc}")
        return {"error": "permanent_failure", "message": str(exc)}


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def create_notification_from_template(
    self, template_code, customer_id, context_data=None, scheduled_for=None
):
    """Crea una notificación usando una plantilla"""
    try:
        with transaction.atomic():
            from customers.models import Customer

            template = NotificationTemplate.objects.get(
                code=template_code, is_active=True
            )
            customer = Customer.objects.get(id=customer_id)

            # Preparar contexto
            context = Context(context_data or {})
            context["customer"] = customer
            context["now"] = timezone.now()

            # Renderizar contenido
            subject_template = Template(template.subject)
            body_template = Template(template.body)

            subject = subject_template.render(context)
            body = body_template.render(context)

            # Crear notificación
            notification = Notification.objects.create(
                customer=customer,
                template=template,
                notification_type=template.notification_type,
                channel=template.default_channel,
                subject=subject,
                body=body,
                scheduled_for=scheduled_for or timezone.now(),
                metadata=context_data or {},
            )

            logger.info(
                f"Notificación creada desde plantilla {template_code} para cliente {customer_id}"
            )

            # Si debe enviarse inmediatamente, programar envío
            if not scheduled_for or scheduled_for <= timezone.now():
                send_notification_task.apply_async((notification.id,))

            return {
                "notification_id": str(notification.id),
                "status": "created",
                "scheduled": scheduled_for is not None,
            }

    except NotificationTemplate.DoesNotExist:
        logger.error(f"Plantilla {template_code} no encontrada")
        return {"error": "template_not_found", "template_code": template_code}

    except Customer.DoesNotExist:
        logger.error(f"Cliente {customer_id} no encontrado")
        return {"error": "customer_not_found", "customer_id": customer_id}

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(
            f"Error de base de datos en create_notification_from_template: {exc}"
        )
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en create_notification_from_template: {exc}")
        return {"error": "creation_failed", "message": str(exc)}


@shared_task
def bulk_create_notifications(
    template_code, customer_ids, context_data=None, scheduled_for=None
):
    """Crea notificaciones en lote para múltiples clientes"""
    results = []

    for customer_id in customer_ids:
        result = create_notification_from_template.apply_async(
            (template_code, customer_id, context_data, scheduled_for)
        )
        results.append({"customer_id": customer_id, "task_id": result.id})

    logger.info(
        f"Creación masiva iniciada para {len(customer_ids)} clientes con plantilla {template_code}"
    )

    return {
        "template_code": template_code,
        "customers_count": len(customer_ids),
        "tasks": results,
        "status": "queued",
    }


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def cleanup_old_notifications(self, days_old=30):
    """Limpia notificaciones antiguas"""
    try:
        cutoff_date = timezone.now() - timedelta(days=days_old)

        # Eliminar notificaciones exitosas antiguas
        deleted_sent, _ = Notification.objects.filter(
            status=Notification.Status.SENT, sent_at__lt=cutoff_date
        ).delete()

        # Eliminar notificaciones fallidas muy antiguas
        deleted_failed, _ = Notification.objects.filter(
            status=Notification.Status.FAILED, created_at__lt=cutoff_date
        ).delete()

        total_deleted = deleted_sent + deleted_failed

        logger.info(
            f"Limpieza completada: {total_deleted} notificaciones eliminadas ({deleted_sent} enviadas, {deleted_failed} fallidas)"
        )

        return {
            "total_deleted": total_deleted,
            "sent_deleted": deleted_sent,
            "failed_deleted": deleted_failed,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en cleanup_old_notifications: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en cleanup_old_notifications: {exc}")
        return {"error": "cleanup_failed", "message": str(exc)}


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def retry_failed_notifications(self, max_age_hours=24):
    """Reintenta notificaciones fallidas recientes"""
    try:
        cutoff_time = timezone.now() - timedelta(hours=max_age_hours)

        failed_notifications = Notification.objects.filter(
            status=Notification.Status.FAILED,
            created_at__gte=cutoff_time,
            retry_count__lt=3,  # Limitar reintentos
        )

        retry_count = 0
        for notification in failed_notifications:
            # Resetear estado y programar reenvío
            notification.status = Notification.Status.PENDING
            notification.error_message = None
            notification.save(update_fields=["status", "error_message"])

            send_notification_task.apply_async((notification.id,))
            retry_count += 1

        logger.info(f"Reintentando {retry_count} notificaciones fallidas")

        return {
            "retried_count": retry_count,
            "status": "queued" if retry_count > 0 else "no_failed",
        }

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en retry_failed_notifications: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en retry_failed_notifications: {exc}")
        return {"error": "retry_failed", "message": str(exc)}


# Funciones auxiliares para envío por canal


def _send_email_notification(notification: Notification) -> tuple[bool, str]:
    """Envía notificación por email"""
    try:
        if not notification.customer or not notification.customer.email:
            return False, "Cliente sin email"

        backend = EmailBackend(
            host=getattr(settings, "EMAIL_HOST", "localhost"),
            port=getattr(settings, "EMAIL_PORT", 587),
            username=getattr(settings, "EMAIL_HOST_USER", ""),
            password=getattr(settings, "EMAIL_HOST_PASSWORD", ""),
            use_tls=getattr(settings, "EMAIL_USE_TLS", True),
            timeout=30,
        )

        send_mail(
            subject=notification.subject,
            message=notification.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.customer.email],
            fail_silently=False,
            connection=backend,
        )

        return True, None

    except Exception as e:
        return False, str(e)


def _send_sms_notification(notification: Notification) -> tuple[bool, str]:
    """Envía notificación por SMS (placeholder)"""
    # TODO: Implementar integración con servicio SMS (Twilio, etc.)
    logger.warning("SMS no implementado - simulando envío exitoso")
    return True, None


def _send_push_notification(notification: Notification) -> tuple[bool, str]:
    """Envía notificación push (placeholder)"""
    # TODO: Implementar integración con servicio push (Firebase, etc.)
    logger.warning("Push notifications no implementadas - simulando envío exitoso")
    return True, None
