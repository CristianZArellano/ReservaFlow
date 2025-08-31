# ReservaFlow API Documentation

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, the API does not require authentication for development. In production, you should implement proper authentication (JWT, OAuth, etc.).

## API Endpoints

### Restaurants

#### GET /api/restaurants/restaurants/
Lista todos los restaurantes

**Response:**
```json
{
    "count": 10,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "Restaurant Name",
            "description": "Restaurant description",
            "address": "123 Main St",
            "phone": "+1-555-1234",
            "email": "contact@restaurant.com",
            "website": "https://restaurant.com",
            "cuisine_type": "italian",
            "price_range": "mid",
            "opening_time": "09:00:00",
            "closing_time": "22:00:00",
            "reservation_duration": 120,
            "advance_booking_days": 30,
            "min_party_size": 1,
            "max_party_size": 12,
            "accepts_walk_ins": true,
            "requires_deposit": false,
            "cancellation_hours": 24,
            "total_capacity": 100,
            "total_reservations": 150,
            "average_rating": 4.5,
            "is_active": true,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z"
        }
    ]
}
```

#### GET /api/restaurants/restaurants/{id}/
Obtiene un restaurante específico

#### POST /api/restaurants/restaurants/
Crea un nuevo restaurante

**Request Body:**
```json
{
    "name": "New Restaurant",
    "description": "A great place to eat",
    "address": "456 Oak Ave",
    "phone": "+1-555-5678",
    "email": "info@newrestaurant.com",
    "cuisine_type": "mexican",
    "price_range": "high",
    "opening_time": "11:00:00",
    "closing_time": "23:00:00"
}
```

#### PUT /api/restaurants/restaurants/{id}/
Actualiza un restaurante completo

#### PATCH /api/restaurants/restaurants/{id}/
Actualización parcial de un restaurante

#### DELETE /api/restaurants/restaurants/{id}/
Elimina un restaurante

### Tables

#### GET /api/restaurants/tables/
Lista todas las mesas

**Response:**
```json
{
    "count": 20,
    "results": [
        {
            "id": 1,
            "restaurant": 1,
            "number": "T001",
            "capacity": 4,
            "min_capacity": 2,
            "location": "indoor",
            "shape": "round",
            "is_accessible": true,
            "has_view": false,
            "is_quiet": false,
            "has_high_chairs": true,
            "requires_special_request": false,
            "special_notes": "Near the window",
            "is_active": true,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z"
        }
    ]
}
```

#### GET /api/restaurants/tables/{id}/
Obtiene una mesa específica

#### POST /api/restaurants/tables/
Crea una nueva mesa

#### PUT /api/restaurants/tables/{id}/
Actualiza una mesa completa

#### PATCH /api/restaurants/tables/{id}/
Actualización parcial de una mesa

#### DELETE /api/restaurants/tables/{id}/
Elimina una mesa

### Customers

#### GET /api/customers/customers/
Lista todos los clientes

**Response:**
```json
{
    "count": 50,
    "results": [
        {
            "id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@email.com",
            "phone": "+1-555-9876",
            "birth_date": "1990-01-15",
            "preferences": "Vegetarian options",
            "allergies": "Nuts",
            "customer_score": 85.5,
            "total_reservations": 12,
            "cancelled_reservations": 1,
            "no_show_count": 0,
            "is_active": true,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z"
        }
    ]
}
```

#### GET /api/customers/customers/{id}/
Obtiene un cliente específico

#### POST /api/customers/customers/
Crea un nuevo cliente

**Request Body:**
```json
{
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane.smith@email.com",
    "phone": "+1-555-4321",
    "birth_date": "1985-03-20",
    "preferences": "Gluten-free",
    "allergies": "Shellfish"
}
```

#### PUT /api/customers/customers/{id}/
Actualiza un cliente completo

#### PATCH /api/customers/customers/{id}/
Actualización parcial de un cliente

#### DELETE /api/customers/customers/{id}/
Elimina un cliente

### Reservations

#### GET /api/reservations/
Lista todas las reservas

**Query Parameters:**
- `status`: Filtrar por estado (`pending`, `confirmed`, `completed`, `cancelled`, `no_show`, `expired`)
- `restaurant`: Filtrar por ID de restaurante
- `customer`: Filtrar por ID de cliente
- `reservation_date`: Filtrar por fecha (YYYY-MM-DD)

**Response:**
```json
{
    "count": 100,
    "results": [
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "customer": 1,
            "restaurant": 1,
            "table": 1,
            "reservation_date": "2025-02-01",
            "reservation_time": "19:00:00",
            "party_size": 4,
            "status": "confirmed",
            "special_requests": "Window table if possible",
            "notes": "Anniversary dinner",
            "expires_at": null,
            "confirmed_at": "2025-01-15T14:30:00Z",
            "cancelled_at": null,
            "completed_at": null,
            "created_at": "2025-01-15T14:00:00Z",
            "updated_at": "2025-01-15T14:30:00Z"
        }
    ]
}
```

#### GET /api/reservations/{id}/
Obtiene una reserva específica

#### POST /api/reservations/
Crea una nueva reserva

**Request Body:**
```json
{
    "customer_id": 1,
    "restaurant_id": 1,
    "table_id": 1,
    "reservation_date": "2025-02-15",
    "reservation_time": "20:00:00",
    "party_size": 2,
    "special_requests": "Quiet table please"
}
```

**Response:**
```json
{
    "id": "456e7890-e89b-12d3-a456-426614174001",
    "customer": 1,
    "restaurant": 1,
    "table": 1,
    "reservation_date": "2025-02-15",
    "reservation_time": "20:00:00",
    "party_size": 2,
    "status": "pending",
    "special_requests": "Quiet table please",
    "notes": "",
    "expires_at": "2025-02-15T20:15:00Z",
    "created_at": "2025-01-15T15:00:00Z",
    "updated_at": "2025-01-15T15:00:00Z"
}
```

#### PUT /api/reservations/{id}/
Actualiza una reserva completa

#### PATCH /api/reservations/{id}/
Actualización parcial de una reserva

#### DELETE /api/reservations/{id}/
Cancela una reserva (cambia estado a 'cancelled')

### Notifications

#### GET /api/notifications/notifications/
Lista todas las notificaciones

**Response:**
```json
{
    "count": 25,
    "results": [
        {
            "id": "789e1234-e89b-12d3-a456-426614174002",
            "customer": 1,
            "type": "reservation_confirmation",
            "channel": "email",
            "subject": "Reservation Confirmed",
            "message": "Your reservation has been confirmed",
            "metadata": {"reservation_id": "123e4567-e89b-12d3-a456-426614174000"},
            "status": "sent",
            "sent_at": "2025-01-15T14:31:00Z",
            "failed_at": null,
            "retry_count": 0,
            "created_at": "2025-01-15T14:30:00Z",
            "updated_at": "2025-01-15T14:31:00Z"
        }
    ]
}
```

#### GET /api/notifications/notifications/{id}/
Obtiene una notificación específica

#### POST /api/notifications/notifications/
Crea una nueva notificación

### Notification Templates

#### GET /api/notifications/templates/
Lista todas las plantillas de notificaciones

#### GET /api/notifications/templates/{id}/
Obtiene una plantilla específica

#### POST /api/notifications/templates/
Crea una nueva plantilla

#### PUT/PATCH /api/notifications/templates/{id}/
Actualiza una plantilla

#### DELETE /api/notifications/templates/{id}/
Elimina una plantilla

### Notification Preferences

#### GET /api/notifications/preferences/
Lista las preferencias de notificaciones

#### GET /api/notifications/preferences/{id}/
Obtiene preferencias específicas

#### POST /api/notifications/preferences/
Crea preferencias de notificación

#### PUT/PATCH /api/notifications/preferences/{id}/
Actualiza preferencias

## Status Codes

- `200 OK` - Solicitud exitosa
- `201 Created` - Recurso creado exitosamente
- `204 No Content` - Eliminación exitosa
- `400 Bad Request` - Datos inválidos
- `404 Not Found` - Recurso no encontrado
- `409 Conflict` - Conflicto (ej. doble reserva)
- `500 Internal Server Error` - Error del servidor

## Error Response Format

```json
{
    "error": "Error message description",
    "details": {
        "field_name": ["Field specific error message"]
    }
}
```

## Reservation Status Flow

```
pending → confirmed → completed
   ↓         ↓
expired   cancelled/no_show
```

## Available Filter Options

### Cuisine Types
- `mexican`, `italian`, `japanese`, `american`, `french`, `chinese`, `indian`, `mediterranean`, `fusion`, `other`

### Price Ranges
- `low`, `mid`, `high`, `luxury`

### Table Locations
- `indoor`, `outdoor`, `bar`

### Table Shapes
- `round`, `square`, `rectangular`, `booth`

### Reservation Status
- `pending`, `confirmed`, `completed`, `cancelled`, `no_show`, `expired`

### Notification Types
- `reservation_confirmation`, `reservation_reminder`, `reservation_cancellation`, `promotional`

### Notification Channels
- `email`, `sms`, `push`

## Rate Limiting

The API implements rate limiting to prevent abuse:
- 100 requests per hour for general endpoints
- 10 reservation creation requests per minute
- Limits are per IP address

## Pagination

All list endpoints support pagination:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

Example: `/api/restaurants/restaurants/?page=2&page_size=10`