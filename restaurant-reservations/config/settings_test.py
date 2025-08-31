"""
Settings específicos para tests de integración realistas con Docker
"""
import os
from .settings import *

# ================================
# CONFIGURACIÓN DE BASE DE DATOS REAL
# ================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'reservaflow_test'),
        'USER': os.getenv('POSTGRES_USER', 'test_user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'test_password'),
        'HOST': os.getenv('POSTGRES_HOST', 'test-db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'charset': 'utf8',
        },
        'TEST': {
            # Para tests, usar la misma DB (Docker maneja aislamiento)
            'NAME': os.getenv('POSTGRES_DB', 'reservaflow_test'),
        }
    }
}

# ================================
# REDIS REAL PARA LOCKS Y CACHE
# ================================
REDIS_URL = os.getenv('REDIS_URL', 'redis://test-redis:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 300,  # 5 minutos default
    }
}

# ================================
# CELERY REAL (NO EAGER MODE)
# ================================
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://test-redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://test-redis:6379/0')

# CRÍTICO: NO usar EAGER mode - queremos comportamiento real
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

# Configuración realista de Celery
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Timeouts realistas
CELERY_TASK_SOFT_TIME_LIMIT = 60
CELERY_TASK_TIME_LIMIT = 120

# Retry configuration realista
CELERY_TASK_ANNOTATIONS = {
    'reservations.tasks.expire_reservation': {
        'rate_limit': '10/m',  # Máximo 10 por minuto
        'retry_delay': 60,
    },
    'reservations.tasks.send_confirmation_email': {
        'rate_limit': '50/m',
        'retry_delay': 30,
    },
    'reservations.tasks.send_reminder': {
        'rate_limit': '100/m',
        'retry_delay': 10,
    }
}

# ================================
# EMAIL - MOCK PARA TESTS
# ================================
# Seguimos usando locmem para no enviar emails reales
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'test@reservaflow.com'

# ================================
# LOGGING PARA DEBUGGING
# ================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'reservations': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'restaurants': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# ================================
# CONFIGURACIÓN ESPECÍFICA DE TESTS
# ================================

# Timeout más corto para tests
RESERVATION_PENDING_TIMEOUT = 2  # 2 minutos en lugar de 15

# Permitir conexiones desde contenedores Docker
ALLOWED_HOSTS = ['*']

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
SECRET_KEY = 'test-secret-key-not-for-production'
DEBUG = True

# CORS settings para tests
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = []

# ================================
# CONFIGURACIÓN DE TIMEOUTS PARA TESTS REALISTAS
# ================================
# Timeouts más cortos para acelerar tests pero mantener realismo
DATABASES['default']['OPTIONS']['timeout'] = 10

# Redis connection timeout
CACHES['default']['OPTIONS']['CONNECTION_POOL_KWARGS'] = {
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
}

print("🧪 CONFIGURACIÓN DE TESTS REALISTAS CARGADA")
print(f"📊 Database: {DATABASES['default']['NAME']} @ {DATABASES['default']['HOST']}")
print(f"🔴 Redis: {REDIS_URL}")
print(f"📨 Celery Broker: {CELERY_BROKER_URL}")
print(f"⚡ Celery Eager Mode: {CELERY_TASK_ALWAYS_EAGER}")