-----

# 🍽️ ReservaFlow

**ReservaFlow** es una aplicación web desarrollada en **Django** que permite gestionar reservas de restaurantes de manera sencilla y eficiente.

-----

## 🚀 Características

  * **Gestión de reservas en línea:** Controla las reservas de tu restaurante de manera digital.
  * **Autenticación de usuarios:** Permite a los clientes registrarse y acceder de forma segura.
  * **Administración de restaurantes:** Gestiona la información de tus establecimientos y mesas.
  * **Panel administrativo:** Utiliza el panel de Django Admin para una gestión centralizada.
  * **Notificaciones:** Envía notificaciones por correo (configurable con Celery + Redis).
  * **Despliegue:** Preparado para producción con **Docker** y **docker-compose**.

-----

## 🛠️ Tecnologías utilizadas

  * [Python 3.12+](https://www.python.org/)
  * [Django 5](https://www.djangoproject.com/)
  * [Django REST Framework (DRF)](https://www.django-rest-framework.org/)
  * [Celery](https://docs.celeryq.dev/) y [Redis](https://redis.io/) para tareas en segundo plano
  * [PostgreSQL](https://www.postgresql.org/) como base de datos principal
  * [Docker](https://www.docker.com/) y [Docker Compose](https://docs.docker.com/compose/)
  * [uv](https://github.com/astral-sh/uv) para la gestión de dependencias

-----

## 📦 Instalación y configuración con `uv`

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/CristianZArellano/ReservaFlow.git
    cd ReservaFlow
    ```
2.  **Instala las dependencias:**
    ```bash
    uv sync
    ```
3.  **Activa el entorno virtual:**
    ```bash
    source .venv/bin/activate  # Linux/Mac
    .venv\Scripts\activate     # Windows
    ```
4.  **Crea el archivo `.env`:**
    ```env
    SECRET_KEY=tu_secret_key
    DEBUG=True
    DATABASE_URL=postgres://usuario:password@localhost:5432/reservaflow
    REDIS_URL=redis://localhost:6379/0
    ```
5.  **Ejecuta las migraciones y crea un superusuario:**
    ```bash
    uv run python manage.py migrate
    uv run python manage.py createsuperuser
    ```
6.  **Inicia el servidor:**
    ```bash
    uv run python manage.py runserver
    ```

-----

## 🐳 Uso con Docker

Si prefieres usar Docker, ejecuta este comando para levantar todos los servicios:

```bash
docker-compose up --build
```

Esto iniciará:

  * La aplicación de Django
  * La base de datos PostgreSQL
  * El servidor de Redis
  * Celery y Celery Beat para las tareas en segundo plano

-----

## 📂 Estructura del proyecto

```
ReservaFlow/
├── config/             # Configuración del proyecto
├── apps/               # Aplicaciones internas
├── templates/          # Archivos HTML
├── static/             # Archivos estáticos (CSS, JS, imágenes)
├── pyproject.toml      # Gestión de dependencias con uv
├── docker-compose.yml
├── Dockerfile
├── .gitignore
├── README.md
```

-----

## 👨‍💻 Autor

Proyecto desarrollado por **Cristian Z. Arellano**

  * **GitHub:** [CristianZArellano](https://github.com/CristianZArellano)

-----

## 📜 Licencia

Este proyecto está bajo la licencia **MIT**. Puedes usarlo, modificarlo y distribuirlo libremente.

✨ ¡Listo para gestionar reservas de restaurantes de forma eficiente\!
