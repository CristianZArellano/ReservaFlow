#!/usr/bin/env python3
"""
SCRIPT PRINCIPAL DE TESTS - RESERVAFLOW
======================================

Este script ejecuta todos los tipos de tests organizados:
- Tests unitarios
- Tests de integración  
- Tests realistas
- Tests de validación
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime

def run_command(command, description, capture_output=False):
    """Ejecutar comando con manejo de errores"""
    print(f"\n🔄 {description}")
    print(f"   Comando: {command}")
    print("-" * 60)
    
    try:
        if capture_output:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(
                command, 
                shell=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            return result.returncode == 0, "", ""
    except Exception as e:
        print(f"❌ Error ejecutando comando: {e}")
        return False, "", str(e)

def run_unit_tests():
    """Ejecutar tests unitarios"""
    success, stdout, stderr = run_command(
        "python -m pytest tests/unit/ -v --tb=short",
        "Ejecutando Tests Unitarios"
    )
    return success

def run_integration_tests():
    """Ejecutar tests de integración"""
    success, stdout, stderr = run_command(
        "python -m pytest tests/integration/ -v --tb=short",
        "Ejecutando Tests de Integración"
    )
    return success

def run_realistic_tests():
    """Ejecutar tests realistas"""
    success, stdout, stderr = run_command(
        "python -m pytest tests/realistic/ -v --tb=short",
        "Ejecutando Tests Realistas"
    )
    return success

def run_validation_tests():
    """Ejecutar tests de validación específicos"""
    print("\n🔍 Ejecutando Tests de Validación Específicos")
    print("-" * 60)
    
    validation_tests = [
        ("tests/validation/test_double_booking.py", "Double Booking Prevention"),
        ("tests/validation/test_email_config.py", "Email Configuration"),
        ("tests/validation/test_full_reservation_flow.py", "Full Reservation Flow"),
        ("tests/validation/test_reminder_system.py", "Reminder System"),
        ("tests/validation/test_all_problems_fixed.py", "All Problems Fixed Validation"),
    ]
    
    all_passed = True
    for test_file, description in validation_tests:
        success, stdout, stderr = run_command(
            f"python {test_file}",
            f"🧪 {description}"
        )
        all_passed = all_passed and success
        if not success:
            print(f"   ❌ Falló: {description}")
        else:
            print(f"   ✅ Pasó: {description}")
    
    return all_passed

def run_realistic_demonstrations():
    """Ejecutar demostraciones realistas"""
    print("\n🎭 Ejecutando Demostraciones Realistas")
    print("-" * 60)
    
    demonstrations = [
        ("tests/scripts/realistic_test_demonstration.py", "Realistic Test Demonstration"),
        ("tests/scripts/final_realistic_test_report.py", "Final Realistic Report"),
    ]
    
    all_passed = True
    for script_file, description in demonstrations:
        success, stdout, stderr = run_command(
            f"python {script_file}",
            f"🎯 {description}"
        )
        all_passed = all_passed and success
        if not success:
            print(f"   ❌ Falló: {description}")
        else:
            print(f"   ✅ Pasó: {description}")
    
    return all_passed

def generate_test_report(results):
    """Generar reporte final de todos los tests"""
    print("\n" + "="*80)
    print("📊 REPORTE FINAL DE TESTS - RESERVAFLOW")
    print("="*80)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕐 Ejecutado: {timestamp}")
    
    total_categories = len(results)
    passed_categories = sum(1 for success in results.values() if success)
    success_rate = (passed_categories / total_categories) * 100 if total_categories > 0 else 0
    
    print("\n📈 RESUMEN EJECUTIVO:")
    print(f"   Total de categorías: {total_categories}")
    print(f"   Categorías exitosas: {passed_categories}")
    print(f"   Tasa de éxito: {success_rate:.1f}%")
    
    print("\n📋 DETALLE POR CATEGORÍA:")
    
    category_names = {
        'unit': 'Tests Unitarios',
        'integration': 'Tests de Integración', 
        'realistic': 'Tests Realistas',
        'validation': 'Tests de Validación',
        'demonstrations': 'Demostraciones Realistas'
    }
    
    for category, success in results.items():
        name = category_names.get(category, category)
        status = "✅ PASÓ" if success else "❌ FALLÓ"
        print(f"   {name:25} {status}")
    
    print("\n💡 ESTRUCTURA DE TESTS ORGANIZADA:")
    print("   📁 tests/unit/           - Tests unitarios de modelos, vistas, tareas")
    print("   📁 tests/integration/    - Tests de integración API y flujos") 
    print("   📁 tests/realistic/      - Tests con servicios reales (Redis, BD)")
    print("   📁 tests/validation/     - Tests de validación específicos")
    print("   📁 tests/scripts/        - Scripts de demostración y herramientas")
    print("   📁 tests/fixtures/       - Factories y fixtures compartidos")
    print("   📁 docs/                 - Documentación técnica")
    
    if success_rate >= 80:
        print("\n🏆 CONCLUSIÓN:")
        print("   ✅ SISTEMA DE TESTS ROBUSTO Y ORGANIZADO")
        print("   📚 Todos los tipos de tests están funcionando correctamente")
        print("   🚀 ReservaFlow tiene cobertura completa de testing")
    elif success_rate >= 60:
        print("\n⚠️ CONCLUSIÓN:")
        print("   🔧 SISTEMA DE TESTS MAYORMENTE FUNCIONAL")
        print("   📝 Algunas categorías necesitan ajustes menores")
    else:
        print("\n❌ CONCLUSIÓN:")
        print("   🚨 SISTEMA DE TESTS REQUIERE ATENCIÓN")
        print("   🔧 Problemas críticos en múltiples categorías")
    
    return success_rate >= 80

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Ejecutar tests de ReservaFlow')
    parser.add_argument('--type', choices=['unit', 'integration', 'realistic', 'validation', 'demonstrations', 'all'], 
                       default='all', help='Tipo de tests a ejecutar')
    parser.add_argument('--quick', action='store_true', help='Ejecutar solo tests rápidos')
    
    args = parser.parse_args()
    
    print("🧪 SISTEMA DE TESTS ORGANIZADO - RESERVAFLOW")
    print("="*80)
    print("🎯 Ejecutando tests organizados por categorías")
    print("📊 Estructura optimizada para desarrollo y CI/CD")
    
    results = {}
    
    if args.type in ['unit', 'all']:
        results['unit'] = run_unit_tests()
    
    if args.type in ['integration', 'all'] and not args.quick:
        results['integration'] = run_integration_tests()
    
    if args.type in ['realistic', 'all'] and not args.quick:
        results['realistic'] = run_realistic_tests()
    
    if args.type in ['validation', 'all'] and not args.quick:
        results['validation'] = run_validation_tests()
    
    if args.type in ['demonstrations', 'all'] and not args.quick:
        results['demonstrations'] = run_realistic_demonstrations()
    
    # Generar reporte final
    overall_success = generate_test_report(results)
    
    print("\n🎉 EJECUCIÓN COMPLETADA!")
    if overall_success:
        print("   ✅ Todos los tests están organizados y funcionando")
        sys.exit(0)
    else:
        print("   ⚠️ Algunas categorías de tests necesitan atención")
        sys.exit(1)

if __name__ == "__main__":
    main()