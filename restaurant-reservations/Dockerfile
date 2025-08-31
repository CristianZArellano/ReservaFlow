FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para tests
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias primero (para cache de Docker)
COPY pyproject.toml ./

# Instalar dependencias directamente con pip
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

# Copiar resto del código
COPY . .

# Crear usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash app \
    && chmod +x entrypoint.sh \
    && chown -R app:app /app

# Configurar variables de entorno
ENV PYTHONPATH="/app"
ENV DJANGO_SETTINGS_MODULE="config.settings"

USER app

EXPOSE 8000

# Usar entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
