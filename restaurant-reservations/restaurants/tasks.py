# restaurants/tasks.py
import logging
from datetime import timedelta, date, datetime

from celery import shared_task
from django.db import transaction, OperationalError, models
from django.utils import timezone

from .models import Restaurant, Table

logger = logging.getLogger(__name__)

# Definir excepciones específicas para retry
DATABASE_RETRY_EXCEPTIONS = (OperationalError,)


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def calculate_restaurant_stats(self, restaurant_id):
    """Calcula estadísticas de un restaurante específico"""
    try:
        from reservations.models import Reservation

        with transaction.atomic():
            restaurant = Restaurant.objects.select_for_update().get(id=restaurant_id)

            # Estadísticas de reservas
            reservations = Reservation.objects.filter(restaurant=restaurant)

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

            # Estadísticas de las últimas 30 días
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_reservations = reservations.filter(created_at__gte=thirty_days_ago)
            recent_completed = recent_reservations.filter(
                status=Reservation.Status.COMPLETED
            ).count()

            # Calcular tasas
            completion_rate = (
                (completed_reservations / total_reservations * 100)
                if total_reservations > 0
                else 0
            )
            cancellation_rate = (
                (cancelled_reservations / total_reservations * 100)
                if total_reservations > 0
                else 0
            )
            no_show_rate = (
                (no_show_count / total_reservations * 100)
                if total_reservations > 0
                else 0
            )

            # Ocupación promedio por mesa
            tables = Table.objects.filter(restaurant=restaurant, is_active=True)
            total_capacity = sum(table.capacity for table in tables)

            # Estadísticas de ocupación
            occupancy_stats = {
                "total_tables": tables.count(),
                "total_capacity": total_capacity,
                "avg_party_size": reservations.aggregate(
                    avg_size=models.Avg("party_size")
                )["avg_size"]
                or 0,
            }

            stats = {
                "total_reservations": total_reservations,
                "confirmed_reservations": confirmed_reservations,
                "completed_reservations": completed_reservations,
                "cancelled_reservations": cancelled_reservations,
                "no_show_count": no_show_count,
                "recent_completed": recent_completed,
                "completion_rate": round(completion_rate, 2),
                "cancellation_rate": round(cancellation_rate, 2),
                "no_show_rate": round(no_show_rate, 2),
                "occupancy_stats": occupancy_stats,
                "last_updated": timezone.now(),
            }

            logger.info(f"Estadísticas calculadas para restaurante {restaurant_id}")

            return {
                "restaurant_id": str(restaurant.id),
                "stats": stats,
                "status": "calculated",
            }

    except Restaurant.DoesNotExist:
        logger.warning(f"Restaurante {restaurant_id} no encontrado")
        return {"restaurant_id": restaurant_id, "error": "not_found"}

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en calculate_restaurant_stats: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error no recuperable en calculate_restaurant_stats: {exc}")
        return {
            "restaurant_id": restaurant_id,
            "error": "permanent_failure",
            "message": str(exc),
        }


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def optimize_table_assignments(self, restaurant_id, target_date=None):
    """Optimiza la asignación de mesas para un restaurante en una fecha específica"""
    try:
        from reservations.models import Reservation

        restaurant = Restaurant.objects.get(id=restaurant_id)

        if target_date is None:
            target_date = timezone.now().date()
        elif isinstance(target_date, str):
            target_date = datetime.fromisoformat(target_date).date()

        # Obtener reservas del día
        reservations = (
            Reservation.objects.filter(
                restaurant=restaurant,
                reservation_date=target_date,
                status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED],
            )
            .select_related("table")
            .order_by("reservation_time", "party_size")
        )

        if not reservations.exists():
            logger.info(
                f"No hay reservas para optimizar en {restaurant.name} el {target_date}"
            )
            return {
                "restaurant_id": str(restaurant.id),
                "target_date": str(target_date),
                "optimized": 0,
                "status": "no_reservations",
            }

        # Obtener mesas disponibles
        tables = Table.objects.filter(restaurant=restaurant, is_active=True).order_by(
            "capacity", "number"
        )

        optimized_count = 0
        recommendations = []

        for reservation in reservations:
            current_table = reservation.table
            party_size = reservation.party_size

            # Encontrar mesa más eficiente
            optimal_table = None
            min_waste = float("inf")

            for table in tables:
                if table.capacity >= party_size:
                    # Verificar disponibilidad en el horario
                    conflicts = Reservation.objects.filter(
                        table=table,
                        reservation_date=target_date,
                        reservation_time=reservation.reservation_time,
                        status__in=[
                            Reservation.Status.PENDING,
                            Reservation.Status.CONFIRMED,
                        ],
                    ).exclude(id=reservation.id)

                    if not conflicts.exists():
                        waste = table.capacity - party_size
                        if waste < min_waste:
                            min_waste = waste
                            optimal_table = table

            # Si encontramos una mesa mejor que la actual
            if (
                optimal_table
                and optimal_table != current_table
                and (
                    current_table is None
                    or optimal_table.capacity < current_table.capacity
                )
            ):
                recommendations.append(
                    {
                        "reservation_id": str(reservation.id),
                        "current_table": str(current_table.id)
                        if current_table
                        else None,
                        "recommended_table": str(optimal_table.id),
                        "party_size": party_size,
                        "current_capacity": current_table.capacity
                        if current_table
                        else None,
                        "recommended_capacity": optimal_table.capacity,
                        "efficiency_gain": (
                            current_table.capacity - optimal_table.capacity
                        )
                        if current_table
                        else optimal_table.capacity - party_size,
                    }
                )
                optimized_count += 1

        logger.info(
            f"Optimización completada para {restaurant.name}: {optimized_count} recomendaciones"
        )

        return {
            "restaurant_id": str(restaurant.id),
            "target_date": str(target_date),
            "total_reservations": reservations.count(),
            "optimized": optimized_count,
            "recommendations": recommendations,
            "status": "optimized",
        }

    except Restaurant.DoesNotExist:
        logger.warning(f"Restaurante {restaurant_id} no encontrado")
        return {"restaurant_id": restaurant_id, "error": "not_found"}

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en optimize_table_assignments: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en optimize_table_assignments: {exc}")
        return {
            "restaurant_id": restaurant_id,
            "error": "optimization_failed",
            "message": str(exc),
        }


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def generate_availability_report(self, restaurant_id, start_date=None, days_ahead=7):
    """Genera reporte de disponibilidad para un restaurante"""
    try:
        from reservations.models import Reservation

        restaurant = Restaurant.objects.get(id=restaurant_id)

        if start_date is None:
            start_date = timezone.now().date()
        elif isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)

        end_date = start_date + timedelta(days=days_ahead)

        # Obtener todas las mesas activas
        tables = Table.objects.filter(restaurant=restaurant, is_active=True)
        total_tables = tables.count()
        total_capacity = sum(table.capacity for table in tables)

        availability_report = {
            "restaurant_id": str(restaurant.id),
            "restaurant_name": restaurant.name,
            "total_tables": total_tables,
            "total_capacity": total_capacity,
            "period": {
                "start_date": str(start_date),
                "end_date": str(end_date),
                "days": days_ahead,
            },
            "daily_availability": [],
        }

        # Analizar cada día
        current_date = start_date
        while current_date <= end_date:
            # Verificar si el restaurante está abierto
            if not restaurant.is_open_on_day(current_date.weekday()):
                availability_report["daily_availability"].append(
                    {
                        "date": str(current_date),
                        "is_open": False,
                        "reason": "Restaurant closed",
                    }
                )
                current_date += timedelta(days=1)
                continue

            # Obtener horarios disponibles
            available_times = restaurant.get_available_times(current_date)

            # Calcular reservas existentes
            reservations = Reservation.objects.filter(
                restaurant=restaurant,
                reservation_date=current_date,
                status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED],
            )

            reservations_by_time = {}
            for reservation in reservations:
                time_str = reservation.reservation_time.strftime("%H:%M")
                if time_str not in reservations_by_time:
                    reservations_by_time[time_str] = []
                reservations_by_time[time_str].append(
                    {
                        "table_id": str(reservation.table.id),
                        "party_size": reservation.party_size,
                        "capacity_used": reservation.table.capacity,
                    }
                )

            # Calcular disponibilidad por franja horaria
            time_slots = []
            for time_slot in available_times:
                time_str = time_slot.strftime("%H:%M")
                reserved_tables = len(reservations_by_time.get(time_str, []))
                available_tables = total_tables - reserved_tables

                # Calcular capacidad disponible
                reserved_capacity = sum(
                    res["capacity_used"]
                    for res in reservations_by_time.get(time_str, [])
                )
                available_capacity = total_capacity - reserved_capacity

                utilization_rate = (
                    (reserved_capacity / total_capacity * 100)
                    if total_capacity > 0
                    else 0
                )

                time_slots.append(
                    {
                        "time": time_str,
                        "available_tables": available_tables,
                        "reserved_tables": reserved_tables,
                        "available_capacity": available_capacity,
                        "reserved_capacity": reserved_capacity,
                        "utilization_rate": round(utilization_rate, 2),
                    }
                )

            # Calcular métricas del día
            daily_reservations = reservations.count()
            avg_utilization = (
                sum(slot["utilization_rate"] for slot in time_slots) / len(time_slots)
                if time_slots
                else 0
            )

            availability_report["daily_availability"].append(
                {
                    "date": str(current_date),
                    "is_open": True,
                    "total_reservations": daily_reservations,
                    "avg_utilization": round(avg_utilization, 2),
                    "time_slots": time_slots,
                    "peak_utilization": max(
                        slot["utilization_rate"] for slot in time_slots
                    )
                    if time_slots
                    else 0,
                }
            )

            current_date += timedelta(days=1)

        # Calcular métricas del período
        open_days = [
            day for day in availability_report["daily_availability"] if day["is_open"]
        ]
        if open_days:
            period_avg_utilization = sum(
                day["avg_utilization"] for day in open_days
            ) / len(open_days)
            total_period_reservations = sum(
                day["total_reservations"] for day in open_days
            )

            availability_report["period_summary"] = {
                "avg_utilization": round(period_avg_utilization, 2),
                "total_reservations": total_period_reservations,
                "open_days": len(open_days),
                "busiest_day": max(open_days, key=lambda d: d["avg_utilization"])[
                    "date"
                ]
                if open_days
                else None,
            }

        logger.info(f"Reporte de disponibilidad generado para {restaurant.name}")

        return availability_report

    except Restaurant.DoesNotExist:
        logger.warning(f"Restaurante {restaurant_id} no encontrado")
        return {"restaurant_id": restaurant_id, "error": "not_found"}

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en generate_availability_report: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en generate_availability_report: {exc}")
        return {
            "restaurant_id": restaurant_id,
            "error": "report_failed",
            "message": str(exc),
        }


@shared_task(
    bind=True,
    autoretry_for=DATABASE_RETRY_EXCEPTIONS,
    retry_backoff=True,
    max_retries=3,
)
def update_table_status(self, table_id, is_active=None, maintenance_reason=None):
    """Actualiza el estado de una mesa (mantenimiento, limpieza, etc.)"""
    try:
        with transaction.atomic():
            table = Table.objects.select_for_update().get(id=table_id)

            if is_active is not None:
                table.is_active = is_active

            if maintenance_reason:
                table.notes = f"Mantenimiento: {maintenance_reason} - {timezone.now().strftime('%Y-%m-%d %H:%M')}"

            table.save(update_fields=["is_active", "notes"])

            # Si se desactiva una mesa, verificar reservas futuras
            if is_active is False:
                from reservations.models import Reservation

                future_reservations = Reservation.objects.filter(
                    table=table,
                    reservation_date__gte=timezone.now().date(),
                    status__in=[
                        Reservation.Status.PENDING,
                        Reservation.Status.CONFIRMED,
                    ],
                )

                affected_reservations = future_reservations.count()

                if affected_reservations > 0:
                    logger.warning(
                        f"Mesa {table.number} desactivada con {affected_reservations} reservas futuras"
                    )

                    return {
                        "table_id": str(table.id),
                        "status": "deactivated_with_conflicts",
                        "affected_reservations": affected_reservations,
                        "message": f"Mesa desactivada pero tiene {affected_reservations} reservas futuras que requieren reasignación",
                    }

            logger.info(
                f"Estado de mesa {table.number} actualizado: activa={table.is_active}"
            )

            return {
                "table_id": str(table.id),
                "table_number": table.number,
                "is_active": table.is_active,
                "maintenance_reason": maintenance_reason,
                "status": "updated",
            }

    except Table.DoesNotExist:
        logger.warning(f"Mesa {table_id} no encontrada")
        return {"table_id": table_id, "error": "not_found"}

    except DATABASE_RETRY_EXCEPTIONS as exc:
        logger.warning(f"Error de base de datos en update_table_status: {exc}")
        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)

    except Exception as exc:
        logger.error(f"Error en update_table_status: {exc}")
        return {"table_id": table_id, "error": "update_failed", "message": str(exc)}
