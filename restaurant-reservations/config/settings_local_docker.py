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
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # Base de datos en memoria para tests rápidos
    }
}

# ================================
# REDIS PARA LOCKS Y CACHE - FALLBACK A LOCMEM
# ================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# ================================
# CELERY CON MODO EAGER
# ================================
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

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
print(f"📊 Database: localhost:5436")
print(f"🔴 Redis: localhost:6385")
print(f"⚡ Celery Eager Mode: {CELERY_TASK_ALWAYS_EAGER}")