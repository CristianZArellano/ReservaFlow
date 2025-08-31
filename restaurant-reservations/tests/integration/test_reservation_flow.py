"""
Integration tests for complete reservation flow
"""
from datetime import date, time, timedelta
from django.test import TransactionTestCase
from django.db import transaction
from django.utils import timezone
from unittest.mock import patch

from reservations.models import Reservation
from reservations.tasks import expire_reservation
from tests.fixtures.factories import (
    RestaurantFactory,
    TableFactory,
    CustomerFactory,
    ReservationFactory
)


class ReservationFlowIntegrationTest(TransactionTestCase):
    """Test complete reservation flow integration"""
    
    def setUp(self):
        """Set up test data"""
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant, number="1")
        self.customer = CustomerFactory()
    
    @patch('django.core.mail.send_mail')
    @patch('reservations.tasks.expire_reservation.apply_async')
    @patch('reservations.tasks.schedule_reminder.delay')
    def test_complete_reservation_lifecycle(self, mock_reminder, mock_expire, mock_email):
        """Test complete reservation lifecycle from creation to completion"""
        
        # 1. Create pending reservation
        reservation = ReservationFactory(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            status=Reservation.Status.PENDING
        )
        
        self.assertEqual(reservation.status, Reservation.Status.PENDING)
        self.assertIsNotNone(reservation.expires_at)
        
        # Verify expiration was scheduled
        mock_expire.assert_called()
        
        # 2. Confirm reservation
        reservation.status = Reservation.Status.CONFIRMED
        reservation.save()
        
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
        
        # Verify reminder was scheduled
        mock_reminder.assert_called_once_with(str(reservation.id), hours_before=24)
        
        # 3. Complete reservation
        reservation.status = Reservation.Status.COMPLETED
        reservation.save()
        
        self.assertEqual(reservation.status, Reservation.Status.COMPLETED)
    
    def test_reservation_expiration_flow(self):
        """Test automatic reservation expiration"""
        # Create reservation manually to control expires_at
        past_time = timezone.now() - timedelta(minutes=30)
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=time(19, 0),
            party_size=2,
            status=Reservation.Status.PENDING,
            expires_at=past_time
        )
        
        # Run expiration task
        result = expire_reservation(str(reservation.id))
        
        # Verify reservation was expired
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)
        self.assertEqual(result['status'], 'expired')
    
    def test_double_booking_prevention_integration(self):
        """Test double booking prevention across the full stack"""
        # Create first reservation
        reservation1 = ReservationFactory(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status=Reservation.Status.CONFIRMED
        )
        
        # Try to create conflicting reservation through different code paths
        
        # 1. Through model validation
        with self.assertRaises(Exception):  # ValidationError or IntegrityError
            with transaction.atomic():
                reservation2 = Reservation(
                    restaurant=self.restaurant,
                    customer=self.customer,
                    table=self.table,
                    reservation_date=date(2025, 9, 15),
                    reservation_time=time(19, 0),
                    party_size=2,
                    status=Reservation.Status.PENDING
                )
                reservation2.full_clean()
                reservation2.save()
        
        # 2. Through direct creation (should hit database constraint)
        with self.assertRaises(Exception):  # IntegrityError
            with transaction.atomic():
                Reservation.objects.create(
                    restaurant=self.restaurant,
                    customer=self.customer,
                    table=self.table,
                    reservation_date=date(2025, 9, 15),
                    reservation_time=time(19, 0),
                    party_size=2,
                    status=Reservation.Status.PENDING
                )
    
    def test_reservation_allowed_after_cancellation(self):
        """Test that new reservation can be made after cancellation"""
        # Create and cancel first reservation
        reservation1 = ReservationFactory(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status=Reservation.Status.CANCELLED
        )
        
        # Create new reservation for same slot
        reservation2 = ReservationFactory(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status=Reservation.Status.PENDING
        )
        
        # Should succeed
        self.assertIsNotNone(reservation2.id)
        self.assertEqual(reservation2.status, Reservation.Status.PENDING)
    
    def test_email_integration_flow(self):
        """Test email sending integration with reservation flow"""
        # Email mocking is handled globally by conftest.py
        
        # Import tasks here to avoid circular imports
        from reservations.tasks import send_confirmation_email, send_reminder
        
        reservation = ReservationFactory(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            status=Reservation.Status.CONFIRMED,
            customer__email="test@example.com",
            customer__first_name="John"
        )
        
        # Test confirmation email
        result = send_confirmation_email(str(reservation.id))
        self.assertEqual(result['status'], 'email_sent')
        
        # Test reminder email
        result = send_reminder(str(reservation.id))
        self.assertEqual(result['status'], 'reminder_sent')
    
    def test_multiple_restaurants_isolation(self):
        """Test that reservations are properly isolated between restaurants"""
        # Create second restaurant and table
        restaurant2 = RestaurantFactory()
        table2 = TableFactory(restaurant=restaurant2, number="1")
        
        # Create reservations for same date/time on different restaurants
        reservation1 = ReservationFactory(
            restaurant=self.restaurant,
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status=Reservation.Status.CONFIRMED
        )
        
        reservation2 = ReservationFactory(
            restaurant=restaurant2,
            table=table2,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status=Reservation.Status.CONFIRMED
        )
        
        # Both should succeed (different restaurants)
        self.assertIsNotNone(reservation1.id)
        self.assertIsNotNone(reservation2.id)
        self.assertNotEqual(reservation1.restaurant, reservation2.restaurant)
    
    def test_table_capacity_and_multiple_reservations(self):
        """Test multiple reservations for different tables at same restaurant"""
        # Create additional tables
        table2 = TableFactory(restaurant=self.restaurant, number="2")
        table3 = TableFactory(restaurant=self.restaurant, number="3")
        
        # Create reservations for same time on different tables
        reservations = []
        for table in [self.table, table2, table3]:
            reservation = ReservationFactory(
                restaurant=self.restaurant,
                table=table,
                reservation_date=date(2025, 9, 15),
                reservation_time=time(19, 0),
                status=Reservation.Status.CONFIRMED
            )
            reservations.append(reservation)
        
        # All should succeed (different tables)
        self.assertEqual(len(reservations), 3)
        table_numbers = {r.table.number for r in reservations}
        self.assertEqual(table_numbers, {"1", "2", "3"})


class ReservationConcurrencyTest(TransactionTestCase):
    """Test reservation system under concurrent conditions"""
    
    def setUp(self):
        """Set up test data"""
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer = CustomerFactory()
    
    def test_concurrent_reservation_attempts(self):
        """Test handling of concurrent reservation attempts"""
        # Test sequential attempts to simulate concurrency since SQLite in-memory 
        # doesn't handle true concurrency well in tests
        
        # Create first reservation
        reservation1 = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            party_size=2,
            status=Reservation.Status.CONFIRMED
        )
        
        # Try to create conflicting reservation - should fail
        from django.core.exceptions import ValidationError
        from django.db import IntegrityError
        
        with self.assertRaises((ValidationError, IntegrityError)):
            with transaction.atomic():
                reservation2 = Reservation.objects.create(
                    restaurant=self.restaurant,
                    customer=CustomerFactory(),  # Different customer
                    table=self.table,
                    reservation_date=date(2025, 9, 15),
                    reservation_time=time(19, 0),
                    party_size=2,
                    status=Reservation.Status.PENDING
                )
        
        # Verify only one reservation exists for this slot
        reservations = Reservation.objects.filter(
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED]
        )
        self.assertEqual(reservations.count(), 1)


class SystemIntegrationTest(TransactionTestCase):
    """Test system-wide integration scenarios"""
    
    def setUp(self):
        """Set up complex test scenario"""
        self.restaurants = [RestaurantFactory() for _ in range(3)]
        self.tables = []
        self.customers = [CustomerFactory() for _ in range(5)]
        
        # Create tables for each restaurant
        for restaurant in self.restaurants:
            restaurant_tables = [
                TableFactory(restaurant=restaurant, number=str(i))
                for i in range(1, 4)
            ]
            self.tables.extend(restaurant_tables)
    
    @patch('django.core.mail.send_mail')
    def test_complex_reservation_scenario(self, mock_send_mail):
        """Test complex scenario with multiple restaurants, tables, and customers"""
        mock_send_mail.return_value = 1
        
        reservations = []
        
        # Create various types of reservations
        reservation_scenarios = [
            # Restaurant 1 - Multiple time slots
            (self.restaurants[0], self.tables[0], self.customers[0], time(18, 0), Reservation.Status.CONFIRMED),
            (self.restaurants[0], self.tables[0], self.customers[1], time(20, 0), Reservation.Status.PENDING),
            (self.restaurants[0], self.tables[1], self.customers[2], time(18, 0), Reservation.Status.CONFIRMED),
            
            # Restaurant 2 - Same times as restaurant 1 (should work)
            (self.restaurants[1], self.tables[3], self.customers[3], time(18, 0), Reservation.Status.CONFIRMED),
            (self.restaurants[1], self.tables[4], self.customers[4], time(18, 0), Reservation.Status.PENDING),
            
            # Restaurant 3 - Mixed statuses
            (self.restaurants[2], self.tables[6], self.customers[0], time(19, 0), Reservation.Status.CANCELLED),
            (self.restaurants[2], self.tables[7], self.customers[1], time(19, 0), Reservation.Status.COMPLETED),
        ]
        
        for restaurant, table, customer, res_time, status in reservation_scenarios:
            reservation = ReservationFactory(
                restaurant=restaurant,
                table=table,
                customer=customer,
                reservation_date=date(2025, 9, 15),
                reservation_time=res_time,
                status=status
            )
            reservations.append(reservation)
        
        # Verify all reservations were created
        self.assertEqual(len(reservations), 7)
        
        # Verify no conflicts
        active_reservations = [r for r in reservations if r.status in ['pending', 'confirmed']]
        self.assertEqual(len(active_reservations), 5)
        
        # Test querying reservations by various criteria
        restaurant1_reservations = Reservation.objects.filter(restaurant=self.restaurants[0])
        self.assertEqual(restaurant1_reservations.count(), 3)
        
        time_18_reservations = Reservation.objects.filter(
            reservation_time=time(18, 0),
            status__in=['pending', 'confirmed']
        )
        # Should have at least the 3 we created, but factories might create more
        self.assertGreaterEqual(time_18_reservations.count(), 3)
        
        # Test updating reservation status
        pending_reservation = Reservation.objects.filter(status='pending').first()
        if pending_reservation:
            pending_reservation.status = Reservation.Status.CONFIRMED
            pending_reservation.save()
            
            pending_reservation.refresh_from_db()
            self.assertEqual(pending_reservation.status, Reservation.Status.CONFIRMED)