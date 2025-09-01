# 🧪 Backend Tests - ReservaFlow

Esta carpeta contiene todos los tests del backend Django organizados por categorías y funcionalidad.

## 📁 Estructura de Tests

```
tests/
├── 📂 unit/                    # Tests unitarios
│   ├── 📄 test_models.py       # Tests de modelos
│   ├── 📄 test_serializers.py  # Tests de serializers
│   ├── 📄 test_views.py        # Tests de vistas/APIs
│   └── 📄 test_tasks.py        # Tests de tareas Celery
│
├── 📂 integration/             # Tests de integración
│   ├── 📄 test_api_integration.py        # API end-to-end
│   └── 📄 test_reservation_flow.py       # Flujo completo de reservas
│
├── 📂 celery_tasks/            # Tests específicos de Celery
│   └── 📄 test_reservation_tasks.py      # Tests de tareas de reserva
│
├── 📂 monitoring/              # Tests de monitoreo
│   └── 📄 test_task_monitoring.py        # Tests de métricas de tareas
│
├── 📂 notifications/           # Tests de notificaciones
│   └── 📄 test_notification_tasks.py     # Tests de tareas de notificación
│
├── 📂 validation/              # Tests de validación
│   ├── 📄 test_double_booking.py         # Prevención de doble reserva
│   ├── 📄 test_email_config.py           # Configuración de email
│   ├── 📄 test_full_reservation_flow.py  # Flujo completo
│   └── 📄 test_reminder_system.py        # Sistema de recordatorios
│
├── 📂 realistic/               # Tests con escenarios reales
│   └── 📄 test_celery_tasks.py           # Tareas Celery realistas
│
├── 📂 system/                  # Tests del sistema
│   └── 📄 test_integration.py            # Integración del sistema
│
├── 📄 conftest.py              # Configuración pytest y fixtures
└── 📄 README.md                # Esta documentación
```

## 🎯 Tipos de Tests

### 📝 Tests Unitarios (`unit/`)
Tests que prueban componentes individuales de forma aislada:
- **Modelos**: Validaciones, métodos, propiedades
- **Serializers**: Validación de datos, transformaciones
- **Views**: Lógica de vistas, respuestas HTTP
- **Tasks**: Funciones de Celery individuales

### 🔗 Tests de Integración (`integration/`)
Tests que verifican la interacción entre múltiples componentes:
- **API Integration**: Pruebas end-to-end de endpoints
- **Reservation Flow**: Flujo completo de creación de reservas
- **Performance**: Tests de rendimiento y carga

### ⚡ Tests de Celery (`celery_tasks/`)
Tests específicos para tareas asíncronas:
- **Task Execution**: Ejecución correcta de tareas
- **Error Handling**: Manejo de errores y reintentos
- **Scheduling**: Programación de tareas

### 📊 Tests de Monitoreo (`monitoring/`)
Tests del sistema de monitoreo y métricas:
- **Task Monitoring**: Métricas de tareas
- **Health Checks**: Verificaciones de salud del sistema
- **Performance Metrics**: Métricas de rendimiento

### 📧 Tests de Notificaciones (`notifications/`)
Tests del sistema de notificaciones:
- **Email Notifications**: Envío de emails
- **SMS Notifications**: Envío de SMS
- **Push Notifications**: Notificaciones push
- **Template System**: Sistema de plantillas

### ✅ Tests de Validación (`validation/`)
Tests de validación de reglas de negocio:
- **Double Booking Prevention**: Prevención de reservas duplicadas
- **Email Configuration**: Configuración de email
- **Full Reservation Flow**: Flujo completo de reservas
- **Reminder System**: Sistema de recordatorios

### 🌍 Tests Realistas (`realistic/`)
Tests con escenarios del mundo real:
- **Real Data**: Datos similares a producción
- **Concurrent Operations**: Operaciones concurrentes
- **Load Testing**: Pruebas de carga

### 🔧 Tests de Sistema (`system/`)
Tests del sistema completo:
- **System Integration**: Integración entre todos los componentes
- **End-to-End**: Pruebas completas del flujo de usuario

## 🚀 Comandos de Testing

### Ejecutar todos los tests
```bash
docker-compose exec web uv run pytest -v
```

### Tests por categoría
```bash
# Tests unitarios
docker-compose exec web uv run pytest tests/unit/ -v

# Tests de integración
docker-compose exec web uv run pytest tests/integration/ -v

# Tests de Celery
docker-compose exec web uv run pytest tests/celery_tasks/ -v

# Tests de validación
docker-compose exec web uv run pytest tests/validation/ -v
```

### Tests específicos
```bash
# Test específico por archivo
docker-compose exec web uv run pytest tests/unit/test_models.py -v

# Test específico por función
docker-compose exec web uv run pytest tests/unit/test_models.py::TestReservationModel::test_create_reservation -v
```

### Tests con cobertura
```bash
# Cobertura completa
docker-compose exec web uv run pytest --cov=. --cov-report=html

# Cobertura por app
docker-compose exec web uv run pytest --cov=reservations --cov-report=html
```

### Tests en paralelo
```bash
# Ejecutar tests en paralelo (requiere pytest-xdist)
docker-compose exec web uv run pytest -n 4
```

## 📊 Métricas de Tests

### Cobertura de Código
- **Objetivo**: >90% de cobertura
- **Reporte HTML**: `htmlcov/index.html`
- **Áreas críticas**: Modelos, Views, Tasks

### Performance
- **Tests lentos**: Identificar tests que toman >5s
- **Optimización**: Usar fixtures y mocks apropiados
- **Paralelización**: Tests independientes para ejecución paralela

## 🔧 Configuración de Tests

### Fixtures (`conftest.py`)
Fixtures compartidos para todos los tests:
- **Database**: Configuración de base de datos de test
- **Users**: Usuarios de prueba
- **Restaurants**: Restaurantes de prueba
- **Reservations**: Reservas de prueba

### Configuración de pytest
```python
# pytest.ini o pyproject.toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
python_files = ["test_*.py", "*_test.py"]
addopts = [
    "--tb=short",
    "--strict-markers",
    "--disable-warnings",
]
testpaths = ["tests"]
```

## 🎯 Mejores Prácticas

### Nomenclatura
- **Archivos**: `test_<funcionalidad>.py`
- **Clases**: `Test<ComponentName>`
- **Métodos**: `test_<accion>_<resultado>`

### Estructura de Test
```python
def test_should_create_reservation_when_valid_data():
    # Arrange (Preparar)
    restaurant = RestaurantFactory()
    customer = CustomerFactory()
    
    # Act (Actuar)
    reservation = create_reservation(restaurant, customer)
    
    # Assert (Verificar)
    assert reservation.status == 'pending'
    assert reservation.customer == customer
```

### Mocking
- **APIs externas**: Mock servicios externos
- **Tiempo**: Mock datetime para tests determinísticos
- **Celery**: Mock tareas para tests unitarios

### Datos de Test
- **Factories**: Usar factory_boy para crear datos
- **Fixtures**: Para datos complejos reutilizables
- **Isolation**: Cada test debe ser independiente

## 🐛 Debugging Tests

### Tests fallidos
```bash
# Ver traceback completo
docker-compose exec web uv run pytest -v --tb=long

# Parar en el primer fallo
docker-compose exec web uv run pytest -x

# Ejecutar solo tests fallidos
docker-compose exec web uv run pytest --lf
```

### Debugging interactivo
```bash
# Con pdb
docker-compose exec web uv run pytest --pdb

# Con ipdb (si está instalado)
import ipdb; ipdb.set_trace()
```

## 📈 Monitoreo de Tests

### CI/CD Integration
- **GitHub Actions**: Ejecutar tests en cada PR
- **Coverage Reports**: Reportes de cobertura automáticos
- **Quality Gates**: No permitir merge si tests fallan

### Métricas
- **Test Duration**: Tiempo de ejecución de tests
- **Flaky Tests**: Tests que fallan esporádicamente
- **Coverage Trends**: Tendencia de cobertura de código

---

**Objetivo**: Mantener una suite de tests robusta y confiable que garantice la calidad del código y facilite el desarrollo continuo.