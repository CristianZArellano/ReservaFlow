#!/bin/bash

echo "🚀 PROBANDO SETUP COMPLETO DE DOCKER - RESERVAFLOW"
echo "=================================================================="

# Detener servicios existentes
echo "🛑 Deteniendo servicios existentes..."
docker compose -f docker-compose.test.yml down --volumes

# Rebuild imagen con nueva dependencia
echo "🔨 Construyendo nueva imagen con dependencias actualizadas..."
docker build -f Dockerfile -t reservaflow-test .

# Iniciar solo servicios base
echo "🗄️  Iniciando servicios base (PostgreSQL y Redis)..."
docker compose -f docker-compose.test.yml up -d test-db test-redis

# Esperar a que servicios estén listos
echo "⏳ Esperando servicios base..."
sleep 15

# Probar configuración
echo "🧪 Probando configuración de Django..."
docker run --rm --network reservaflow_test_network \
  -e POSTGRES_HOST=restaurant-reservations-test-db-1 \
  -e POSTGRES_PORT=5432 \
  -e REDIS_URL=redis://restaurant-reservations-test-redis-1:6379/0 \
  -e DJANGO_SETTINGS_MODULE=config.settings_test \
  reservaflow-test python test_docker.py

if [ $? -eq 0 ]; then
    echo "✅ Configuración básica funciona!"
    
    echo "🚀 Iniciando servicio web completo..."
    docker compose -f docker-compose.test.yml up test-web --build
else
    echo "❌ Configuración básica falló"
    exit 1
fi

echo "🎉 ¡Setup completo!"