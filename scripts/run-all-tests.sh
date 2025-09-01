#!/bin/bash

# 🧪 ReservaFlow - Script para ejecutar todos los tests
# Este script ejecuta tests del backend y frontend con reportes

set -e  # Exit on any error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir headers
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Función para imprimir éxito
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Función para imprimir error
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Función para imprimir warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Función para imprimir info
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Variables
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/restaurant-reservations"
FRONTEND_DIR="$PROJECT_ROOT/FrontendReact"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORTS_DIR="$PROJECT_ROOT/test-reports/$TIMESTAMP"

# Crear directorio de reportes
mkdir -p "$REPORTS_DIR"

# Función para verificar prerrequisitos
check_prerequisites() {
    print_header "Verificando Prerrequisitos"
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker no está instalado"
        exit 1
    fi
    
    # Verificar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose no está instalado"
        exit 1
    fi
    
    # Verificar Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js no está instalado"
        exit 1
    fi
    
    # Verificar npm
    if ! command -v npm &> /dev/null; then
        print_error "npm no está instalado"
        exit 1
    fi
    
    print_success "Todos los prerrequisitos están disponibles"
}

# Función para verificar servicios del backend
check_backend_services() {
    print_header "Verificando Servicios del Backend"
    
    cd "$BACKEND_DIR"
    
    # Verificar si los contenedores están ejecutándose
    if ! docker-compose ps | grep -q "Up"; then
        print_warning "Servicios del backend no están ejecutándose"
        print_info "Iniciando servicios..."
        docker-compose up -d
        sleep 30  # Esperar a que los servicios estén listos
    fi
    
    # Verificar salud de los servicios
    if docker-compose exec -T web python manage.py check --deploy > /dev/null 2>&1; then
        print_success "Backend está funcionando correctamente"
    else
        print_error "Backend tiene problemas de configuración"
        return 1
    fi
}

# Función para ejecutar tests del backend
run_backend_tests() {
    print_header "Ejecutando Tests del Backend Django"
    
    cd "$BACKEND_DIR"
    
    local backend_report="$REPORTS_DIR/backend-test-report.xml"
    local coverage_report="$REPORTS_DIR/backend-coverage.xml"
    
    print_info "Ejecutando tests con pytest..."
    
    # Ejecutar tests con cobertura y reporte XML
    if docker-compose exec -T web uv run pytest \
        --junitxml="$backend_report" \
        --cov=. \
        --cov-report=xml:"$coverage_report" \
        --cov-report=html:"$REPORTS_DIR/backend-coverage-html" \
        --tb=short \
        -v > "$REPORTS_DIR/backend-tests.log" 2>&1; then
        
        print_success "Tests del backend completados exitosamente"
        
        # Mostrar resumen de cobertura
        if [ -f "$coverage_report" ]; then
            print_info "Reporte de cobertura generado en: $coverage_report"
        fi
        
        return 0
    else
        print_error "Tests del backend fallaron"
        print_info "Ver detalles en: $REPORTS_DIR/backend-tests.log"
        return 1
    fi
}

# Función para verificar frontend
check_frontend_dependencies() {
    print_header "Verificando Dependencias del Frontend"
    
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ]; then
        print_warning "Dependencias de Node.js no están instaladas"
        print_info "Instalando dependencias..."
        npm install
    fi
    
    print_success "Dependencias del frontend están listas"
}

# Función para ejecutar tests del frontend
run_frontend_tests() {
    print_header "Ejecutando Tests del Frontend React"
    
    cd "$FRONTEND_DIR"
    
    print_info "Ejecutando tests con Jest..."
    
    # Configurar variables de entorno para tests
    export CI=true
    export REACT_APP_API_URL="http://localhost:8000"
    
    # Ejecutar tests con cobertura
    if npm test -- \
        --coverage \
        --watchAll=false \
        --testResultsProcessor="jest-junit" \
        --coverageReporters=text-lcov \
        --coverageReporters=cobertura \
        --coverageReporters=html \
        --coverageDirectory="$REPORTS_DIR/frontend-coverage" \
        > "$REPORTS_DIR/frontend-tests.log" 2>&1; then
        
        print_success "Tests del frontend completados exitosamente"
        
        # Mover reporte de Jest si existe
        if [ -f "junit.xml" ]; then
            mv "junit.xml" "$REPORTS_DIR/frontend-test-report.xml"
        fi
        
        return 0
    else
        print_error "Tests del frontend fallaron"
        print_info "Ver detalles en: $REPORTS_DIR/frontend-tests.log"
        return 1
    fi
}

# Función para ejecutar linting
run_linting() {
    print_header "Ejecutando Análisis de Código"
    
    # Backend linting
    cd "$BACKEND_DIR"
    print_info "Ejecutando ruff en el backend..."
    
    if docker-compose exec -T web uv run ruff check . > "$REPORTS_DIR/backend-lint.log" 2>&1; then
        print_success "Linting del backend pasó"
    else
        print_warning "Linting del backend encontró problemas"
        print_info "Ver detalles en: $REPORTS_DIR/backend-lint.log"
    fi
    
    # Frontend linting (si está configurado)
    cd "$FRONTEND_DIR"
    if [ -f ".eslintrc.js" ] || [ -f ".eslintrc.json" ]; then
        print_info "Ejecutando ESLint en el frontend..."
        
        if npx eslint src/ --ext .js,.jsx > "$REPORTS_DIR/frontend-lint.log" 2>&1; then
            print_success "Linting del frontend pasó"
        else
            print_warning "Linting del frontend encontró problemas"
            print_info "Ver detalles en: $REPORTS_DIR/frontend-lint.log"
        fi
    fi
}

# Función para generar reporte final
generate_final_report() {
    print_header "Generando Reporte Final"
    
    local final_report="$REPORTS_DIR/final-report.html"
    
    cat > "$final_report" << EOF
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ReservaFlow - Reporte de Tests</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #ffa69e; color: white; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border-left: 4px solid #b8f2e6; }
        .success { color: #28a745; }
        .error { color: #dc3545; }
        .warning { color: #ffc107; }
        .info { color: #17a2b8; }
        .timestamp { font-size: 0.9em; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🍽️ ReservaFlow - Reporte de Tests</h1>
        <p class="timestamp">Generado el: $(date)</p>
    </div>
    
    <div class="section">
        <h2>📊 Resumen Ejecutivo</h2>
        <p>Tests ejecutados automáticamente para el sistema ReservaFlow.</p>
        <ul>
            <li><strong>Backend:</strong> Django REST Framework</li>
            <li><strong>Frontend:</strong> React + Material-UI</li>
            <li><strong>Infraestructura:</strong> Docker + PostgreSQL + Redis</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>🧪 Resultados de Tests</h2>
        <h3>Backend Django</h3>
        <p>Logs disponibles en: <code>backend-tests.log</code></p>
        
        <h3>Frontend React</h3>
        <p>Logs disponibles en: <code>frontend-tests.log</code></p>
    </div>
    
    <div class="section">
        <h2>📈 Cobertura de Código</h2>
        <h3>Backend</h3>
        <p>Reporte HTML: <a href="backend-coverage-html/index.html">Ver Cobertura Backend</a></p>
        
        <h3>Frontend</h3>
        <p>Reporte HTML: <a href="frontend-coverage/index.html">Ver Cobertura Frontend</a></p>
    </div>
    
    <div class="section">
        <h2>🔧 Análisis de Código</h2>
        <p>Logs de linting:</p>
        <ul>
            <li>Backend (ruff): <code>backend-lint.log</code></li>
            <li>Frontend (eslint): <code>frontend-lint.log</code></li>
        </ul>
    </div>
    
    <div class="section">
        <h2>📁 Archivos de Reporte</h2>
        <ul>
            <li><code>backend-test-report.xml</code> - Reporte JUnit del backend</li>
            <li><code>frontend-test-report.xml</code> - Reporte JUnit del frontend</li>
            <li><code>backend-coverage.xml</code> - Cobertura del backend (XML)</li>
            <li><code>backend-tests.log</code> - Log detallado del backend</li>
            <li><code>frontend-tests.log</code> - Log detallado del frontend</li>
        </ul>
    </div>
</body>
</html>
EOF
    
    print_success "Reporte final generado: $final_report"
}

# Función principal
main() {
    print_header "🧪 ReservaFlow - Ejecutor de Tests Completo"
    print_info "Iniciando ejecución de tests en: $TIMESTAMP"
    print_info "Reportes se guardarán en: $REPORTS_DIR"
    
    local backend_success=0
    local frontend_success=0
    
    # Ejecutar verificaciones y tests
    check_prerequisites
    check_backend_services
    check_frontend_dependencies
    
    # Ejecutar tests del backend
    if run_backend_tests; then
        backend_success=1
    fi
    
    # Ejecutar tests del frontend
    if run_frontend_tests; then
        frontend_success=1
    fi
    
    # Ejecutar linting
    run_linting
    
    # Generar reporte final
    generate_final_report
    
    # Resumen final
    print_header "📋 Resumen Final"
    
    if [ $backend_success -eq 1 ]; then
        print_success "Tests del Backend: EXITOSO"
    else
        print_error "Tests del Backend: FALLIDO"
    fi
    
    if [ $frontend_success -eq 1 ]; then
        print_success "Tests del Frontend: EXITOSO"
    else
        print_error "Tests del Frontend: FALLIDO"
    fi
    
    print_info "Reportes disponibles en: $REPORTS_DIR"
    print_info "Reporte HTML principal: $REPORTS_DIR/final-report.html"
    
    # Exit code basado en resultados
    if [ $backend_success -eq 1 ] && [ $frontend_success -eq 1 ]; then
        print_success "🎉 Todos los tests completados exitosamente!"
        exit 0
    else
        print_error "❌ Algunos tests fallaron. Revisar reportes para más detalles."
        exit 1
    fi
}

# Verificar si se llama directamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi