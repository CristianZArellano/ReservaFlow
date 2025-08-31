#!/usr/bin/env python3
"""
Test script para verificar que Django funciona en el contenedor Docker
"""

import os
import sys
import django
from pathlib import Path

# Configuración del entorno
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_test')
os.environ.setdefault('POSTGRES_HOST', 'localhost')
os.environ.setdefault('POSTGRES_PORT', '5433')
os.environ.setdefault('POSTGRES_DB', 'reservaflow_test')
os.environ.setdefault('POSTGRES_USER', 'test_user')
os.environ.setdefault('POSTGRES_PASSWORD', 'test_password')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6380/0')

# Configuración de Django
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

def test_imports():
    """Test que Django y todas las apps se importen correctamente"""
    try:
        from django.conf import settings
        print("✅ Django configurado correctamente")
        
        from reservations.models import Reservation
        print("✅ Modelos de reservations importados")
        
        from reservations.tasks import send_confirmation_email
        print("✅ Tasks de Celery importadas")
        
        from restaurants.services import TableReservationLock
        print("✅ Servicios de restaurants importados")
        
        return True
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False

def test_database_connection():
    """Test conexión a la base de datos"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                print("✅ Conexión a la base de datos exitosa")
                return True
    except Exception as e:
        print(f"❌ Error de conexión a BD: {e}")
        return False

def main():
    """Función principal de test"""
    print("🧪 Iniciando tests de configuración Docker...")
    
    tests = [
        test_imports,
        test_database_connection,
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Resultado: {passed}/{len(tests)} tests pasaron")
    
    if passed == len(tests):
        print("🎉 Todos los tests pasaron! El contenedor está funcionando correctamente")
        return 0
    else:
        print("❌ Algunos tests fallaron")
        return 1

if __name__ == "__main__":
    sys.exit(main())