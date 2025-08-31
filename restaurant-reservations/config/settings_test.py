"""
Settings específicos para tests de integración realistas con Docker
"""

import os
from .settings import *  # noqa: F403, F401

# ================================
# CONFIGURACIÓN DE BASE DE DATOS TEMPORAL PARA TESTS
# ================================
# Django creará automáticamente una BD de test y la destruirá al final
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "restaurant_reservations",  # BD base para crear test_*
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "db",  # Usa el servicio PostgreSQL del docker-compose unificado
        "PORT": "5432",
        "OPTIONS": {},
        "TEST": {
            "NAME": "test_restaurant_reservations_realistic",  # BD temporal
        },
    }
}

# ================================
# REDIS REAL PARA LOCKS Y CACHE
# ================================
REDIS_URL = os.getenv(
    "REDIS_URL", "redis://redis:6379/0"
)  # Usa Redis del docker-compose unificado

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            # Usar el backend nativo de Django (compatible con redis-py 5.x)
            "db": 0,
        },
        "TIMEOUT": 300,  # 5 minutos default
    }
}

# ================================
# CELERY REAL (NO EAGER MODE)
# ================================
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL", "redis://redis:6379/0"
)  # Usa Redis del docker-compose unificado
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

# CRÍTICO: NO usar EAGER mode - queremos comportamiento real
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

# Configuración realista de Celery
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True

# Timeouts realistas
CELERY_TASK_SOFT_TIME_LIMIT = 60
CELERY_TASK_TIME_LIMIT = 120

# Retry configuration realista
CELERY_TASK_ANNOTATIONS = {
    "reservations.tasks.expire_reservation": {
        "rate_limit": "10/m",  # Máximo 10 por minuto
        "retry_delay": 60,
    },
    "reservations.tasks.send_confirmation_email": {
        "rate_limit": "50/m",
        "retry_delay": 30,
    },
    "reservations.tasks.send_reminder": {
        "rate_limit": "100/m",
        "retry_delay": 10,
    },
}

# ================================
# EMAIL - MOCK PARA TESTS
# ================================
# Seguimos usando locmem para no enviar emails reales
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "test@reservaflow.com"

# ================================
# LOGGING PARA DEBUGGING
# ================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "reservations": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
        "restaurants": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# ================================
# CONFIGURACIÓN ESPECÍFICA DE TESTS
# ================================

# Timeout más corto para tests
RESERVATION_PENDING_TIMEOUT = 2  # 2 minutos en lugar de 15

# Permitir conexiones desde contenedores Docker
ALLOWED_HOSTS = ["*"]


# Desabilitar migraciones en tests para velocidad (opcional)
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


# Descomenta si quieres tests más rápidos (pero menos realistas)
# MIGRATION_MODULES = DisableMigrations()

# ================================
# CONFIGURACIONES DE SEGURIDAD RELAJADAS PARA TESTS
# ================================
SECRET_KEY = "test-secret-key-not-for-production"
DEBUG = True

# CORS settings para tests
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = []

# ================================
# CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS
# ================================
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")  # noqa: F405
STATICFILES_DIRS = []

# ================================
# CONFIGURACIÓN DE TIMEOUTS PARA TESTS REALISTAS
# ================================
# Timeouts más cortos para acelerar tests pero mantener realismo
# DATABASES['default']['OPTIONS']['timeout'] = 10  # Comentado - no válido para PostgreSQL

# Redis connection timeout no es necesario con el backend nativo de Django

print("🧪 CONFIGURACIÓN DE TESTS REALISTAS CARGADA")
print(f"📊 Database: {DATABASES['default']['NAME']} @ {DATABASES['default']['HOST']}")
print(f"🔴 Redis: {REDIS_URL}")
print(f"📨 Celery Broker: {CELERY_BROKER_URL}")
print(f"⚡ Celery Eager Mode: {CELERY_TASK_ALWAYS_EAGER}")
