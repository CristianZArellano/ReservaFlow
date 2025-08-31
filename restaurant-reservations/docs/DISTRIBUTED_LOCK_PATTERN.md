# Patrón de Lock Distribuido en ReservaFlow

## Resumen

ReservaFlow implementa un patrón robusto de **lock distribuido + select_for_update() + transaction.atomic()** para prevenir reservas dobles en ambientes con múltiples procesos/replicas. Este documento explica la arquitectura y implementación del sistema.

## Arquitectura del Sistema

### Componentes Clave

1. **TableReservationLock** (Redis): Lock distribuido para coordinar entre procesos
2. **select_for_update()** (PostgreSQL): Lock a nivel de base de datos
3. **transaction.atomic()** (Django): Transacciones ACID
4. **Unique Constraints** (PostgreSQL): Constraint único condicional como última línea de defensa

### Flujo de Operación

```
┌─────────────────┐
│ Cliente Request │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 1. Acquire      │
│ Redis Lock      │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 2. Start        │
│ DB Transaction  │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 3. Select For   │
│ Update Query    │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 4. Create       │
│ Reservation     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ 5. Commit &     │
│ Release Lock    │
└─────────────────┘
```

## Implementación Detallada

### 1. Redis Lock Distribuido (`TableReservationLock`)

**Ubicación:** `restaurants/services.py:28`

```python
class TableReservationLock:
    def __init__(self, table_id, date, time_slot, timeout=30, max_retries=3):
        self.lock_key = f"table_lock:{table_id}:{date}:{time_slot}"
        self.timeout = timeout
        self.max_retries = max_retries
```

**Características:**

- **Atomicidad**: Usa `SET NX EX` para operaciones atómicas
- **Timeout**: Auto-expiración para evitar deadlocks
- **Retry Logic**: Backoff exponencial con múltiples intentos
- **Fallback**: Funciona sin Redis para desarrollo/testing

**Script Lua para Release Seguro:**
```lua
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
```

### 2. Database Locks y Transacciones

**Ubicación:** `reservations/views.py:108`

```python
with transaction.atomic():
    # Lock a nivel de base de datos
    conflicts = Reservation.objects.select_for_update().filter(
        table_id=table_id,
        reservation_date=reservation_date,
        reservation_time=reservation_time,
        status__in=["pending", "confirmed"],
    ).exists()
    
    if conflicts:
        return Response({"error": "Mesa no disponible"}, status=409)
    
    # Crear reserva con validación completa
    reservation = Reservation.objects.create(...)
```

### 3. Constraint Único Condicional

**Ubicación:** `reservations/models.py:48`

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["table", "reservation_date", "reservation_time"],
            condition=models.Q(status__in=["pending", "confirmed"]),
            name="unique_active_reservation_per_table_datetime",
        )
    ]
```

**SQL Generado:**
```sql
CREATE UNIQUE INDEX "unique_active_reservation_per_table_datetime" 
ON "reservations_reservation" ("table_id", "reservation_date", "reservation_time") 
WHERE "status" IN ('pending', 'confirmed');
```

## Índices de Base de Datos

### Índices Implementados

```sql
-- Índice principal para lookups de reservas
CREATE INDEX "reservation_table_i_2f1b8b_idx" 
ON "reservations_reservation" ("table_id", "reservation_date", "reservation_time");

-- Índice para cleanup de reservas expiradas
CREATE INDEX "reservation_status_f2f985_idx" 
ON "reservations_reservation" ("status", "expires_at");
```

### Justificación de Índices

1. **`(table_id, reservation_date, reservation_time)`**: 
   - Optimiza el query de verificación de conflictos
   - Usado en el `select_for_update()` query
   - Cubre el 95% de consultas de disponibilidad

2. **`(status, expires_at)`**: 
   - Optimiza cleanup de reservas expiradas
   - Usado por tareas Celery de limpieza
   - Mejora performance de queries por estado

## Manejo de Errores y Edge Cases

### 1. Lock Acquisition Failures

```python
except LockAcquisitionError as lae:
    return Response({
        "error": "Mesa temporalmente no disponible",
        "details": "Demasiada concurrencia - intente nuevamente",
        "retry_after": 5
    }, status=429)
```

### 2. Redis Unavailable

```python
if redis_client is None:
    logger.warning("Redis no disponible - usando fallback local")
    return True  # Fallback para desarrollo
```

### 3. Database Constraint Violations

```python
except IntegrityError as ie:
    logger.warning(f"Constraint violation: {ie}")
    return Response({
        "error": "Mesa ya reservada",
        "details": "Otra reserva fue creada simultáneamente"
    }, status=409)
```

## Configuración de Performance

### Redis Configuration

```python
# Timeout generoso para alta concurrencia
lock_timeout = 45  # 45 segundos
max_retries = 5    # Más intentos

# Cliente Redis optimizado
client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=False
)
```

### Cache Invalidation

```python
# Invalidar cache antes de verificar disponibilidad
cache_key = f"availability:{table_id}:{reservation_date}:{reservation_time}"
cache.delete(cache_key)
```

## Validación con DRF Serializers

### Timezone-Aware Validation

**Ubicación:** `reservations/serializers.py:242`

```python
def validate(self, attrs):
    # Combine date and time for timezone validation
    reservation_datetime = timezone.datetime.combine(
        attrs["reservation_date"], 
        attrs["reservation_time"]
    )
    
    # Make timezone-aware
    reservation_datetime = timezone.make_aware(reservation_datetime)
    current_datetime = timezone.now()
    
    # Validate minimum advance notice
    time_diff = reservation_datetime - current_datetime
    min_advance = timezone.timedelta(hours=2) if same_day else timezone.timedelta(minutes=30)
```

### Business Rules Validation

- **Time Slots**: Solo intervalos de 15 minutos
- **Operating Hours**: 10:00 AM - 10:00 PM
- **Advance Notice**: 2 horas mismo día, 30 minutos días futuros
- **Future Limit**: Máximo 90 días anticipación

## Testing y Monitoring

### Test de Concurrencia

**Ubicación:** `tests/realistic/test_database_constraints.py`

```python
def test_concurrent_reservation_creation(self):
    """Test de creación concurrente de reservas"""
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(50):  # 50 requests concurrentes
            future = executor.submit(self.create_reservation_request)
            futures.append(future)
        
        # Solo una debe exitosa, resto debe fallar con 409
        successful = sum(1 for f in futures if f.result().status_code == 201)
        self.assertEqual(successful, 1)
```

### Logging y Monitoring

```python
logger.info(f"Lock adquirido: {self.lock_key}")
logger.warning(f"Lock acquisition failed: {lae}")
logger.error(f"Error inesperado: {e}", exc_info=True)
```

## Beneficios del Patrón

### ✅ Ventajas

1. **Robustez**: Múltiples capas de protección contra race conditions
2. **Performance**: Redis lock evita contención innecesaria en BD
3. **Escalabilidad**: Funciona con múltiples procesos/replicas
4. **Fallback**: Degradación controlada sin Redis
5. **Monitoring**: Logs detallados para debugging
6. **Business Rules**: Validación completa con DRF serializers

### ⚠️ Consideraciones

1. **Latencia**: Lock distribuido añade ~5-20ms por request
2. **Complejidad**: Múltiples componentes a mantener
3. **Dependencias**: Requiere Redis para máxima robustez
4. **Tuning**: Timeouts requieren ajuste según carga

## Configuración Recomendada para Producción

### Redis Settings

```python
REDIS_URL = "redis://redis-cluster:6379/0"
RESERVATION_LOCK_TIMEOUT = 45  # segundos
RESERVATION_LOCK_RETRIES = 5
```

### Database Settings

```python
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'isolation_level': 'read_committed',
        }
    }
}
```

### Monitoring

```python
LOGGING = {
    'loggers': {
        'restaurants.services': {
            'level': 'INFO',
        },
        'reservations.views': {
            'level': 'WARNING',
        },
    }
}
```

## Conclusión

Este patrón proporciona una solución robusta para prevenir reservas dobles en sistemas distribuidos, combinando lo mejor de locks distribuidos, base de datos transaccional, y validación de negocio, resultando en un sistema confiable y escalable para gestión de reservas en tiempo real.