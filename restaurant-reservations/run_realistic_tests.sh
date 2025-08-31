#!/bin/bash
set -e

echo "🚀 EJECUTANDO TESTS REALISTAS CON DOCKER COMPOSE UNIFICADO"
echo "============================================================"

# Asegurar que los servicios estén corriendo
echo "📊 Iniciando servicios Redis y Celery si no están corriendo..."
docker-compose up -d redis celery-worker

# Esperar a que Redis esté listo
echo "⏳ Esperando a que Redis esté listo..."
timeout 30s bash -c 'until docker-compose exec redis redis-cli ping | grep PONG; do sleep 1; done' || {
    echo "❌ Error: Redis no está respondiendo"
    exit 1
}

echo "✅ Redis está listo"

# Verificar que Celery worker esté corriendo
echo "⏳ Verificando que Celery worker esté activo..."
sleep 5  # Dar tiempo a que Celery se inicie

echo "🧪 Ejecutando tests realistas..."
echo ""

# Ejecutar tests realistas usando DJANGO_SETTINGS_MODULE para tests
docker-compose run --rm \
    -e DJANGO_SETTINGS_MODULE=config.settings_test \
    web \
    uv run python -m pytest tests/realistic/ -v --tb=short

# Mostrar estado de los servicios después de los tests
echo ""
echo "📊 Estado de servicios después de tests:"
docker-compose ps

echo ""
echo "✅ Tests realistas completados"
echo "💡 La base de datos de test fue creada y destruida automáticamente por Django"
echo "💡 Redis y Celery mantuvieron estado real durante los tests"