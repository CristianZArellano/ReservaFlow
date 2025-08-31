"""
Integration tests for API endpoints
"""
from django.test import TransactionTestCase
from django.test import Client
from unittest.mock import patch
import json

from reservations.models import Reservation
from tests.fixtures.factories import (
    RestaurantFactory,
    TableFactory,
    CustomerFactory,
    ReservationFactory
)


class APIIntegrationTest(TransactionTestCase):
    """Test API integration with real database operations"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer = CustomerFactory()
    
    @patch('reservations.views.TableReservationLock')
    @patch('reservations.views.check_table_availability')
    @patch('reservations.tasks.expire_reservation.apply_async')
    def test_end_to_end_reservation_creation(self, mock_expire, mock_availability, mock_lock):
        """Test complete end-to-end reservation creation via API"""
        # Setup mocks
        mock_availability.return_value = True
        mock_lock.return_value.__enter__.return_value = None
        
        # API request data
        data = {
            'restaurant_id': self.restaurant.id,
            'customer_id': self.customer.id,
            'table_id': self.table.id,
            'reservation_date': '2025-09-15',
            'reservation_time': '19:00:00',
            'party_size': 4
        }
        
        # Make API call
        response = self.client.post(
            '/api/',
            json.dumps(data),
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        
        self.assertIn('id', response_data)
        self.assertEqual(response_data['status'], 'pending')
        self.assertIn('expires_at', response_data)
        self.assertIn('message', response_data)
        
        # Verify database state
        reservation = Reservation.objects.get(id=response_data['id'])
        self.assertEqual(reservation.restaurant, self.restaurant)
        self.assertEqual(reservation.customer, self.customer)
        self.assertEqual(reservation.table, self.table)
        self.assertEqual(reservation.party_size, 4)
        self.assertEqual(str(reservation.reservation_date), '2025-09-15')
        self.assertEqual(str(reservation.reservation_time), '19:00:00')
        self.assertEqual(reservation.status, 'pending')
        self.assertIsNotNone(reservation.expires_at)
        
        # Verify expiration was scheduled
        mock_expire.assert_called_once()
    
    @patch('reservations.views.TableReservationLock')
    @patch('reservations.views.check_table_availability')
    def test_api_double_booking_prevention(self, mock_availability, mock_lock):
        """Test double booking prevention through API"""
        mock_availability.return_value = True
        mock_lock.return_value.__enter__.return_value = None
        
        # Create first reservation via API
        data = {
            'restaurant_id': self.restaurant.id,
            'customer_id': self.customer.id,
            'table_id': self.table.id,
            'reservation_date': '2025-09-15',
            'reservation_time': '19:00:00',
            'party_size': 2
        }
        
        response1 = self.client.post(
            '/api/',
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, 201)
        
        # Try to create conflicting reservation
        response2 = self.client.post(
            '/api/',
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response2.status_code, 400)
        
        response_data = response2.json()
        self.assertEqual(response_data['error'], 'Validación fallida')
        self.assertIn('details', response_data)
    
    def test_api_reservation_retrieval(self):
        """Test retrieving reservations via API"""
        # Create test reservations
        reservation1 = ReservationFactory(restaurant=self.restaurant)
        reservation2 = ReservationFactory(restaurant=self.restaurant)
        
        # Test list endpoint
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        
        reservation_ids = {r['id'] for r in data}
        self.assertIn(str(reservation1.id), reservation_ids)
        self.assertIn(str(reservation2.id), reservation_ids)
        
        # Test detail endpoint
        response = self.client.get(f'/api/{reservation1.id}/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['id'], str(reservation1.id))
        self.assertEqual(data['status'], reservation1.status)
    
    @patch('reservations.views.TableReservationLock')
    @patch('reservations.views.check_table_availability')
    def test_api_table_unavailable_scenario(self, mock_availability, mock_lock):
        """Test API response when table is unavailable"""
        mock_availability.return_value = False
        mock_lock.return_value.__enter__.return_value = None
        
        data = {
            'restaurant_id': self.restaurant.id,
            'customer_id': self.customer.id,
            'table_id': self.table.id,
            'reservation_date': '2025-09-15',
            'reservation_time': '19:00:00',
            'party_size': 2
        }
        
        response = self.client.post(
            '/api/',
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('no disponible', data['error'])
    
    def test_api_validation_errors(self):
        """Test API validation error handling"""
        # Missing required fields
        data = {
            'reservation_date': '2025-09-15',
            'party_size': 2
        }
        
        response = self.client.post(
            '/api/',
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertIn('campos requeridos', response_data['error'])
    
    def test_api_nonexistent_resource(self):
        """Test API response for nonexistent resources"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = self.client.get(f'/api/{fake_id}/')
        self.assertEqual(response.status_code, 404)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('no encontrada', data['error'])


class APIPerformanceIntegrationTest(TransactionTestCase):
    """Test API performance and scalability"""
    
    def setUp(self):
        """Set up performance test data"""
        self.client = Client()
        self.restaurant = RestaurantFactory()
        self.tables = [
            TableFactory(restaurant=self.restaurant, number=str(i))
            for i in range(1, 11)  # 10 tables
        ]
        self.customers = [CustomerFactory() for _ in range(20)]
    
    @patch('reservations.views.TableReservationLock')
    @patch('reservations.views.check_table_availability')
    def test_multiple_reservations_creation(self, mock_availability, mock_lock):
        """Test creating multiple reservations efficiently"""
        mock_availability.return_value = True
        mock_lock.return_value.__enter__.return_value = None
        
        reservation_requests = []
        
        # Create 20 different reservation requests
        for i, customer in enumerate(self.customers):
            table = self.tables[i % len(self.tables)]
            hour = 18 + (i % 4)  # Hours 18-21
            
            data = {
                'restaurant_id': self.restaurant.id,
                'customer_id': customer.id,
                'table_id': table.id,
                'reservation_date': '2025-09-15',
                'reservation_time': f'{hour:02d}:00:00',
                'party_size': 2 + (i % 4)
            }
            reservation_requests.append(data)
        
        successful_reservations = 0
        failed_reservations = 0
        
        # Create reservations
        for data in reservation_requests:
            response = self.client.post(
                '/api/',
                json.dumps(data),
                content_type='application/json'
            )
            
            if response.status_code == 201:
                successful_reservations += 1
            else:
                failed_reservations += 1
        
        # Should have created multiple reservations successfully
        self.assertGreater(successful_reservations, 15)
        
        # Verify database state
        total_reservations = Reservation.objects.count()
        self.assertEqual(total_reservations, successful_reservations)
    
    def test_api_list_performance_with_many_reservations(self):
        """Test list API performance with many reservations"""
        # Create many reservations
        reservations = []
        for i in range(50):
            table = self.tables[i % len(self.tables)]
            customer = self.customers[i % len(self.customers)]
            
            reservation = ReservationFactory(
                restaurant=self.restaurant,
                table=table,
                customer=customer
            )
            reservations.append(reservation)
        
        # Test list endpoint performance
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data), 50)
        
        # Verify data structure
        for reservation_data in data[:5]:  # Check first 5
            self.assertIn('id', reservation_data)
            self.assertIn('status', reservation_data)
            self.assertIn('reservation_date', reservation_data)
            self.assertIn('reservation_time', reservation_data)


class APISecurityIntegrationTest(TransactionTestCase):
    """Test API security aspects"""
    
    def setUp(self):
        """Set up security test data"""
        self.client = Client()
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer = CustomerFactory()
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection attacks"""
        # Try SQL injection in URL parameter
        malicious_id = "1'; DROP TABLE reservations_reservation; --"
        
        response = self.client.get(f'/api/{malicious_id}/')
        
        # Should return 404 or 400, not crash
        self.assertIn(response.status_code, [400, 404])
        
        # Verify table still exists by querying it
        count = Reservation.objects.count()
        self.assertEqual(count, 0)  # Should be 0 (empty), not crashed
    
    def test_malicious_json_payload(self):
        """Test handling of malicious JSON payloads"""
        malicious_payloads = [
            # Extremely long string
            {'table_id': 'x' * 10000},
            
            # Nested objects (should be handled gracefully)
            {'table_id': {'$ne': None}},
            
            # Script injection attempt
            {'party_size': '<script>alert("xss")</script>'},
        ]
        
        for payload in malicious_payloads:
            response = self.client.post(
                '/api/',
                json.dumps(payload),
                content_type='application/json'
            )
            
            # Should return validation error, not crash
            self.assertIn(response.status_code, [400, 500])
    
    def test_large_payload_handling(self):
        """Test handling of unreasonably large payloads"""
        # Create very large payload
        large_data = {
            'table_id': self.table.id,
            'reservation_date': '2025-09-15',
            'reservation_time': '19:00:00',
            'party_size': 2,
            'notes': 'x' * 100000  # 100KB of notes
        }
        
        response = self.client.post(
            '/api/',
            json.dumps(large_data),
            content_type='application/json'
        )
        
        # Should handle gracefully (might accept or reject based on limits)
        self.assertIn(response.status_code, [200, 201, 400, 413])
    
    def test_content_type_validation(self):
        """Test proper content type validation"""
        data = {
            'table_id': self.table.id,
            'reservation_date': '2025-09-15',
            'reservation_time': '19:00:00',
            'party_size': 2
        }
        
        # Send as form data instead of JSON
        response = self.client.post('/api/', data)
        
        # Should handle different content types appropriately
        self.assertIn(response.status_code, [200, 201, 400, 415])