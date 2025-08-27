FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos
COPY pyproject.toml uv.lock ./
COPY . .

# Instalar uv y dependencias
RUN pip install uv
RUN uv sync

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
