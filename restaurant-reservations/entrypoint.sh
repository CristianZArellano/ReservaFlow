#!/bin/bash
set -e

# Configurar variables de entorno para Django
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"
export PYTHONPATH="/app:$PYTHONPATH"

# Ejecutar el comando pasado como argumentos
exec "$@"