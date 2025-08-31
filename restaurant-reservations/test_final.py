#!/usr/bin/env python
"""
Test final para verificar que el sistema completo funciona
sin errores de CONNECTION_POOL_KWARGS
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")

import django

django.setup()


def test_redis_connection():
    """Test conexión a Redis usando Django cache"""
    from django.core.cache import cache

    print("🧪 Probando conexión Redis con Django cache...")
    try:
        cache.set("test_final", "funcionando", 30)
        result = cache.get("test_final")

        if result == "funcionando":
            print("✅ Django Redis Cache: OK")
            return True
        else:
            print("❌ Django Redis Cache: Falló")
            return False
    except Exception as e:
        print(f"❌ Django Redis Cache Error: {e}")
        return False


def test_redis_locks():
    """Test locks distribuidos Redis"""
    from restaurants.services import TableReservationLock
    from datetime import date

    print("🔐 Probando locks distribuidos Redis...")
    try:
        lock = TableReservationLock(
            table_id=1, date=date(2025, 9, 15), time_slot="19:00"
        )

        acquired = lock.acquire()
        if acquired:
            print("✅ Redis Distributed Lock: OK")
            lock.release()
            return True
        else:
            print("❌ Redis Distributed Lock: No se pudo adquirir")
            return False

    except Exception as e:
        print(f"❌ Redis Distributed Lock Error: {e}")
        return False


def test_database():
    """Test conexión a base de datos"""
    from django.db import connection

    print("💾 Probando conexión a base de datos...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

        if result:
            print("✅ Database Connection: OK")
            return True
        else:
            print("❌ Database Connection: Falló")
            return False
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return False


if __name__ == "__main__":
    print("🚀 VERIFICACIÓN FINAL DEL SISTEMA ReservaFlow")
    print("=" * 50)

    tests = [
        ("Redis Connection", test_redis_connection),
        ("Redis Distributed Locks", test_redis_locks),
        ("Database Connection", test_database),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}:")
        if test_func():
            passed += 1

    print("\n" + "=" * 50)
    print(f"📊 RESULTADO: {passed}/{total} tests pasados")

    if passed == total:
        print("✅ SISTEMA COMPLETAMENTE FUNCIONAL")
        print("✅ Error CONNECTION_POOL_KWARGS RESUELTO")
        print("✅ ReservaFlow listo para desarrollo y tests realistas")
    else:
        print("❌ Algunos tests fallaron")

    print("\n🌐 Aplicación disponible en: http://127.0.0.1:8000")
    print("🔍 Health check: http://127.0.0.1:8000/health/")
