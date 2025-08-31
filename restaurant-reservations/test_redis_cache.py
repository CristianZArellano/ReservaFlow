#!/usr/bin/env python3
"""
Test específico para verificar que django-redis funciona correctamente
"""

import os
import sys
import django
from pathlib import Path

# Configuración del entorno
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")
os.environ.setdefault("POSTGRES_DB", "reservaflow_test")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")

# Configuración de Django
sys.path.insert(0, str(Path(__file__).parent))
django.setup()


def test_redis_cache():
    """Test que el cache de Redis funcione"""
    try:
        from django.core.cache import cache

        # Test básico de cache
        test_key = "test_key_123"
        test_value = "test_value_123"

        cache.set(test_key, test_value, timeout=30)
        cached_value = cache.get(test_key)

        if cached_value == test_value:
            print("✅ Redis cache funcionando correctamente")
            return True
        else:
            print(
                f"❌ Error en Redis cache: esperado '{test_value}', obtenido '{cached_value}'"
            )
            return False

    except Exception as e:
        print(f"❌ Error en Redis cache: {e}")
        return False


def main():
    """Función principal de test"""
    print("🧪 Test específico de django-redis...")

    # Import test
    try:
        import django_redis  # noqa: F401

        print("✅ django-redis importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando django-redis: {e}")
        return 1

    # Cache test
    if test_redis_cache():
        print("🎉 django-redis configurado y funcionando correctamente!")
        return 0
    else:
        print("❌ Problemas con la configuración de django-redis")
        return 1


if __name__ == "__main__":
    sys.exit(main())
