#!/bin/bash

# 🧪 Script específico para tests del backend Django

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Variables
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/restaurant-reservations"

# Función para mostrar ayuda
show_help() {
    cat << EOF
🧪 ReservaFlow - Script de Tests del Backend

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help              Mostrar esta ayuda
    -v, --verbose           Modo verbose
    -c, --coverage          Ejecutar con cobertura
    -f, --fast              Tests rápidos (sin integración)
    -u, --unit              Solo tests unitarios
    -i, --integration       Solo tests de integración
    -l, --lint              Solo linting
    --no-docker             Ejecutar sin Docker (requiere entorno local)
    --watch                 Modo watch (solo sin Docker)

EXAMPLES:
    $0                      # Ejecutar todos los tests
    $0 -c                   # Tests con cobertura
    $0 -u -v               # Tests unitarios en modo verbose
    $0 -l                   # Solo linting
    $0 --watch              # Modo watch (desarrollo)

CATEGORÍAS DE TESTS:
    - unit/                 Tests unitarios
    - integration/          Tests de integración
    - celery_tasks/         Tests de Celery
    - validation/           Tests de validación
    - realistic/            Tests con escenarios reales
EOF
}

# Parsear argumentos
VERBOSE=false
COVERAGE=false
FAST=false
UNIT_ONLY=false
INTEGRATION_ONLY=false
LINT_ONLY=false
NO_DOCKER=false
WATCH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -f|--fast)
            FAST=true
            shift
            ;;
        -u|--unit)
            UNIT_ONLY=true
            shift
            ;;
        -i|--integration)
            INTEGRATION_ONLY=true
            shift
            ;;
        -l|--lint)
            LINT_ONLY=true
            shift
            ;;
        --no-docker)
            NO_DOCKER=true
            shift
            ;;
        --watch)
            WATCH=true
            NO_DOCKER=true
            shift
            ;;
        *)
            echo "Opción desconocida: $1"
            show_help
            exit 1
            ;;
    esac
done

# Función para verificar servicios Docker
check_docker_services() {
    cd "$BACKEND_DIR"
    
    if ! docker-compose ps | grep -q "Up"; then
        print_info "Iniciando servicios Docker..."
        docker-compose up -d
        sleep 20
    fi
    
    # Esperar a que la base de datos esté lista
    print_info "Esperando a que los servicios estén listos..."
    docker-compose exec -T web python manage.py check --deploy
    print_success "Servicios Docker están funcionando"
}

# Función para ejecutar linting
run_linting() {
    print_header "Ejecutando Análisis de Código (ruff)"
    
    cd "$BACKEND_DIR"
    
    local lint_cmd
    if [ "$NO_DOCKER" = true ]; then
        lint_cmd="uv run ruff check ."
    else
        lint_cmd="docker-compose exec -T web uv run ruff check ."
    fi
    
    if $lint_cmd; then
        print_success "Linting completado sin errores"
    else
        print_error "Se encontraron problemas en el código"
        return 1
    fi
}

# Función para ejecutar tests
run_tests() {
    print_header "Ejecutando Tests del Backend"
    
    cd "$BACKEND_DIR"
    
    # Construir comando de pytest
    local pytest_args=()
    
    # Verbosity
    if [ "$VERBOSE" = true ]; then
        pytest_args+=("-v")
    else
        pytest_args+=("-q")
    fi
    
    # Cobertura
    if [ "$COVERAGE" = true ]; then
        pytest_args+=("--cov=." "--cov-report=term-missing" "--cov-report=html")
    fi
    
    # Categorías de tests
    if [ "$UNIT_ONLY" = true ]; then
        pytest_args+=("tests/unit/")
    elif [ "$INTEGRATION_ONLY" = true ]; then
        pytest_args+=("tests/integration/")
    elif [ "$FAST" = true ]; then
        pytest_args+=("tests/unit/" "tests/validation/")
    fi
    
    # Modo watch
    if [ "$WATCH" = true ]; then
        pytest_args+=("-f")  # fail fast
        pytest_args+=("--looponfail")  # rerun on file changes
    fi
    
    # Ejecutar comando
    local test_cmd
    if [ "$NO_DOCKER" = true ]; then
        test_cmd="uv run pytest ${pytest_args[*]}"
    else
        test_cmd="docker-compose exec -T web uv run pytest ${pytest_args[*]}"
    fi
    
    print_info "Ejecutando: $test_cmd"
    
    if $test_cmd; then
        print_success "Tests completados exitosamente"
        return 0
    else
        print_error "Algunos tests fallaron"
        return 1
    fi
}

# Función para mostrar estadísticas
show_stats() {
    print_header "Estadísticas de Tests"
    
    cd "$BACKEND_DIR"
    
    # Contar archivos de test
    local test_files=$(find tests/ -name "test_*.py" | wc -l)
    print_info "Archivos de test: $test_files"
    
    # Mostrar estructura de directorios
    print_info "Estructura de tests:"
    tree tests/ 2>/dev/null || ls -la tests/
    
    # Si hay cobertura, mostrar resumen
    if [ -f "htmlcov/index.html" ]; then
        print_info "Reporte de cobertura disponible en: htmlcov/index.html"
    fi
}

# Función para limpiar archivos temporales
cleanup() {
    print_header "Limpiando Archivos Temporales"
    
    cd "$BACKEND_DIR"
    
    # Limpiar archivos de cobertura
    rm -rf htmlcov/ .coverage coverage.xml
    
    # Limpiar cache de pytest
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    # Limpiar archivos de test temporales
    rm -rf .pytest_cache/
    
    print_success "Limpieza completada"
}

# Función principal
main() {
    print_header "🧪 ReservaFlow - Tests del Backend Django"
    
    # Si solo se quiere linting
    if [ "$LINT_ONLY" = true ]; then
        if [ "$NO_DOCKER" = false ]; then
            check_docker_services
        fi
        run_linting
        exit $?
    fi
    
    # Configurar entorno
    if [ "$NO_DOCKER" = false ]; then
        check_docker_services
    else
        cd "$BACKEND_DIR"
        if [ ! -d ".venv" ]; then
            print_info "Configurando entorno virtual..."
            uv sync
        fi
        source .venv/bin/activate
    fi
    
    # Ejecutar linting si no es modo rápido
    if [ "$FAST" = false ] && [ "$WATCH" = false ]; then
        run_linting
    fi
    
    # Ejecutar tests
    local test_success=0
    if run_tests; then
        test_success=1
    fi
    
    # Mostrar estadísticas si no es modo watch
    if [ "$WATCH" = false ]; then
        show_stats
    fi
    
    # Resultado final
    if [ $test_success -eq 1 ]; then
        print_success "🎉 Todos los tests del backend completados exitosamente!"
        exit 0
    else
        print_error "❌ Algunos tests fallaron"
        exit 1
    fi
}

# Trap para cleanup en caso de interrupción
trap cleanup EXIT

# Ejecutar si se llama directamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi