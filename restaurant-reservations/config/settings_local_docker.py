"""
Settings para tests usando servicios Docker corriendo localmente
"""

import os
from .settings import *  # noqa: F403, F401

# ================================
# CONFIGURACIÓN DE BASE DE DATOS TEMPORAL PARA TESTS
# ================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "restaurant_reservations",
        "USER": "postgres", 
        "PASSWORD": "postgres",
        "HOST": "localhost",  # Conectar al puerto expuesto localmente
        "PORT": "5434",       # Puerto expuesto por Docker
        "OPTIONS": {},
        "TEST": {
            "NAME": "test_restaurant_reservations_docker",  # BD temporal
        },
    }
}

# ================================
# REDIS PARA LOCKS Y CACHE
# ================================
REDIS_URL = "redis://localhost:6381/0"  # Puerto expuesto por Docker

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "db": 0,
        },
        "TIMEOUT": 300,
    }
}

# ================================
# CELERY CON REDIS EXTERNO
# ================================
CELERY_BROKER_URL = "redis://localhost:6381/0"
CELERY_RESULT_BACKEND = "redis://localhost:6381/0"

# Para tests, usaremos modo eager para control determinístico
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Configuración de Celery
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True

# ================================
# EMAIL - MOCK PARA TESTS
# ================================
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "test@reservaflow.com"

# ================================
# CONFIGURACIONES DE TESTS
# ================================
SECRET_KEY = "test-secret-key-for-docker-tests"
DEBUG = True
ALLOWED_HOSTS = ["*"]

# Timeout más corto para tests
RESERVATION_PENDING_TIMEOUT = 2  # 2 minutos

# ================================
# LOGGING SIMPLIFICADO
# ================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "reservations": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "restaurants": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

print("🐳 CONFIGURACIÓN DOCKER LOCAL CARGADA")
print(f"📊 Database: localhost:5434")
print(f"🔴 Redis: localhost:6381")
print(f"⚡ Celery Eager Mode: {CELERY_TASK_ALWAYS_EAGER}")