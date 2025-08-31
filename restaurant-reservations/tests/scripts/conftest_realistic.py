"""
Configuración de pytest para tests realistas con servicios Docker reales
"""
import os
import pytest
import redis
import time
from celery import current_app
from django.conf import settings
from django.test import TransactionTestCase
from django.core.management import call_command
from django.db import connections


@pytest.fixture(scope="session", autouse=True)
def django_db_setup():
    """Configuración de base de datos para tests realistas"""
    # Asegurar que estamos usando la configuración correcta
    assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'
    assert not settings.CELERY_TASK_ALWAYS_EAGER
    
    print("🐘 Configurando base de datos PostgreSQL para tests realistas...")
    
    # Ejecutar migraciones
    call_command('migrate', verbosity=0, interactive=False)
    
    # Verificar conexión a la base de datos
    db = connections['default']
    with db.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"📊 PostgreSQL conectado: {version}")
    
    yield
    
    # Cleanup después de todos los tests
    print("🧹 Limpiando base de datos...")


@pytest.fixture(scope="session", autouse=True)
def redis_setup():
    """Configuración de Redis para tests realistas"""
    print("🔴 Verificando conexión a Redis...")
    
    # Verificar que Redis está disponible
    redis_client = redis.from_url(settings.REDIS_URL)
    
    try:
        redis_client.ping()
        info = redis_client.info()
        print(f"🔴 Redis conectado: {info['redis_version']}")
        
        # Limpiar Redis antes de los tests
        redis_client.flushall()
        print("🔴 Redis limpio para tests")
        
    except redis.ConnectionError as e:
        pytest.fail(f"❌ No se puede conectar a Redis: {e}")
    
    yield redis_client
    
    # Cleanup después de tests
    print("🔴 Limpiando Redis...")
    redis_client.flushall()


@pytest.fixture(scope="session", autouse=True) 
def celery_setup():
    """Configuración de Celery para tests realistas"""
    print("📨 Verificando workers de Celery...")
    
    # Verificar que hay workers disponibles
    inspect = current_app.control.inspect()
    
    # Esperar hasta que haya workers disponibles
    max_retries = 30
    for i in range(max_retries):
        stats = inspect.stats()
        if stats:
            worker_count = len(stats)
            print(f"📨 {worker_count} workers de Celery disponibles")
            break
        print(f"⏳ Esperando workers Celery ({i+1}/{max_retries})...")
        time.sleep(1)
    else:
        pytest.fail("❌ No hay workers de Celery disponibles")
    
    # Purgar cola antes de tests
    current_app.control.purge()
    print("📨 Cola de Celery purgada")
    
    yield current_app
    
    # Cleanup después de tests
    print("📨 Purgando cola de Celery...")
    current_app.control.purge()


@pytest.fixture
def clean_redis():
    """Limpiar Redis antes de cada test que lo necesite"""
    redis_client = redis.from_url(settings.REDIS_URL)
    redis_client.flushall()
    yield redis_client
    redis_client.flushall()


@pytest.fixture
def clean_celery():
    """Limpiar cola de Celery antes de cada test que lo necesite"""
    current_app.control.purge()
    yield current_app
    current_app.control.purge()


# Configuración de marcadores de pytest
def pytest_configure(config):
    """Configurar marcadores personalizados"""
    config.addinivalue_line(
        "markers", "redis: tests que requieren Redis real"
    )
    config.addinivalue_line(
        "markers", "celery: tests que requieren workers Celery reales"
    )
    config.addinivalue_line(
        "markers", "concurrency: tests de concurrencia real"
    )
    config.addinivalue_line(
        "markers", "database: tests que requieren PostgreSQL real"
    )
    config.addinivalue_line(
        "markers", "slow: tests que pueden tardar más de 30 segundos"
    )
    config.addinivalue_line(
        "markers", "integration: tests de integración completa"
    )


def pytest_collection_modifyitems(config, items):
    """Modificar colección de tests para manejar marcadores"""
    for item in items:
        # Marcar automáticamente tests según su contenido
        if "redis" in str(item.fspath).lower():
            item.add_marker(pytest.mark.redis)
        
        if "celery" in str(item.fspath).lower():
            item.add_marker(pytest.mark.celery)
        
        if "concurrent" in item.name.lower():
            item.add_marker(pytest.mark.concurrency)
        
        if "database" in str(item.fspath).lower():
            item.add_marker(pytest.mark.database)
        
        if "realistic" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.slow)


@pytest.fixture
def realistic_test_environment():
    """Fixture que proporciona entorno completo para tests realistas"""
    environment_info = {
        'database': {
            'engine': settings.DATABASES['default']['ENGINE'],
            'name': settings.DATABASES['default']['NAME'],
            'host': settings.DATABASES['default']['HOST'],
        },
        'redis': {
            'url': settings.REDIS_URL,
        },
        'celery': {
            'broker': settings.CELERY_BROKER_URL,
            'eager_mode': settings.CELERY_TASK_ALWAYS_EAGER,
        }
    }
    
    # Verificar que estamos en modo realista
    assert not settings.CELERY_TASK_ALWAYS_EAGER, "Tests realistas requieren Celery NO-EAGER"
    assert 'postgresql' in settings.DATABASES['default']['ENGINE'], "Tests realistas requieren PostgreSQL"
    assert 'redis' in settings.REDIS_URL, "Tests realistas requieren Redis"
    
    print(f"🧪 Entorno de tests realistas configurado: {environment_info}")
    
    return environment_info