#!/usr/bin/env python
"""
Test runner script for ReservaFlow
"""

import sys
import subprocess


def main():
    """Run tests with different options"""

    print("🧪 ReservaFlow Test Suite")
    print("=" * 50)

    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    else:
        test_type = "all"

    # Base pytest command
    base_cmd = ["uv", "run", "pytest"]

    if test_type == "unit":
        print("🔬 Running Unit Tests...")
        cmd = base_cmd + ["tests/unit/", "-m", "unit"]

    elif test_type == "integration":
        print("🔗 Running Integration Tests...")
        cmd = base_cmd + ["tests/integration/", "-m", "integration"]

    elif test_type == "fast":
        print("⚡ Running Fast Tests...")
        cmd = base_cmd + ["-m", "not slow"]

    elif test_type == "coverage":
        print("📊 Running Tests with Coverage...")
        cmd = base_cmd + ["--cov=.", "--cov-report=term-missing", "--cov-report=html"]

    elif test_type == "models":
        print("🗃️ Running Model Tests...")
        cmd = base_cmd + ["tests/unit/test_models.py", "-v"]

    elif test_type == "tasks":
        print("⚙️ Running Celery Task Tests...")
        cmd = base_cmd + ["tests/unit/test_tasks.py", "-v"]

    elif test_type == "views":
        print("🌐 Running View Tests...")
        cmd = base_cmd + ["tests/unit/test_views.py", "-v"]

    elif test_type == "flow":
        print("🌊 Running Integration Flow Tests...")
        cmd = base_cmd + ["tests/integration/test_reservation_flow.py", "-v"]

    elif test_type == "api":
        print("🔌 Running API Integration Tests...")
        cmd = base_cmd + ["tests/integration/test_api_integration.py", "-v"]

    else:
        print("🚀 Running All Tests...")
        cmd = base_cmd + ["-v"]

    # Add common options
    cmd.extend(["--tb=short", "--disable-warnings"])

    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)

    # Run tests
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def print_usage():
    """Print usage information"""
    print("""
Usage: python run_tests.py [test_type]

Test Types:
  all          - Run all tests (default)
  unit         - Run only unit tests
  integration  - Run only integration tests
  fast         - Run fast tests (exclude slow ones)
  coverage     - Run tests with coverage report
  models       - Run model tests only
  tasks        - Run Celery task tests only  
  views        - Run view/API tests only
  flow         - Run reservation flow tests only
  api          - Run API integration tests only

Examples:
  python run_tests.py unit
  python run_tests.py coverage
  python run_tests.py models
""")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print_usage()
        sys.exit(0)

    exit_code = main()
    sys.exit(exit_code)
