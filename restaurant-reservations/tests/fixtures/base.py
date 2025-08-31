"""
Base test classes and utilities
"""
from django.test import TestCase, TransactionTestCase

from .factories import (
    RestaurantFactory, 
    TableFactory, 
    CustomerFactory
)


class BaseTestCase(TestCase):
    """Base test case with common setup"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data"""
        cls.restaurant = RestaurantFactory()
        cls.table = TableFactory(restaurant=cls.restaurant)
        cls.customer = CustomerFactory()
    
    def setUp(self):
        """Set up for each test"""
        # Refresh objects from database
        self.restaurant.refresh_from_db()
        self.table.refresh_from_db() 
        self.customer.refresh_from_db()


class CeleryTestCase(TransactionTestCase):
    """Base test case for testing Celery tasks"""
    
    def setUp(self):
        """Set up for Celery tests"""
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer = CustomerFactory()
        
        # Don't mock Celery tasks here - let conftest.py handle it globally
        # Individual tests can access the mocks from the fixture if needed


class EmailTestCase(BaseTestCase):
    """Base test case for testing email functionality"""
    
    def setUp(self):
        """Set up for email tests"""
        super().setUp()
        # Email mocking is now handled globally by conftest.py
        # Individual tests can access the mocks from the celery fixture if needed


class APITestCase(BaseTestCase):
    """Base test case for API testing"""
    
    def setUp(self):
        """Set up for API tests"""
        super().setUp()
        from rest_framework.test import APIClient
        from django.contrib.auth.models import User
        
        self.client = APIClient()
        
        # Create a test user and authenticate for API tests that require authentication
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.test_user)
        
        # Don't mock external services here - the services are already test-friendly
        # Individual tests can mock specific services if needed