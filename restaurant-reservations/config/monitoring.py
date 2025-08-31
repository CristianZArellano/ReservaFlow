# config/monitoring.py
import logging
import time
from typing import Dict, Any

from celery.signals import (
    task_prerun,
    task_postrun,
    task_failure,
    task_success,
    worker_ready,
)
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger("celery.monitoring")


class TaskMonitor:
    """Monitor para tareas de Celery con métricas y alertas"""

    CACHE_PREFIX = "celery_monitor"

    @staticmethod
    def get_cache_key(key: str) -> str:
        """Genera clave de cache con prefijo"""
        return f"{TaskMonitor.CACHE_PREFIX}:{key}"

    @staticmethod
    def record_task_start(task_id: str, task_name: str) -> None:
        """Registra el inicio de una tarea"""
        start_time = time.time()
        cache.set(
            TaskMonitor.get_cache_key(f"task_start:{task_id}"),
            {
                "task_name": task_name,
                "start_time": start_time,
                "started_at": timezone.now().isoformat(),
            },
            timeout=3600,  # 1 hora
        )

        # Incrementar contador de tareas iniciadas
        TaskMonitor._increment_counter(f"tasks_started:{task_name}")
        TaskMonitor._increment_counter("tasks_started:total")

    @staticmethod
    def record_task_end(
        task_id: str, task_name: str, state: str, result: Any = None
    ) -> None:
        """Registra el final de una tarea"""
        end_time = time.time()

        # Obtener tiempo de inicio
        start_data = cache.get(TaskMonitor.get_cache_key(f"task_start:{task_id}"))
        duration = None

        if start_data:
            duration = end_time - start_data["start_time"]
            # Limpiar datos de inicio
            cache.delete(TaskMonitor.get_cache_key(f"task_start:{task_id}"))

        # Registrar métricas
        TaskMonitor._increment_counter(f"tasks_{state.lower()}:{task_name}")
        TaskMonitor._increment_counter(f"tasks_{state.lower()}:total")

        if duration is not None:
            TaskMonitor._record_duration(task_name, duration)

        # Log del resultado
        if state == "SUCCESS":
            logger.info(
                f"Task {task_name} [{task_id}] completed successfully in {duration:.2f}s"
                if duration
                else f"Task {task_name} [{task_id}] completed successfully"
            )
        elif state == "FAILURE":
            logger.error(
                f"Task {task_name} [{task_id}] failed in {duration:.2f}s"
                if duration
                else f"Task {task_name} [{task_id}] failed"
            )

        # Alertas para tareas críticas fallidas
        if state == "FAILURE" and task_name in TaskMonitor._get_critical_tasks():
            TaskMonitor._send_alert(task_name, task_id, "FAILURE", result)

    @staticmethod
    def _increment_counter(key: str) -> None:
        """Incrementa contador en cache"""
        cache_key = TaskMonitor.get_cache_key(f"counter:{key}")
        try:
            current = cache.get(cache_key, 0)
            cache.set(cache_key, current + 1, timeout=86400)  # 24 horas
        except Exception as e:
            logger.warning(f"Error incrementing counter {key}: {e}")

    @staticmethod
    def _record_duration(task_name: str, duration: float) -> None:
        """Registra duración de tarea para estadísticas"""
        cache_key = TaskMonitor.get_cache_key(f"durations:{task_name}")
        try:
            durations = cache.get(cache_key, [])
            durations.append(duration)

            # Mantener solo las últimas 100 duraciones
            if len(durations) > 100:
                durations = durations[-100:]

            cache.set(cache_key, durations, timeout=86400)  # 24 horas
        except Exception as e:
            logger.warning(f"Error recording duration for {task_name}: {e}")

    @staticmethod
    def _get_critical_tasks() -> list:
        """Lista de tareas críticas que requieren alertas"""
        return [
            "maintenance.tasks.cleanup_expired_reservations",
            "notifications.tasks.process_pending_notifications",
            "maintenance.tasks.database_maintenance",
            "reservations.tasks.expire_reservation",
            "reservations.tasks.send_confirmation_email",
        ]

    @staticmethod
    def _send_alert(
        task_name: str, task_id: str, alert_type: str, details: Any = None
    ) -> None:
        """Envía alerta para tarea crítica fallida"""
        alert_key = TaskMonitor.get_cache_key(f"alert:{task_name}:{alert_type}")

        # Evitar spam de alertas (máximo 1 por tarea por hora)
        if cache.get(alert_key):
            return

        cache.set(alert_key, True, timeout=3600)  # 1 hora

        logger.critical(
            f"ALERT: Critical task {task_name} [{task_id}] {alert_type.lower()}",
            extra={
                "task_name": task_name,
                "task_id": task_id,
                "alert_type": alert_type,
                "details": str(details) if details else None,
                "timestamp": timezone.now().isoformat(),
            },
        )

    @staticmethod
    def get_task_stats(task_name: str = None) -> Dict[str, Any]:
        """Obtiene estadísticas de tareas"""
        stats = {}

        if task_name:
            # Estadísticas específicas de una tarea
            stats = {
                "task_name": task_name,
                "started": cache.get(
                    TaskMonitor.get_cache_key(f"counter:tasks_started:{task_name}"), 0
                ),
                "success": cache.get(
                    TaskMonitor.get_cache_key(f"counter:tasks_success:{task_name}"), 0
                ),
                "failure": cache.get(
                    TaskMonitor.get_cache_key(f"counter:tasks_failure:{task_name}"), 0
                ),
                "retry": cache.get(
                    TaskMonitor.get_cache_key(f"counter:tasks_retry:{task_name}"), 0
                ),
            }

            # Estadísticas de duración
            durations = cache.get(
                TaskMonitor.get_cache_key(f"durations:{task_name}"), []
            )
            if durations:
                stats["duration"] = {
                    "avg": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "count": len(durations),
                }

        else:
            # Estadísticas globales
            stats = {
                "total": {
                    "started": cache.get(
                        TaskMonitor.get_cache_key("counter:tasks_started:total"), 0
                    ),
                    "success": cache.get(
                        TaskMonitor.get_cache_key("counter:tasks_success:total"), 0
                    ),
                    "failure": cache.get(
                        TaskMonitor.get_cache_key("counter:tasks_failure:total"), 0
                    ),
                    "retry": cache.get(
                        TaskMonitor.get_cache_key("counter:tasks_retry:total"), 0
                    ),
                }
            }

        return stats

    @staticmethod
    def reset_stats() -> None:
        """Resetea todas las estadísticas"""
        try:
            # Eliminar claves principales del monitor
            cache.delete_many(
                [
                    TaskMonitor.get_cache_key("counter:tasks_started:total"),
                    TaskMonitor.get_cache_key("counter:tasks_success:total"),
                    TaskMonitor.get_cache_key("counter:tasks_failure:total"),
                    TaskMonitor.get_cache_key("counter:tasks_retry:total"),
                ]
            )

            logger.info("Task monitoring stats reset")

        except Exception as e:
            logger.error(f"Error resetting task stats: {e}")


# Signal handlers para Celery


@task_prerun.connect
def task_prerun_handler(
    sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds
):
    """Handler ejecutado antes del inicio de cada tarea"""
    TaskMonitor.record_task_start(task_id, task.name)


@task_postrun.connect
def task_postrun_handler(
    sender=None,
    task_id=None,
    task=None,
    args=None,
    kwargs=None,
    retval=None,
    state=None,
    **kwds,
):
    """Handler ejecutado después de cada tarea"""
    TaskMonitor.record_task_end(task_id, task.name, state or "UNKNOWN", retval)


@task_failure.connect
def task_failure_handler(
    sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds
):
    """Handler específico para fallos de tareas"""
    if sender:
        TaskMonitor.record_task_end(task_id, sender.name, "FAILURE", str(exception))

        # Log adicional del traceback para tareas críticas
        if sender.name in TaskMonitor._get_critical_tasks():
            logger.error(
                f"Critical task failure: {sender.name} [{task_id}]",
                extra={
                    "task_name": sender.name,
                    "task_id": task_id,
                    "exception": str(exception),
                    "traceback": str(traceback),
                },
            )


@task_success.connect
def task_success_handler(sender=None, result=None, **kwds):
    """Handler específico para éxito de tareas"""
    # El postrun handler ya maneja esto, pero podemos agregar lógica adicional aquí
    pass


@worker_ready.connect
def worker_ready_handler(sender=None, **kwds):
    """Handler ejecutado cuando un worker está listo"""
    logger.info(f"Celery worker ready: {sender}")

    # Registrar worker activo
    worker_key = TaskMonitor.get_cache_key(f"worker:{sender}")
    cache.set(
        worker_key,
        {"status": "ready", "started_at": timezone.now().isoformat()},
        timeout=3600,
    )


# Utilidades adicionales para monitoreo


class HealthChecker:
    """Verificador de salud del sistema Celery"""

    @staticmethod
    def check_celery_health() -> Dict[str, Any]:
        """Verifica el estado de salud de Celery"""
        from celery import current_app

        health = {
            "status": "unknown",
            "broker": {},
            "workers": {},
            "tasks": {},
            "timestamp": timezone.now().isoformat(),
        }

        try:
            # Verificar conexión al broker
            conn = current_app.connection()
            conn.ensure_connection(max_retries=3)
            health["broker"]["status"] = "healthy"
            health["broker"]["url"] = current_app.conf.broker_url
        except Exception as e:
            health["broker"]["status"] = "unhealthy"
            health["broker"]["error"] = str(e)

        try:
            # Información de workers activos
            inspect = current_app.control.inspect()
            active_workers = inspect.active()

            if active_workers:
                health["workers"]["count"] = len(active_workers)
                health["workers"]["nodes"] = list(active_workers.keys())
                health["workers"]["status"] = "healthy"
            else:
                health["workers"]["count"] = 0
                health["workers"]["status"] = "no_workers"
        except Exception as e:
            health["workers"]["status"] = "error"
            health["workers"]["error"] = str(e)

        # Estadísticas de tareas
        health["tasks"] = TaskMonitor.get_task_stats()

        # Estado general
        if (
            health["broker"].get("status") == "healthy"
            and health["workers"].get("count", 0) > 0
        ):
            health["status"] = "healthy"
        elif health["broker"].get("status") == "healthy":
            health["status"] = "degraded"  # Broker OK pero sin workers
        else:
            health["status"] = "unhealthy"

        return health

    @staticmethod
    def get_task_queue_info() -> Dict[str, Any]:
        """Obtiene información sobre las colas de tareas"""
        from celery import current_app

        queue_info = {}

        try:
            inspect = current_app.control.inspect()

            # Tareas activas
            active = inspect.active()
            if active:
                queue_info["active_tasks"] = {
                    worker: len(tasks) for worker, tasks in active.items()
                }
                queue_info["total_active"] = sum(queue_info["active_tasks"].values())

            # Tareas reservadas (en cola)
            reserved = inspect.reserved()
            if reserved:
                queue_info["reserved_tasks"] = {
                    worker: len(tasks) for worker, tasks in reserved.items()
                }
                queue_info["total_reserved"] = sum(
                    queue_info["reserved_tasks"].values()
                )

            # Tareas programadas
            scheduled = inspect.scheduled()
            if scheduled:
                queue_info["scheduled_tasks"] = {
                    worker: len(tasks) for worker, tasks in scheduled.items()
                }
                queue_info["total_scheduled"] = sum(
                    queue_info["scheduled_tasks"].values()
                )

        except Exception as e:
            queue_info["error"] = str(e)

        return queue_info
