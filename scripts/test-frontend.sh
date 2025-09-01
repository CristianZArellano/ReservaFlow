#!/bin/bash

# 🧪 Script específico para tests del frontend React

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

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Variables
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/FrontendReact"

# Función para mostrar ayuda
show_help() {
    cat << EOF
🧪 ReservaFlow - Script de Tests del Frontend

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help              Mostrar esta ayuda
    -w, --watch             Modo watch (desarrollo)
    -c, --coverage          Ejecutar con cobertura
    -u, --update            Actualizar snapshots
    -v, --verbose           Modo verbose
    -s, --silent            Modo silencioso
    --components            Solo tests de componentes
    --pages                 Solo tests de páginas
    --services              Solo tests de servicios
    --integration           Solo tests de integración
    --lint                  Solo linting (ESLint)
    --fix                   Ejecutar ESLint con --fix
    --ci                    Modo CI (sin interacción)

EXAMPLES:
    $0                      # Ejecutar todos los tests
    $0 -w                   # Modo watch para desarrollo
    $0 -c                   # Tests con cobertura
    $0 --components -v      # Solo tests de componentes (verbose)
    $0 --lint --fix         # Linting con corrección automática
    $0 --ci                 # Modo CI

ESTRUCTURA DE TESTS:
    src/
    ├── __tests__/          Tests principales
    ├── components/__tests__/ Tests de componentes
    ├── pages/__tests__/    Tests de páginas
    ├── services/__tests__/ Tests de servicios
    └── integration/        Tests de integración
EOF
}

# Parsear argumentos
WATCH=false
COVERAGE=false
UPDATE_SNAPSHOTS=false
VERBOSE=false
SILENT=false
COMPONENTS_ONLY=false
PAGES_ONLY=false
SERVICES_ONLY=false
INTEGRATION_ONLY=false
LINT_ONLY=false
FIX_LINT=false
CI_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -w|--watch)
            WATCH=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -u|--update)
            UPDATE_SNAPSHOTS=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -s|--silent)
            SILENT=true
            shift
            ;;
        --components)
            COMPONENTS_ONLY=true
            shift
            ;;
        --pages)
            PAGES_ONLY=true
            shift
            ;;
        --services)
            SERVICES_ONLY=true
            shift
            ;;
        --integration)
            INTEGRATION_ONLY=true
            shift
            ;;
        --lint)
            LINT_ONLY=true
            shift
            ;;
        --fix)
            FIX_LINT=true
            shift
            ;;
        --ci)
            CI_MODE=true
            shift
            ;;
        *)
            echo "Opción desconocida: $1"
            show_help
            exit 1
            ;;
    esac
done

# Función para verificar dependencias
check_dependencies() {
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ] || [ ! -f "package-lock.json" ]; then
        print_info "Instalando dependencias de Node.js..."
        npm install
        print_success "Dependencias instaladas"
    fi
    
    # Verificar si las dependencias están actualizadas
    if [ "package.json" -nt "node_modules/.package-lock.json" ] 2>/dev/null; then
        print_warning "package.json es más reciente que node_modules"
        print_info "Ejecutando npm install..."
        npm install
    fi
}

# Función para verificar configuración de ESLint
check_eslint_config() {
    cd "$FRONTEND_DIR"
    
    local eslint_config=""
    if [ -f ".eslintrc.js" ]; then
        eslint_config=".eslintrc.js"
    elif [ -f ".eslintrc.json" ]; then
        eslint_config=".eslintrc.json"
    elif [ -f "eslint.config.js" ]; then
        eslint_config="eslint.config.js"
    fi
    
    if [ -n "$eslint_config" ]; then
        print_success "Configuración de ESLint encontrada: $eslint_config"
        return 0
    else
        print_warning "No se encontró configuración de ESLint"
        return 1
    fi
}

# Función para crear configuración básica de ESLint si no existe
create_eslint_config() {
    cd "$FRONTEND_DIR"
    
    if ! check_eslint_config; then
        print_info "Creando configuración básica de ESLint..."
        
        cat > .eslintrc.json << EOF
{
  "extends": [
    "react-app",
    "react-app/jest"
  ],
  "rules": {
    "no-unused-vars": "warn",
    "no-console": "warn"
  },
  "env": {
    "browser": true,
    "jest": true,
    "es6": true
  }
}
EOF
        print_success "Configuración de ESLint creada"
    fi
}

# Función para ejecutar linting
run_linting() {
    print_header "Ejecutando Análisis de Código (ESLint)"
    
    cd "$FRONTEND_DIR"
    
    create_eslint_config
    
    local eslint_args=("src/")
    eslint_args+=("--ext" ".js,.jsx,.ts,.tsx")
    
    if [ "$FIX_LINT" = true ]; then
        eslint_args+=("--fix")
    fi
    
    if [ "$VERBOSE" = true ]; then
        eslint_args+=("--format" "detailed")
    fi
    
    local eslint_cmd="npx eslint ${eslint_args[*]}"
    
    print_info "Ejecutando: $eslint_cmd"
    
    if $eslint_cmd; then
        print_success "Linting completado sin errores"
        return 0
    else
        if [ "$FIX_LINT" = true ]; then
            print_warning "Linting completado con correcciones automáticas"
            return 0
        else
            print_error "Se encontraron problemas en el código"
            print_info "Ejecuta con --fix para corrección automática"
            return 1
        fi
    fi
}

# Función para ejecutar tests
run_tests() {
    print_header "Ejecutando Tests del Frontend React"
    
    cd "$FRONTEND_DIR"
    
    # Configurar variables de entorno
    export CI="$CI_MODE"
    export REACT_APP_API_URL="http://localhost:8000"
    
    # Construir argumentos para npm test
    local test_args=()
    
    # Configuración base
    if [ "$WATCH" = true ]; then
        test_args+=("--watchAll")
    else
        test_args+=("--watchAll=false")
    fi
    
    if [ "$CI_MODE" = true ]; then
        test_args+=("--ci")
    fi
    
    # Cobertura
    if [ "$COVERAGE" = true ]; then
        test_args+=("--coverage")
        if [ "$CI_MODE" = false ]; then
            test_args+=("--coverageReporters=text")
            test_args+=("--coverageReporters=html")
        fi
    fi
    
    # Snapshots
    if [ "$UPDATE_SNAPSHOTS" = true ]; then
        test_args+=("--updateSnapshot")
    fi
    
    # Verbosity
    if [ "$VERBOSE" = true ]; then
        test_args+=("--verbose")
    elif [ "$SILENT" = true ]; then
        test_args+=("--silent")
    fi
    
    # Filtros por categoría
    if [ "$COMPONENTS_ONLY" = true ]; then
        test_args+=("--testPathPattern=components")
    elif [ "$PAGES_ONLY" = true ]; then
        test_args+=("--testPathPattern=pages")
    elif [ "$SERVICES_ONLY" = true ]; then
        test_args+=("--testPathPattern=services")
    elif [ "$INTEGRATION_ONLY" = true ]; then
        test_args+=("--testPathPattern=integration")
    fi
    
    # Ejecutar tests
    local test_cmd="npm test -- ${test_args[*]}"
    
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
    
    cd "$FRONTEND_DIR"
    
    # Contar archivos de test
    local test_files=$(find src/ -name "*.test.js" -o -name "*.test.jsx" -o -name "*.spec.js" -o -name "*.spec.jsx" | wc -l)
    print_info "Archivos de test: $test_files"
    
    # Mostrar estructura de tests
    print_info "Estructura de tests:"
    if command -v tree &> /dev/null; then
        tree src/ -I "node_modules" -P "*.test.js|*.spec.js|__tests__|*.test.jsx|*.spec.jsx" 2>/dev/null || true
    else
        find src/ -name "*test*" -type f -o -name "*spec*" -type f | sort
    fi
    
    # Información de cobertura
    if [ -d "coverage" ]; then
        print_info "Reporte de cobertura disponible en: coverage/lcov-report/index.html"
        
        # Mostrar resumen de cobertura si existe
        if [ -f "coverage/coverage-summary.json" ]; then
            print_info "Resumen de cobertura:"
            node -e "
                const fs = require('fs');
                try {
                    const coverage = JSON.parse(fs.readFileSync('coverage/coverage-summary.json'));
                    const total = coverage.total;
                    console.log('  Statements:', total.statements.pct + '%');
                    console.log('  Branches:', total.branches.pct + '%');
                    console.log('  Functions:', total.functions.pct + '%');
                    console.log('  Lines:', total.lines.pct + '%');
                } catch (e) {
                    console.log('  No se pudo leer el resumen de cobertura');
                }
            "
        fi
    fi
    
    # Información del bundle
    if [ -f "build/static/js/main.*.js" ]; then
        local bundle_size=$(du -h build/static/js/main.*.js | cut -f1)
        print_info "Tamaño del bundle principal: $bundle_size"
    fi
}

# Función para verificar la calidad del código
run_quality_checks() {
    print_header "Verificaciones de Calidad"
    
    cd "$FRONTEND_DIR"
    
    local quality_issues=0
    
    # Verificar archivos grandes
    print_info "Verificando tamaño de archivos..."
    local large_files=$(find src/ -name "*.js" -o -name "*.jsx" | xargs wc -l | awk '$1 > 300 {print $2 " (" $1 " líneas)"}')
    if [ -n "$large_files" ]; then
        print_warning "Archivos grandes encontrados:"
        echo "$large_files"
        ((quality_issues++))
    fi
    
    # Verificar TODO/FIXME
    print_info "Verificando TODOs y FIXMEs..."
    local todos=$(grep -r "TODO\|FIXME" src/ --include="*.js" --include="*.jsx" 2>/dev/null || true)
    if [ -n "$todos" ]; then
        print_warning "TODOs/FIXMEs encontrados:"
        echo "$todos" | head -10
        ((quality_issues++))
    fi
    
    # Verificar console.log
    print_info "Verificando console.log..."
    local console_logs=$(grep -r "console\." src/ --include="*.js" --include="*.jsx" 2>/dev/null || true)
    if [ -n "$console_logs" ]; then
        print_warning "console.log encontrados:"
        echo "$console_logs" | head -5
        ((quality_issues++))
    fi
    
    if [ $quality_issues -eq 0 ]; then
        print_success "No se encontraron problemas de calidad"
    else
        print_warning "Se encontraron $quality_issues problemas de calidad"
    fi
    
    return $quality_issues
}

# Función para limpiar archivos temporales
cleanup() {
    print_header "Limpiando Archivos Temporales"
    
    cd "$FRONTEND_DIR"
    
    # Limpiar cobertura
    rm -rf coverage/
    
    # Limpiar build
    rm -rf build/
    
    # Limpiar cache de Jest
    npm test -- --clearCache > /dev/null 2>&1 || true
    
    print_success "Limpieza completada"
}

# Función principal
main() {
    print_header "🧪 ReservaFlow - Tests del Frontend React"
    
    # Verificar dependencias
    check_dependencies
    
    # Si solo se quiere linting
    if [ "$LINT_ONLY" = true ]; then
        run_linting
        exit $?
    fi
    
    # Ejecutar linting si no es modo watch
    local lint_success=true
    if [ "$WATCH" = false ]; then
        if ! run_linting; then
            lint_success=false
        fi
    fi
    
    # Ejecutar tests
    local test_success=false
    if run_tests; then
        test_success=true
    fi
    
    # Mostrar estadísticas si no es modo watch
    if [ "$WATCH" = false ]; then
        show_stats
        
        # Ejecutar verificaciones de calidad
        if [ "$CI_MODE" = false ]; then
            run_quality_checks
        fi
    fi
    
    # Resultado final
    if [ "$test_success" = true ] && [ "$lint_success" = true ]; then
        print_success "🎉 Todos los tests del frontend completados exitosamente!"
        exit 0
    else
        if [ "$test_success" = false ]; then
            print_error "❌ Algunos tests fallaron"
        fi
        if [ "$lint_success" = false ]; then
            print_error "❌ Problemas de linting encontrados"
        fi
        exit 1
    fi
}

# Trap para cleanup en caso de interrupción (solo si no es modo watch)
if [ "$WATCH" = false ]; then
    trap cleanup EXIT
fi

# Ejecutar si se llama directamente
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi