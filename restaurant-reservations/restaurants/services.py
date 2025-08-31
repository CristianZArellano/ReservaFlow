import redis
import time
import logging
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


# Cliente de Redis con configuración robusta
def get_redis_client():
    """Obtener cliente Redis con manejo de errores (compatible redis-py 5.x)"""
    try:
        client = redis.from_url(
            settings.REDIS_URL or "redis://localhost:6379/0", decode_responses=False
        )
        # Test de conexión
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis no disponible: {e}")
        return None


redis_client = get_redis_client()


class TableReservationLock:
    """Lock distribuido robusto para evitar dobles reservas"""

    def __init__(self, table_id, date, time_slot, timeout=30, max_retries=3):
        self.lock_key = f"table_lock:{table_id}:{date}:{time_slot}"
        self.timeout = timeout
        self.max_retries = max_retries
        self.lock_acquired = False
        self.lock_value = f"{time.time()}"  # Valor único para el lock

    def acquire(self, retry_delay=0.1):
        """Intenta obtener el lock con retry automático"""
        global redis_client

        if redis_client is None:
            logger.warning("Redis no disponible - usando fallback local")
            return True  # Fallback para testing/desarrollo

        for attempt in range(self.max_retries):
            try:
                # Usar SET con NX y EX para operación atómica
                result = redis_client.set(
                    self.lock_key, self.lock_value, ex=self.timeout, nx=True
                )

                if result:
                    self.lock_acquired = True
                    logger.debug(
                        f"Lock adquirido: {self.lock_key} (intento {attempt + 1})"
                    )
                    return True

                # Lock ya existe, verificar si ha expirado manualmente
                current_value = redis_client.get(self.lock_key)
                if current_value is None:
                    # El lock expiró entre medias, intentar de nuevo
                    continue

                logger.debug(f"Lock ocupado: {self.lock_key} (intento {attempt + 1})")

                # Backoff exponencial
                if attempt < self.max_retries - 1:
                    sleep_time = retry_delay * (2**attempt)
                    time.sleep(sleep_time)

            except redis.RedisError as e:
                logger.error(f"Error Redis en acquire: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(retry_delay * (2**attempt))
                    # Intentar reconectar
                    new_client = get_redis_client()
                    if new_client is not None:
                        redis_client = new_client
                    else:
                        break
                else:
                    logger.error(f"Fallo definitivo adquiriendo lock: {self.lock_key}")

        return False

    def release(self):
        """Libera el lock de forma segura"""
        if not self.lock_acquired:
            return True

        if redis_client is None:
            self.lock_acquired = False
            return True

        try:
            # Script Lua para release atómico (solo libera si somos el owner)
            lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
            """
            result = redis_client.eval(lua_script, 1, self.lock_key, self.lock_value)

            if result == 1:
                logger.debug(f"Lock liberado: {self.lock_key}")
                self.lock_acquired = False
                return True
            else:
                logger.warning(f"Lock ya no nos pertenece: {self.lock_key}")
                self.lock_acquired = False
                return False

        except redis.RedisError as e:
            logger.error(f"Error Redis en release: {e}")
            self.lock_acquired = False
            return False

    def extend_lock(self, additional_time=30):
        """Extiende el tiempo de vida del lock"""
        if not self.lock_acquired or redis_client is None:
            return False

        try:
            # Script Lua para extender solo si somos el owner
            lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("expire", KEYS[1], ARGV[2])
                else
                    return 0
                end
            """
            result = redis_client.eval(
                lua_script, 1, self.lock_key, self.lock_value, additional_time
            )

            return result == 1

        except redis.RedisError as e:
            logger.error(f"Error extendiendo lock: {e}")
            return False

    def __enter__(self):
        if not self.acquire():
            raise LockAcquisitionError(
                f"No se pudo adquirir lock para mesa después de {self.max_retries} intentos. "
                f"Mesa probablemente ocupada o Redis no disponible."
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.release()
        except Exception as e:
            logger.error(f"Error liberando lock: {e}")

    def __del__(self):
        """Cleanup en caso de que no se libere explícitamente"""
        if self.lock_acquired:
            try:
                self.release()
            except Exception:
                pass


class LockAcquisitionError(Exception):
    """Excepción específica para fallos de adquisición de lock"""

    pass


def check_table_availability(table_id, date, time_slot, use_cache=True):
    """Verifica si una mesa está disponible usando cache con invalidación inteligente"""
    cache_key = f"availability:{table_id}:{date}:{time_slot}"

    # Intentar obtener desde cache si está habilitado
    if use_cache:
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit para disponibilidad: {cache_key}")
            return cached_result

    # Si no está en cache, verificar en base de datos
    from reservations.models import Reservation

    try:
        # Usar query optimizada con índice
        conflicts = (
            Reservation.objects.filter(
                table_id=table_id,
                reservation_date=date,
                reservation_time=time_slot,
                status__in=["pending", "confirmed"],
            )
            .only("id")
            .exists()
        )  # Solo traer el ID para optimizar

        available = not conflicts

        # Guardar en cache por tiempo variable según disponibilidad
        if use_cache:
            if available:
                # Si está disponible, cache por más tiempo
                cache.set(cache_key, available, 600)  # 10 minutos
            else:
                # Si no está disponible, cache por menos tiempo por si cambia
                cache.set(cache_key, available, 120)  # 2 minutos

        logger.debug(f"DB query para disponibilidad: {cache_key} = {available}")
        return available

    except Exception as e:
        logger.error(f"Error verificando disponibilidad: {e}")
        # En caso de error, asumir no disponible por seguridad
        return False


def invalidate_table_availability_cache(table_id, date, time_slot):
    """Invalida el cache de disponibilidad para una mesa específica"""
    cache_key = f"availability:{table_id}:{date}:{time_slot}"
    cache.delete(cache_key)
    logger.debug(f"Cache invalidado: {cache_key}")


def get_connection_health():
    """Verificar estado de conexiones de servicios"""
    health = {
        "redis": False,
        "database": False,
        "timestamp": timezone.now().isoformat(),
    }

    # Test Redis
    try:
        if redis_client:
            redis_client.ping()
            health["redis"] = True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")

    # Test Database
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            health["database"] = True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")

    return health
