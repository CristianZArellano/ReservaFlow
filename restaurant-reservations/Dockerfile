FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    curl \
    netcat-openbsd \
    git \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv globalmente usando pip
RUN pip install --no-cache-dir uv

# Copiar archivos de proyecto
COPY . .

# Sincronizar dependencias con uv
RUN uv sync --no-cache

# Configurar variables de entorno
ENV PYTHONPATH="/app"
ENV DJANGO_SETTINGS_MODULE="config.settings"

EXPOSE 8000

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
