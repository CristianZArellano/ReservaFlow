# config/management/commands/celery_status.py
from django.core.management.base import BaseCommand
import json

from config.monitoring import TaskMonitor, HealthChecker


class Command(BaseCommand):
    help = "Muestra el estado de Celery y estadísticas de tareas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--task", type=str, help="Mostrar estadísticas de una tarea específica"
        )
        parser.add_argument(
            "--health",
            action="store_true",
            help="Mostrar verificación de salud completa",
        )
        parser.add_argument(
            "--queues", action="store_true", help="Mostrar información de colas"
        )
        parser.add_argument(
            "--json", action="store_true", help="Salida en formato JSON"
        )
        parser.add_argument(
            "--reset-stats",
            action="store_true",
            help="Resetear estadísticas de monitoreo",
        )

    def handle(self, *args, **options):
        if options["reset_stats"]:
            self.reset_statistics()
            return

        if options["health"]:
            self.show_health_check(options["json"])
        elif options["queues"]:
            self.show_queue_info(options["json"])
        elif options["task"]:
            self.show_task_stats(options["task"], options["json"])
        else:
            self.show_general_stats(options["json"])

    def show_general_stats(self, as_json=False):
        """Muestra estadísticas generales"""
        stats = TaskMonitor.get_task_stats()

        if as_json:
            self.stdout.write(json.dumps(stats, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS("=== Estadísticas Generales de Celery ===")
            )
            self.stdout.write(f"Tareas iniciadas: {stats['total']['started']}")
            self.stdout.write(f"Tareas exitosas: {stats['total']['success']}")
            self.stdout.write(f"Tareas fallidas: {stats['total']['failure']}")
            self.stdout.write(f"Tareas reintentadas: {stats['total']['retry']}")

            # Calcular tasa de éxito
            total = stats["total"]["started"]
            if total > 0:
                success_rate = (stats["total"]["success"] / total) * 100
                self.stdout.write(f"Tasa de éxito: {success_rate:.2f}%")

    def show_task_stats(self, task_name, as_json=False):
        """Muestra estadísticas de una tarea específica"""
        stats = TaskMonitor.get_task_stats(task_name)

        if as_json:
            self.stdout.write(json.dumps(stats, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"=== Estadísticas de {task_name} ===")
            )
            self.stdout.write(f"Iniciadas: {stats['started']}")
            self.stdout.write(f"Exitosas: {stats['success']}")
            self.stdout.write(f"Fallidas: {stats['failure']}")
            self.stdout.write(f"Reintentos: {stats['retry']}")

            if "duration" in stats:
                duration = stats["duration"]
                self.stdout.write("\nDuraciones:")
                self.stdout.write(f"  Promedio: {duration['avg']:.2f}s")
                self.stdout.write(f"  Mínima: {duration['min']:.2f}s")
                self.stdout.write(f"  Máxima: {duration['max']:.2f}s")
                self.stdout.write(f"  Muestras: {duration['count']}")

    def show_health_check(self, as_json=False):
        """Muestra verificación de salud completa"""
        health = HealthChecker.check_celery_health()

        if as_json:
            self.stdout.write(json.dumps(health, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS("=== Verificación de Salud de Celery ===")
            )

            # Estado general
            status_color = (
                self.style.SUCCESS
                if health["status"] == "healthy"
                else self.style.ERROR
            )
            self.stdout.write(
                f"Estado general: {status_color(health['status'].upper())}"
            )

            # Broker
            self.stdout.write("\n--- Broker ---")
            broker_status = health["broker"].get("status", "unknown")
            broker_color = (
                self.style.SUCCESS if broker_status == "healthy" else self.style.ERROR
            )
            self.stdout.write(f"Estado: {broker_color(broker_status.upper())}")
            self.stdout.write(f"URL: {health['broker'].get('url', 'N/A')}")

            if "error" in health["broker"]:
                self.stdout.write(
                    f"Error: {self.style.ERROR(health['broker']['error'])}"
                )

            # Workers
            self.stdout.write("\n--- Workers ---")
            workers = health["workers"]
            worker_count = workers.get("count", 0)
            worker_color = (
                self.style.SUCCESS if worker_count > 0 else self.style.WARNING
            )
            self.stdout.write(f"Workers activos: {worker_color(str(worker_count))}")

            if "nodes" in workers:
                for node in workers["nodes"]:
                    self.stdout.write(f"  - {node}")

            if "error" in workers:
                self.stdout.write(f"Error: {self.style.ERROR(workers['error'])}")

            # Tareas
            self.stdout.write("\n--- Resumen de Tareas ---")
            tasks = health["tasks"]["total"]
            self.stdout.write(f"Total iniciadas: {tasks['started']}")
            self.stdout.write(f"Exitosas: {tasks['success']}")
            self.stdout.write(f"Fallidas: {tasks['failure']}")

    def show_queue_info(self, as_json=False):
        """Muestra información de colas"""
        queue_info = HealthChecker.get_task_queue_info()

        if as_json:
            self.stdout.write(json.dumps(queue_info, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS("=== Información de Colas ==="))

            if "error" in queue_info:
                self.stdout.write(f"Error: {self.style.ERROR(queue_info['error'])}")
                return

            # Tareas activas
            if "total_active" in queue_info:
                self.stdout.write(f"Tareas activas: {queue_info['total_active']}")
                if "active_tasks" in queue_info:
                    for worker, count in queue_info["active_tasks"].items():
                        self.stdout.write(f"  {worker}: {count}")

            # Tareas reservadas
            if "total_reserved" in queue_info:
                self.stdout.write(f"Tareas en cola: {queue_info['total_reserved']}")
                if "reserved_tasks" in queue_info:
                    for worker, count in queue_info["reserved_tasks"].items():
                        self.stdout.write(f"  {worker}: {count}")

            # Tareas programadas
            if "total_scheduled" in queue_info:
                self.stdout.write(
                    f"Tareas programadas: {queue_info['total_scheduled']}"
                )
                if "scheduled_tasks" in queue_info:
                    for worker, count in queue_info["scheduled_tasks"].items():
                        self.stdout.write(f"  {worker}: {count}")

    def reset_statistics(self):
        """Resetea las estadísticas de monitoreo"""
        TaskMonitor.reset_stats()
        self.stdout.write(
            self.style.SUCCESS("Estadísticas de monitoreo reseteadas exitosamente")
        )
