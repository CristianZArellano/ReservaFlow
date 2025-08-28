import redis
from django.conf import settings
from django.core.cache import cache

# Cliente de Redis (usa la URL de settings o localhost por defecto)
redis_client = redis.from_url(settings.REDIS_URL or "redis://localhost:6379/0")


class TableReservationLock:
    """Lock distribuido para evitar dobles reservas de la misma mesa"""

    def __init__(self, table_id, date, time_slot):
        # Clave única por mesa + fecha + franja horaria
        self.lock_key = f"table_lock:{table_id}:{date}:{time_slot}"
        self.timeout = 30  # Lock expira en 30 segundos

    def acquire(self):
        """Intenta obtener el lock"""
        return redis_client.set(self.lock_key, "locked", ex=self.timeout, nx=True)

    def release(self):
        """Libera el lock"""
        redis_client.delete(self.lock_key)

    def __enter__(self):
        if not self.acquire():
            raise Exception("Mesa ya está siendo reservada por otro cliente")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def check_table_availability(table_id, date, time_slot):
    """Verifica si una mesa está disponible usando cache"""
    cache_key = f"availability:{table_id}:{date}:{time_slot}"

    # Intentar obtener desde cache
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    # Si no está en cache, verificar en base de datos
    from reservations.models import Reservation

    conflicts = Reservation.objects.filter(
        table_id=table_id,
        reservation_date=date,
        reservation_time=time_slot,
        status__in=["pending", "confirmed"],
    ).exists()

    available = not conflicts

    # Guardar en cache por 5 minutos
    cache.set(cache_key, available, 300)

    return available
