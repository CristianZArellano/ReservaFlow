#!/bin/bash

# Detener y eliminar contenedores, redes y volúmenes anónimos
echo "🛑 Apagando contenedores..."
docker compose down

# Reconstruir imágenes y levantar en segundo plano
echo "🚀 Levantando contenedores con build..."
docker compose up --build -d

# Mostrar estado
echo "📋 Estado de los contenedores:"
docker compose ps
