# customers/tasks.py
import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction, OperationalError
from django.utils import timezone

from .models import Customer

logger = logging.getLogger(__name__)

# Definir excepciones específicas para retry
DATABASE_RETRY_EXCEPTIONS = (OperationalError,)


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def update_customer_stats(self, customer_id):
    """Actualiza las estadísticas de un cliente específico"""
    try:
        from reservations.models import Reservation

        with transaction.atomic():
            customer = Customer.objects.select_for_update().get(id=customer_id)

            # Calcular estadísticas desde las reservas
            reservations = Reservation.objects.filter(customer=customer)

            total_reservations = reservations.count()
            confirmed_reservations = reservations.filter(
                status=Reservation.Status.CONFIRMED
            ).count()
            completed_reservations = reservations.filter(
                status=Reservation.Status.COMPLETED
            ).count()
            cancelled_reservations = reservations.filter(
                status=Reservation.Status.CANCELLED
            ).count()
            no_show_count = reservations.filter(
                status=Reservation.Status.NO_SHOW
            ).count()

            # Calcular puntaje de cliente
            if total_reservations > 0:
                completion_rate = (completed_reservations / total_reservations) * 100
                cancellation_penalty = (
                    cancelled_reservations * 10
                )  # -10 puntos por cancelación
                no_show_penalty = no_show_count * 20  # -20 puntos por no-show

                base_score = min(100, completion_rate)
                customer_score = max(
                    0, int(base_score - cancellation_penalty - no_show_penalty)
                )

                # Bonus por fidelidad (más de 10 reservas completadas)
                if completed_reservations >= 10:
                    customer_score = min(100, customer_score + 10)
            else:
                customer_score = 100  # Clientes nuevos empiezan con 100

            # Actualizar campos
            customer.total_reservations = total_reservations
            customer.confirmed_reservations = confirmed_reservations
            customer.completed_reservations = completed_reservations
            customer.cancelled_reservations = cancelled_reservations
            customer.no_show_count = no_show_count
            customer.customer_score = customer_score
            customer.last_activity = timezone.now()

            customer.save(
                update_fields=[
                    "total_reservations",
                    "confirmed_reservations",
                    "completed_reservations",
                    "cancelled_reservations",
                    "no_show_count",
                    "customer_score",
                    "last_activity",
                ]
            )

            logger.info(
                f"Estadísticas actualizadas para cliente {customer_id}: score={customer_score}"
            )

            return {
                "customer_id": str(customer.id),
                "total_reservations": total_reservations,
                "customer_score": customer_score,
                "status": "updated",
            }

    except Customer.DoesNotExist:
        logger.warning(f"Cliente {customer_id} no encontrado")
        return {"customer_id": customer_id, "error": "not_found"}

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en update_customer_stats: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error no recuperable en update_customer_stats: {exc}")
        return {
            "customer_id": customer_id,
            "error": "permanent_failure",
            "message": str(exc),
        }


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def update_all_customer_stats(self):
    """Actualiza estadísticas de todos los clientes activos"""
    try:
        active_customers = Customer.objects.filter(is_active=True)
        total_customers = active_customers.count()

        if total_customers == 0:
            logger.info("No hay clientes activos para actualizar")
            return {"processed": 0, "status": "no_customers"}

        processed_count = 0
        failed_count = 0

        for customer in active_customers.iterator(chunk_size=100):
            try:
                # Enviar tarea asíncrona para cada cliente
                update_customer_stats.apply_async((customer.id,))
                processed_count += 1
            except Exception as e:
                logger.error(
                    f"Error al programar actualización para cliente {customer.id}: {e}"
                )
                failed_count += 1

        logger.info(
            f"Programadas {processed_count} actualizaciones de estadísticas de clientes"
        )

        return {
            "total_customers": total_customers,
            "processed": processed_count,
            "failed": failed_count,
            "status": "queued",
        }

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en update_all_customer_stats: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error no recuperable en update_all_customer_stats: {exc}")
        return {"error": "permanent_failure", "message": str(exc)}


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def identify_inactive_customers(self, inactive_days=90):
    """Identifica clientes inactivos para posibles campañas de reactivación"""
    try:
        cutoff_date = timezone.now() - timedelta(days=inactive_days)

        # Clientes que no han hecho reservas recientemente
        inactive_customers = (
            Customer.objects.filter(is_active=True, last_activity__lt=cutoff_date)
            .select_related()
            .order_by("last_activity")
        )

        inactive_count = inactive_customers.count()

        if inactive_count == 0:
            logger.info("No se encontraron clientes inactivos")
            return {
                "inactive_customers": 0,
                "cutoff_date": cutoff_date.isoformat(),
                "status": "no_inactive",
            }

        # Categorizar por nivel de inactividad
        very_inactive = inactive_customers.filter(
            last_activity__lt=timezone.now() - timedelta(days=inactive_days * 2)
        ).count()

        recently_inactive = inactive_count - very_inactive

        # Preparar datos para posible campaña
        customer_ids = list(inactive_customers.values_list("id", flat=True))

        logger.info(
            f"Identificados {inactive_count} clientes inactivos ({recently_inactive} recientes, {very_inactive} muy inactivos)"
        )

        return {
            "inactive_customers": inactive_count,
            "recently_inactive": recently_inactive,
            "very_inactive": very_inactive,
            "customer_ids": customer_ids,
            "cutoff_date": cutoff_date.isoformat(),
            "status": "identified",
        }

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en identify_inactive_customers: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en identify_inactive_customers: {exc}")
        return {"error": "identification_failed", "message": str(exc)}


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def cleanup_customer_data(self, days_old=365):
    """Limpia datos antiguos de clientes inactivos"""
    try:
        cutoff_date = timezone.now() - timedelta(days=days_old)

        # Clientes marcados como inactivos y sin actividad reciente
        candidates_for_cleanup = Customer.objects.filter(
            is_active=False, last_activity__lt=cutoff_date
        )

        # Solo eliminar si no tienen reservas recientes
        from reservations.models import Reservation

        recent_reservation_cutoff = timezone.now() - timedelta(days=days_old // 2)

        customers_to_cleanup = []
        for customer in candidates_for_cleanup:
            recent_reservations = Reservation.objects.filter(
                customer=customer, created_at__gte=recent_reservation_cutoff
            ).exists()

            if not recent_reservations:
                customers_to_cleanup.append(customer.id)

        if not customers_to_cleanup:
            logger.info("No hay clientes para limpiar")
            return {
                "candidates": candidates_for_cleanup.count(),
                "cleaned": 0,
                "status": "no_cleanup",
            }

        # Marcar para anonimización en lugar de eliminación completa
        cleaned_count = 0
        for customer_id in customers_to_cleanup:
            try:
                with transaction.atomic():
                    customer = Customer.objects.select_for_update().get(id=customer_id)

                    # Anonimizar datos sensibles
                    customer.first_name = "Cliente"
                    customer.last_name = "Eliminado"
                    customer.email = f"deleted_{customer_id}@example.com"
                    customer.phone = None
                    customer.birth_date = None
                    customer.address = None
                    customer.preferences = {}
                    customer.dietary_restrictions = None
                    customer.notes = "Datos anonimizados"
                    customer.is_active = False

                    customer.save()
                    cleaned_count += 1

            except Customer.DoesNotExist:
                continue
            except Exception as e:
                logger.error(f"Error al limpiar cliente {customer_id}: {e}")
                continue

        logger.info(f"Limpieza completada: {cleaned_count} clientes anonimizados")

        return {
            "candidates": candidates_for_cleanup.count(),
            "cleaned": cleaned_count,
            "cutoff_date": cutoff_date.isoformat(),
            "status": "completed",
        }

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en cleanup_customer_data: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en cleanup_customer_data: {exc}")
        return {"error": "cleanup_failed", "message": str(exc)}


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def generate_customer_insights(self):
    """Genera insights sobre los clientes para reporting"""
    try:
        insights = {}

        # Estadísticas generales
        total_customers = Customer.objects.filter(is_active=True).count()
        new_customers_month = Customer.objects.filter(
            is_active=True, created_at__gte=timezone.now() - timedelta(days=30)
        ).count()

        # Distribución de puntuaciones
        score_ranges = {
            "excellent": Customer.objects.filter(
                customer_score__gte=90, is_active=True
            ).count(),
            "good": Customer.objects.filter(
                customer_score__gte=70, customer_score__lt=90, is_active=True
            ).count(),
            "fair": Customer.objects.filter(
                customer_score__gte=50, customer_score__lt=70, is_active=True
            ).count(),
            "poor": Customer.objects.filter(
                customer_score__lt=50, is_active=True
            ).count(),
        }

        # Top clientes por actividad
        top_customers = Customer.objects.filter(
            is_active=True, total_reservations__gt=0
        ).order_by("-total_reservations", "-customer_score")[:10]

        top_customers_data = [
            {
                "id": str(customer.id),
                "name": f"{customer.first_name} {customer.last_name}",
                "total_reservations": customer.total_reservations,
                "customer_score": customer.customer_score,
                "completion_rate": customer.completion_rate,
            }
            for customer in top_customers
        ]

        # Estadísticas de comportamiento
        from django.db import models

        avg_score = (
            Customer.objects.filter(is_active=True).aggregate(
                avg_score=models.Avg("customer_score")
            )["avg_score"]
            or 0
        )

        insights = {
            "total_customers": total_customers,
            "new_customers_month": new_customers_month,
            "avg_customer_score": round(avg_score, 2),
            "score_distribution": score_ranges,
            "top_customers": top_customers_data,
            "generated_at": timezone.now().isoformat(),
        }

        logger.info(f"Insights generados para {total_customers} clientes")

        return insights

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en generate_customer_insights: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en generate_customer_insights: {exc}")
        return {"error": "insights_failed", "message": str(exc)}
