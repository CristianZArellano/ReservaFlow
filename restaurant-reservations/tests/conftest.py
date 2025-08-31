"""
pytest configuration and fixtures
"""
import pytest
import os
import sys
from unittest.mock import patch
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def pytest_configure():
    """Configure Django settings for pytest"""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                    'TEST': {
                        'NAME': ':memory:',
                    },
                }
            },
            INSTALLED_APPS=[
                'django.contrib.admin',
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
                'django.contrib.staticfiles',
                'rest_framework',
                'corsheaders',
                'restaurants',
                'customers', 
                'reservations',
                'notifications',
            ],
            ROOT_URLCONF='config.urls',
            SECRET_KEY='test-secret-key',
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
            DEFAULT_FROM_EMAIL='test@example.com',
            CELERY_TASK_ALWAYS_EAGER=True,  # Execute tasks synchronously
            CELERY_TASK_EAGER_PROPAGATES=True,
            CELERY_BROKER_URL='memory://',  # Use in-memory broker for tests
            CELERY_RESULT_BACKEND='cache+memory://',
            RESERVATION_PENDING_TIMEOUT=15,
            USE_TZ=True,
            TIME_ZONE='UTC',
            CACHES={
                'default': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                    'LOCATION': 'unique-snowflake',
                }
            },
            REDIS_URL='redis://localhost:6379/0',  # For services.py compatibility
            MIDDLEWARE=[
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'corsheaders.middleware.CorsMiddleware',
                'django.middleware.common.CommonMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
            ],
            REST_FRAMEWORK={
                'DEFAULT_RENDERER_CLASSES': [
                    'rest_framework.renderers.JSONRenderer',
                ],
                'TEST_REQUEST_DEFAULT_FORMAT': 'json',
                'DEFAULT_THROTTLE_RATES': {
                    'anon': '1000/hour',
                    'user': '2000/hour',
                    'reservation': '50/hour',
                },
            },
        )
        django.setup()

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Enable database access for all tests
    """
    pass

@pytest.fixture(autouse=True)  
def mock_celery_tasks():
    """
    Mock Celery tasks and mail to prevent actual execution during tests
    """
    with patch('django.core.mail.send_mail') as mock_send_mail:
        # Configure send_mail mock
        mock_send_mail.return_value = 1
        
        # Yield mocks for tests that need them
        yield {
            'send_mail': mock_send_mail
        }