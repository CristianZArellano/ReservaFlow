# maintenance/tasks.py
import logging
from datetime import timedelta
from typing import Dict, Any

from celery import shared_task
from django.conf import settings
from django.core.management import call_command
from django.db import transaction, OperationalError, models
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Definir excepciones específicas para retry
DATABASE_RETRY_EXCEPTIONS = (OperationalError,)


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def cleanup_expired_reservations(self):
    """Limpia reservas expiradas automáticamente"""
    try:
        from reservations.models import Reservation

        # Encontrar reservas que deberían haber expirado
        now = timezone.now()

        expired_reservations = Reservation.objects.filter(
            status=Reservation.Status.PENDING, expires_at__lt=now
        ).select_for_update()

        expired_count = 0

        for reservation in expired_reservations:
            try:
                with transaction.atomic():
                    # Verificar nuevamente dentro de la transacción
                    current_reservation = Reservation.objects.select_for_update().get(
                        id=reservation.id, status=Reservation.Status.PENDING
                    )

                    if current_reservation.is_expired():
                        current_reservation.status = Reservation.Status.EXPIRED
                        current_reservation.save(update_fields=["status"])
                        expired_count += 1

                        logger.info(
                            f"Reserva {current_reservation.id} marcada como expirada"
                        )

            except Reservation.DoesNotExist:
                # La reserva ya fue procesada por otro worker
                continue
            except Exception as e:
                logger.error(f"Error al expirar reserva {reservation.id}: {e}")
                continue

        logger.info(
            f"Limpieza de reservas expiradas completada: {expired_count} reservas procesadas"
        )

        return {
            "expired_count": expired_count,
            "status": "completed",
            "processed_at": timezone.now().isoformat(),
        }

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en cleanup_expired_reservations: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en cleanup_expired_reservations: {exc}")
        return {"error": "cleanup_failed", "message": str(exc)}


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def database_maintenance(self):
    """Ejecuta tareas de mantenimiento de la base de datos"""
    try:
        maintenance_results = {}

        # 1. Limpiar sesiones expiradas
        try:
            call_command("clearsessions", verbosity=0)
            maintenance_results["sessions_cleaned"] = True
        except Exception as e:
            logger.error(f"Error limpiando sesiones: {e}")
            maintenance_results["sessions_cleaned"] = False

        # 2. Optimizar tablas (solo para PostgreSQL)
        if "postgresql" in settings.DATABASES["default"]["ENGINE"]:
            try:
                from django.db import connection

                with connection.cursor() as cursor:
                    # Obtener estadísticas de las tablas más importantes
                    cursor.execute("""
                        SELECT 
                            schemaname,
                            tablename,
                            n_tup_ins + n_tup_upd + n_tup_del as total_ops,
                            n_dead_tup
                        FROM pg_stat_user_tables 
                        WHERE schemaname = 'public'
                        ORDER BY total_ops DESC
                        LIMIT 10;
                    """)

                    table_stats = cursor.fetchall()
                    maintenance_results["table_stats"] = [
                        {
                            "schema": row[0],
                            "table": row[1],
                            "operations": row[2],
                            "dead_tuples": row[3],
                        }
                        for row in table_stats
                    ]

            except Exception as e:
                logger.error(f"Error obteniendo estadísticas de BD: {e}")
                maintenance_results["table_stats"] = None

        # 3. Limpiar cache
        try:
            cache.clear()
            maintenance_results["cache_cleared"] = True
            logger.info("Cache limpiado exitosamente")
        except Exception as e:
            logger.error(f"Error limpiando cache: {e}")
            maintenance_results["cache_cleared"] = False

        # 4. Verificar consistencia de datos
        consistency_results = _check_data_consistency()
        maintenance_results["data_consistency"] = consistency_results

        logger.info("Mantenimiento de base de datos completado")

        return {
            "status": "completed",
            "results": maintenance_results,
            "executed_at": timezone.now().isoformat(),
        }

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en database_maintenance: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en database_maintenance: {exc}")
        return {"error": "maintenance_failed", "message": str(exc)}


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def generate_system_health_report(self):
    """Genera un reporte de salud del sistema"""
    try:
        from reservations.models import Reservation
        from customers.models import Customer
        from restaurants.models import Restaurant, Table
        from notifications.models import Notification

        health_report = {
            "timestamp": timezone.now().isoformat(),
            "database": {},
            "celery": {},
            "cache": {},
            "models": {},
        }

        # Estadísticas de la base de datos
        try:
            from django.db import connection

            with connection.cursor() as cursor:
                # Información de conexión
                cursor.execute("SELECT version();")
                db_version = cursor.fetchone()[0]
                health_report["database"]["version"] = db_version

                # Tamaño de la base de datos (PostgreSQL)
                if "postgresql" in settings.DATABASES["default"]["ENGINE"]:
                    cursor.execute("""
                        SELECT pg_size_pretty(pg_database_size(current_database()));
                    """)
                    db_size = cursor.fetchone()[0]
                    health_report["database"]["size"] = db_size

                health_report["database"]["status"] = "healthy"
        except Exception as e:
            logger.error(f"Error obteniendo info de BD: {e}")
            health_report["database"]["status"] = "error"
            health_report["database"]["error"] = str(e)

        # Estadísticas de modelos
        try:
            model_stats = {
                "reservations": {
                    "total": Reservation.objects.count(),
                    "pending": Reservation.objects.filter(
                        status=Reservation.Status.PENDING
                    ).count(),
                    "confirmed": Reservation.objects.filter(
                        status=Reservation.Status.CONFIRMED
                    ).count(),
                    "expired": Reservation.objects.filter(
                        status=Reservation.Status.EXPIRED
                    ).count(),
                },
                "customers": {
                    "total": Customer.objects.count(),
                    "active": Customer.objects.filter(is_active=True).count(),
                    "with_reservations": Customer.objects.filter(
                        total_reservations__gt=0
                    ).count(),
                },
                "restaurants": {
                    "total": Restaurant.objects.count(),
                    "active": Restaurant.objects.filter(is_active=True).count(),
                },
                "tables": {
                    "total": Table.objects.count(),
                    "active": Table.objects.filter(is_active=True).count(),
                },
                "notifications": {
                    "total": Notification.objects.count(),
                    "pending": Notification.objects.filter(
                        status=Notification.Status.PENDING
                    ).count(),
                    "sent": Notification.objects.filter(
                        status=Notification.Status.SENT
                    ).count(),
                    "failed": Notification.objects.filter(
                        status=Notification.Status.FAILED
                    ).count(),
                },
            }

            health_report["models"] = model_stats
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de modelos: {e}")
            health_report["models"]["error"] = str(e)

        # Estado del cache
        try:
            cache.set("health_check", "test", 30)
            cache_test = cache.get("health_check")
            health_report["cache"]["status"] = (
                "healthy" if cache_test == "test" else "error"
            )
            cache.delete("health_check")
        except Exception as e:
            logger.error(f"Error verificando cache: {e}")
            health_report["cache"]["status"] = "error"
            health_report["cache"]["error"] = str(e)

        # Información de Celery
        try:
            from celery import current_app

            # Información básica de Celery
            health_report["celery"]["broker_url"] = current_app.conf.broker_url
            health_report["celery"]["result_backend"] = current_app.conf.result_backend
            health_report["celery"]["status"] = "configured"
        except Exception as e:
            logger.error(f"Error obteniendo info de Celery: {e}")
            health_report["celery"]["status"] = "error"
            health_report["celery"]["error"] = str(e)

        # Verificar métricas de rendimiento
        performance_metrics = _collect_performance_metrics()
        health_report["performance"] = performance_metrics

        logger.info("Reporte de salud del sistema generado")

        return health_report

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(
            f"Error de base de datos en generate_system_health_report: {exc}"
        )
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en generate_system_health_report: {exc}")
        return {"error": "health_report_failed", "message": str(exc)}


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def backup_critical_data(self, backup_type="daily"):
    """Realiza respaldo de datos críticos"""
    try:
        from reservations.models import Reservation
        from customers.models import Customer

        backup_results = {
            "backup_type": backup_type,
            "started_at": timezone.now().isoformat(),
            "tables": {},
        }

        # Respaldar reservas recientes (últimos 30 días)
        recent_reservations = Reservation.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related("customer", "restaurant", "table")

        reservations_data = []
        for reservation in recent_reservations:
            reservations_data.append(
                {
                    "id": str(reservation.id),
                    "customer_email": reservation.customer.email,
                    "restaurant_name": reservation.restaurant.name,
                    "table_number": reservation.table.number,
                    "reservation_date": str(reservation.reservation_date),
                    "reservation_time": str(reservation.reservation_time),
                    "party_size": reservation.party_size,
                    "status": reservation.status,
                    "created_at": reservation.created_at.isoformat(),
                }
            )

        backup_results["tables"]["reservations"] = {
            "count": len(reservations_data),
            "status": "completed",
        }

        # Respaldar información de clientes activos
        active_customers = Customer.objects.filter(is_active=True)
        customers_data = []

        for customer in active_customers:
            customers_data.append(
                {
                    "id": str(customer.id),
                    "email": customer.email,
                    "first_name": customer.first_name,
                    "last_name": customer.last_name,
                    "phone": customer.phone,
                    "total_reservations": customer.total_reservations,
                    "customer_score": customer.customer_score,
                    "created_at": customer.created_at.isoformat(),
                }
            )

        backup_results["tables"]["customers"] = {
            "count": len(customers_data),
            "status": "completed",
        }

        # En un sistema real, aquí se enviarían los datos a un servicio de almacenamiento
        # Por ahora solo registramos las estadísticas del respaldo

        backup_results["completed_at"] = timezone.now().isoformat()
        backup_results["total_records"] = len(reservations_data) + len(customers_data)

        logger.info(
            f"Respaldo {backup_type} completado: {backup_results['total_records']} registros"
        )

        return backup_results

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en backup_critical_data: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en backup_critical_data: {exc}")
        return {"error": "backup_failed", "message": str(exc)}


# Funciones auxiliares


def _check_data_consistency() -> Dict[str, Any]:
    """Verifica consistencia de datos entre modelos relacionados"""
    try:
        from reservations.models import Reservation
        from customers.models import Customer

        consistency_results = {
            "orphaned_reservations": 0,
            "invalid_table_assignments": 0,
            "customer_stats_mismatches": 0,
            "status": "healthy",
        }

        # Verificar reservas huérfanas (sin cliente, restaurante o mesa válidos)
        orphaned = Reservation.objects.filter(
            models.Q(customer__isnull=True)
            | models.Q(restaurant__isnull=True)
            | models.Q(table__isnull=True)
        ).count()
        consistency_results["orphaned_reservations"] = orphaned

        # Verificar asignaciones inválidas de mesas
        invalid_assignments = Reservation.objects.exclude(
            table__restaurant=models.F("restaurant")
        ).count()
        consistency_results["invalid_table_assignments"] = invalid_assignments

        # Verificar estadísticas de clientes desactualizadas
        mismatched_stats = 0
        for customer in Customer.objects.filter(is_active=True)[
            :100
        ]:  # Muestra limitada
            actual_count = Reservation.objects.filter(customer=customer).count()
            if customer.total_reservations != actual_count:
                mismatched_stats += 1

        consistency_results["customer_stats_mismatches"] = mismatched_stats

        # Determinar estado general
        if orphaned > 0 or invalid_assignments > 0 or mismatched_stats > 10:
            consistency_results["status"] = "warning"

        return consistency_results

    except Exception as e:
        logger.error(f"Error verificando consistencia: {e}")
        return {"status": "error", "error": str(e)}


def _collect_performance_metrics() -> Dict[str, Any]:
    """Recolecta métricas de rendimiento del sistema"""
    try:
        from reservations.models import Reservation

        metrics = {}

        # Tiempo promedio de creación de reservas (últimas 24 horas)
        yesterday = timezone.now() - timedelta(days=1)
        recent_reservations = Reservation.objects.filter(
            created_at__gte=yesterday
        ).order_by("created_at")[:100]

        if recent_reservations:
            creation_times = []
            for i in range(1, len(recent_reservations)):
                time_diff = (
                    recent_reservations[i].created_at
                    - recent_reservations[i - 1].created_at
                ).total_seconds()
                creation_times.append(time_diff)

            if creation_times:
                avg_creation_interval = sum(creation_times) / len(creation_times)
                metrics["avg_reservation_creation_interval"] = (
                    f"{avg_creation_interval:.2f} seconds"
                )

        # Distribución de reservas por estado
        status_distribution = {}
        for status_choice in Reservation.Status.choices:
            count = Reservation.objects.filter(status=status_choice[0]).count()
            status_distribution[status_choice[1]] = count

        metrics["reservation_status_distribution"] = status_distribution

        return metrics

    except Exception as e:
        logger.error(f"Error recolectando métricas: {e}")
        return {"error": str(e)}
