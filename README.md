# 🍽️ ReservaFlow

**ReservaFlow** is a web application for managing restaurant reservations, built with **Django** and **Django REST Framework**.

It provides a backend API for handling reservations, customers, and restaurants. The project is configured to use **PostgreSQL** as its database, **Celery** for asynchronous tasks (like sending notifications), and **Redis** as a message broker. The project is also set up for containerization with **Docker** and **Docker Compose**.

## 🚀 Features

*   **Online Reservation Management:** Manage your restaurant's reservations digitally.
*   **User Authentication:** Allows customers to register and log in securely.
*   **Restaurant Management:** Manage information about your establishments and tables.
*   **Admin Panel:** Use the Django Admin panel for centralized management.
*   **Notifications:** Send email notifications (configurable with Celery + Redis).
*   **Deployment:** Ready for production with **Docker** and **docker-compose**.

## 🛠️ Technologies Used

*   [Python 3.12+](https://www.python.org/)
*   [Django 5](https://www.djangoproject.com/)
*   [Django REST Framework (DRF)](https://www.django-rest-framework.org/)
*   [Celery](https://docs.celeryq.dev/) and [Redis](https://redis.io/) for background tasks
*   [PostgreSQL](https://www.postgresql.org/) as the main database
*   [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
*   [uv](https://github.com/astral-sh/uv) for dependency management

## 📦 Local Development Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/CristianZArellano/ReservaFlow.git
    cd ReservaFlow/restaurant-reservations
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    ```

3.  **Activate the virtual environment:**
    ```bash
    source .venv/bin/activate  # Linux/Mac
    .venv\Scripts\activate     # Windows
    ```

4.  **Create the `.env` file:**
    In the `restaurant-reservations` directory, create a `.env` file with the following content:
    ```env
    SECRET_KEY=your_secret_key
    DEBUG=True
    DATABASE_URL=postgres://user:password@localhost:5432/reservaflow
    REDIS_URL=redis://localhost:6379/0
    ```

5.  **Run database migrations and create a superuser:**
    ```bash
    uv run python manage.py migrate
    uv run python manage.py createsuperuser
    ```

6.  **Start the development server:**
    ```bash
    uv run python manage.py runserver
    ```

## 🐳 Docker Deployment

To run the application using Docker, execute the following command from the `restaurant-reservations` directory:

```bash
docker-compose up --build
```

This will start the Django application, PostgreSQL database, Redis server, and Celery workers.

## 🔬 Development Conventions

*   **Dependency Management:** Project dependencies are managed with `uv` and are listed in the `pyproject.toml` file.
*   **Code Style:** The project uses `ruff` for linting and formatting.
    *   `ruff check .` (lint)
    *   `ruff format .` (format)
*   **Testing:** The project is set up to use `pytest` for testing.
    *   `pytest`

## 📂 Project Structure

The project is organized into the following directories inside `restaurant-reservations`:

*   `config/`: Project-level configuration, including `settings.py` and `urls.py`.
*   `customers/`: Django app for managing customer information.
*   `notifications/`: Django app for handling notifications.
*   `reservations/`: Django app for managing reservations.
*   `restaurants/`: Django app for managing restaurant information and tables.

### Data Models

*   **Customer:** Represents a customer with basic contact information and reservation statistics.
*   **Restaurant:** Represents a restaurant with details about its operation, and includes a `Table` model for managing tables and an `Image` model for storing images.
*   **Reservation:** Represents a reservation made by a customer for a specific restaurant and table. It includes the reservation date, time, party size, and status.
*   **Notification:** This model is not yet defined.

## Architecture and Design

ReservaFlow is built with a modular architecture, typical of Django projects. Here are some key design decisions:

### Asynchronous Task Handling with Celery

The application uses Celery to handle long-running or periodic tasks in the background, ensuring the user-facing API remains fast and responsive. The main tasks are:

*   **Reservation Expiration (`expire_reservation`):** When a reservation is created, it has a `pending` status and an expiration time. A Celery task is scheduled to run at the expiration time. If the reservation hasn't been confirmed by then, the task updates its status to `expired`.
*   **Email Notifications (`send_confirmation_email`, `send_reminder`):** Celery is used to send emails asynchronously. This includes confirmation emails when a reservation is made and reminder emails sent 24 hours before the reservation time.

### Preventing Double Bookings with a Distributed Lock

To handle concurrent requests and prevent the same table from being booked at the same time by different users, the system implements a distributed lock using Redis.

*   **`TableReservationLock`:** This service creates a unique lock in Redis for a specific table and time slot. When a user tries to book a table, the system attempts to acquire this lock.
*   If the lock is already held by another request, the system returns a `423 Locked` error, indicating that the resource is temporarily unavailable.
*   Once the reservation is created (or fails), the lock is released, allowing other users to book that table.

### Caching for Performance

The system uses Django's caching framework (configured with Redis) to improve performance when checking table availability.

*   **`check_table_availability`:** This function first checks the cache to see if the availability for a specific table and time has been recently queried. If so, it returns the cached result. Otherwise, it queries the database and caches the result for future requests.

## API Reference

The API is available under the `/api/` prefix.

### Reservation Endpoints

*   **Endpoint:** `/api/reservations/`
*   **Model:** `Reservation`
*   **ViewSet:** `ReservationViewSet`

#### List Reservations

*   **Method:** `GET`
*   **URL:** `/api/reservations/`
*   **Description:** Retrieves a list of all reservations.
*   **Success Response (200 OK):**
    ```json
    [
        {
            "id": "uuid-of-reservation",
            "status": "confirmed",
            "reservation_date": "YYYY-MM-DD",
            "reservation_time": "HH:MM:SS"
        }
    ]
    ```

#### Retrieve a Reservation

*   **Method:** `GET`
*   **URL:** `/api/reservations/{id}/`
*   **Description:** Retrieves a specific reservation by its ID.
*   **Success Response (200 OK):**
    ```json
    {
        "id": "uuid-of-reservation",
        "status": "pending",
        "expires_at": "YYYY-MM-DDTHH:MM:SSZ"
    }
    ```
*   **Error Response (404 Not Found):**
    ```json
    {
        "error": "Reserva no encontrada"
    }
    ```

#### Create a Reservation

*   **Method:** `POST`
*   **URL:** `/api/reservations/`
*   **Description:** Creates a new reservation for a table. This endpoint uses a distributed lock to prevent double bookings.
*   **Body (JSON):**
    ```json
    {
        "restaurant_id": 1,
        "customer_id": 1,
        "table_id": 1,
        "reservation_date": "YYYY-MM-DD",
        "reservation_time": "HH:MM:SS",
        "party_size": 2
    }
    ```
*   **Success Response (201 Created):**
    ```json
    {
        "id": "new-uuid-of-reservation",
        "status": "pending",
        "expires_at": "YYYY-MM-DDTHH:MM:SSZ",
        "message": "Reserva creada exitosamente"
    }
    ```
*   **Error Responses:**
    *   **400 Bad Request:** If required fields are missing.
        ```json
        {
            "error": "Faltan campos requeridos"
        }
        ```
    *   **409 Conflict:** If the table is not available.
        ```json
        {
            "error": "Mesa no disponible en esa fecha/hora"
        }
        ```
    *   **423 Locked:** If another user is currently trying to book the same table.
        ```json
        {
            "error": "Mesa está siendo reservada: Mesa ya está siendo reservada por otro cliente"
        }
        ```

## 👨‍💻 Author

Project developed by **Cristian Z. Arellano**

*   **GitHub:** [CristianZArellano](https://github.com/CristianZArellano)

## 📜 License

This project is under the **MIT** license. You can use, modify, and distribute it freely.

✨ Happy coding!