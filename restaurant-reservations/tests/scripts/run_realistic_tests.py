#!/usr/bin/env python3
"""
Script para ejecutar tests realistas con servicios Docker reales
"""

import sys
import time
import subprocess
import argparse


def run_command(command, check=True, cwd=None):
    """Ejecutar comando y mostrar output"""
    print(f"🚀 Ejecutando: {command}")
    try:
        result = subprocess.run(
            command, shell=True, check=check, cwd=cwd, capture_output=False, text=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        return False


def wait_for_services():
    """Esperar a que los servicios estén listos"""
    print("⏳ Esperando que los servicios estén listos...")

    services_to_check = [
        (
            "PostgreSQL",
            "docker compose -f docker-compose.test.yml exec -T test-db pg_isready -U test_user -d reservaflow_test",
        ),
        (
            "Redis",
            "docker compose -f docker-compose.test.yml exec -T test-redis redis-cli ping",
        ),
    ]

    max_retries = 30
    for service_name, check_cmd in services_to_check:
        print(f"🔍 Verificando {service_name}...")
        for i in range(max_retries):
            if run_command(check_cmd, check=False):
                print(f"✅ {service_name} listo")
                break
            print(
                f"⏳ {service_name} no está listo, reintentando ({i + 1}/{max_retries})..."
            )
            time.sleep(2)
        else:
            print(
                f"❌ {service_name} no se pudo conectar después de {max_retries} intentos"
            )
            return False

    # Esperar un poco más para Celery
    print("⏳ Esperando workers de Celery...")
    time.sleep(10)

    return True


def setup_test_environment():
    """Configurar entorno de test"""
    print("🏗️ Configurando entorno de tests realistas...")

    # Levantar servicios
    print("🐳 Levantando servicios Docker...")
    if not run_command("docker compose -f docker-compose.test.yml up -d"):
        return False

    # Esperar servicios
    if not wait_for_services():
        return False

    # Ejecutar migraciones
    print("📊 Ejecutando migraciones...")
    if not run_command(
        "docker compose -f docker-compose.test.yml exec -T test-web python manage.py migrate --settings=config.settings_test"
    ):
        return False

    return True


def run_tests(test_path=None, verbose=False, failfast=False):
    """Ejecutar tests realistas"""
    print("🧪 Ejecutando tests realistas con servicios Docker...")

    # Construir comando pytest
    pytest_cmd = [
        "docker",
        "compose",
        "-f",
        "docker-compose.test.yml",
        "exec",
        "-T",
        "test-web",
        "python",
        "-m",
        "pytest",
    ]

    # Opciones de pytest
    if verbose:
        pytest_cmd.extend(["-v", "-s"])
    else:
        pytest_cmd.append("-v")

    if failfast:
        pytest_cmd.append("-x")

    # Configuraciones especiales para tests realistas
    pytest_cmd.extend(
        [
            "--tb=short",
            "--disable-warnings",
            "--durations=10",  # Mostrar los 10 tests más lentos
            "--maxfail=5",  # Parar después de 5 fallos
            "--timeout=300",  # Timeout de 5 minutos por test
        ]
    )

    # Path específico de tests
    if test_path:
        pytest_cmd.append(test_path)

    # Variables de entorno para el test
    env_vars = [
        "-e",
        "DJANGO_SETTINGS_MODULE=config.settings_test",
        "-e",
        "PYTHONPATH=/app",
        "-e",
        "CELERY_TASK_ALWAYS_EAGER=False",  # CRÍTICO: Tests realistas
    ]

    # Insertar variables de entorno antes del comando pytest
    final_cmd = pytest_cmd[:5] + env_vars + pytest_cmd[5:]

    print(f"🚀 Comando final: {' '.join(final_cmd)}")

    return run_command(" ".join(final_cmd), check=False)


def run_specific_test_categories():
    """Ejecutar categorías específicas de tests realistas"""
    categories = {
        "locks": "tests/ -k 'lock or Lock or concurrent'",
        "celery": "tests/ -k 'task or Task or celery or Celery'",
        "redis": "tests/ -k 'redis or Redis or cache'",
        "integration": "tests/integration/",
        "models": "tests/unit/test_models.py",
        "views": "tests/unit/test_views.py",
        "security": "tests/ -k 'security or injection'",
        "performance": "tests/ -k 'performance'",
    }

    results = {}

    for category, test_path in categories.items():
        print(f"\n{'=' * 50}")
        print(f"🧪 EJECUTANDO TESTS DE {category.upper()}")
        print(f"{'=' * 50}")

        success = run_tests(test_path, verbose=True)
        results[category] = success

        print(f"📊 {category}: {'✅ PASÓ' if success else '❌ FALLÓ'}")

    return results


def cleanup():
    """Limpiar servicios Docker"""
    print("🧹 Limpiando servicios Docker...")
    run_command("docker compose -f docker-compose.test.yml down -v", check=False)


def show_service_status():
    """Mostrar estado de servicios"""
    print("\n📊 ESTADO DE SERVICIOS:")
    run_command("docker compose -f docker-compose.test.yml ps")

    print("\n🔴 REDIS INFO:")
    run_command(
        "docker compose -f docker-compose.test.yml exec -T test-redis redis-cli info server",
        check=False,
    )

    print("\n📊 POSTGRESQL STATUS:")
    run_command(
        "docker compose -f docker-compose.test.yml exec -T test-db psql -U test_user -d reservaflow_test -c 'SELECT COUNT(*) as reservations_count FROM reservations_reservation;'",
        check=False,
    )


def main():
    parser = argparse.ArgumentParser(description="Ejecutar tests realistas con Docker")
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Solo configurar entorno sin ejecutar tests",
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Solo limpiar servicios Docker"
    )
    parser.add_argument(
        "--status", action="store_true", help="Mostrar estado de servicios"
    )
    parser.add_argument(
        "--test-path", type=str, help="Path específico de tests a ejecutar"
    )
    parser.add_argument(
        "--categories", action="store_true", help="Ejecutar tests por categorías"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Output verboso")
    parser.add_argument(
        "--failfast", "-x", action="store_true", help="Parar en primer fallo"
    )

    args = parser.parse_args()

    if args.cleanup:
        cleanup()
        return

    if args.status:
        show_service_status()
        return

    try:
        # Configurar entorno
        if not setup_test_environment():
            print("❌ Error configurando entorno de tests")
            sys.exit(1)

        if args.setup_only:
            print("✅ Entorno configurado. Servicios corriendo.")
            show_service_status()
            return

        # Ejecutar tests
        if args.categories:
            results = run_specific_test_categories()

            # Reporte final
            print(f"\n{'=' * 60}")
            print("📊 REPORTE FINAL DE TESTS REALISTAS")
            print(f"{'=' * 60}")

            total = len(results)
            passed = sum(results.values())

            for category, success in results.items():
                status = "✅ PASÓ" if success else "❌ FALLÓ"
                print(f"{category:15} {status}")

            print(f"\n📊 RESUMEN: {passed}/{total} categorías pasaron")

        else:
            success = run_tests(args.test_path, args.verbose, args.failfast)
            if success:
                print("✅ Tests completados exitosamente")
            else:
                print("❌ Algunos tests fallaron")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ Cancelado por usuario")

    finally:
        if not args.setup_only:
            cleanup()


if __name__ == "__main__":
    main()
