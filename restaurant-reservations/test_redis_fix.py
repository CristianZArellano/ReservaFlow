#!/usr/bin/env python
"""
Script de prueba simple para verificar que la configuración de Redis funcione
sin el error CONNECTION_POOL_KWARGS
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_test')

import django
django.setup()

try:
    from django.core.cache import cache
    from django.conf import settings
    
    print("🧪 Probando configuración de Redis...")
    print(f"Redis URL: {settings.REDIS_URL}")
    
    # Test básico de conexión
    cache.set('test_connection', 'OK', 30)
    result = cache.get('test_connection')
    
    if result == 'OK':
        print("✅ Redis connection exitosa - sin error CONNECTION_POOL_KWARGS")
        print("✅ Configuración corregida para redis-py 5.x")
    else:
        print("❌ Redis connection falló")
        
except Exception as e:
    print(f"❌ Error: {e}")
    if "CONNECTION_POOL_KWARGS" in str(e):
        print("❌ Todavía hay problema con CONNECTION_POOL_KWARGS")
    else:
        print("❌ Error diferente de CONNECTION_POOL_KWARGS")