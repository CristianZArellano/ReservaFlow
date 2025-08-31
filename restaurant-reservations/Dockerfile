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
COPY pyproject.toml uv.lock ./

# Instalar uv y dependencias
RUN pip install uv
RUN uv sync --frozen

# Copiar resto del código
COPY . .

# Crear usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
