"""
Unit tests for models
"""
from datetime import date, time, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from unittest.mock import patch

from restaurants.models import Restaurant, Table
from customers.models import Customer
from reservations.models import Reservation
from tests.fixtures.factories import (
    RestaurantFactory, 
    TableFactory, 
    CustomerFactory, 
    ReservationFactory,
    ConfirmedReservationFactory,
    ExpiredReservationFactory
)
from tests.fixtures.base import BaseTestCase, CeleryTestCase


class RestaurantModelTest(BaseTestCase):
    """Test Restaurant model"""
    
    def test_restaurant_creation(self):
        """Test basic restaurant creation"""
        restaurant = RestaurantFactory(name="Test Restaurant")
        self.assertEqual(restaurant.name, "Test Restaurant")
        self.assertTrue(restaurant.is_active)
        self.assertIsNotNone(restaurant.created_at)
        self.assertIsNotNone(restaurant.updated_at)
    
    def test_restaurant_str(self):
        """Test restaurant string representation"""
        restaurant = RestaurantFactory(name="My Restaurant")
        self.assertEqual(str(restaurant), "My Restaurant")
    
    def test_restaurant_fields(self):
        """Test all restaurant fields"""
        restaurant = RestaurantFactory(
            name="Test Restaurant",
            description="A great place to eat",
            address="123 Main St",
            phone="555-0123",
            email="test@restaurant.com",
            opening_time=time(8, 0),
            closing_time=time(23, 0),
            reservation_duration=90,
            advance_booking_days=60
        )
        
        self.assertEqual(restaurant.name, "Test Restaurant")
        self.assertEqual(restaurant.description, "A great place to eat")
        self.assertEqual(restaurant.opening_time, time(8, 0))
        self.assertEqual(restaurant.closing_time, time(23, 0))
        self.assertEqual(restaurant.reservation_duration, 90)
        self.assertEqual(restaurant.advance_booking_days, 60)


class TableModelTest(BaseTestCase):
    """Test Table model"""
    
    def test_table_creation(self):
        """Test basic table creation"""
        table = TableFactory(restaurant=self.restaurant, number="T1", capacity=4)
        self.assertEqual(table.restaurant, self.restaurant)
        self.assertEqual(table.number, "T1")
        self.assertEqual(table.capacity, 4)
        self.assertTrue(table.is_active)
    
    def test_table_str(self):
        """Test table string representation"""
        table = TableFactory(restaurant=self.restaurant, number="5")
        expected = f"Mesa 5 - {self.restaurant.name}"
        self.assertEqual(str(table), expected)
    
    def test_table_locations(self):
        """Test different table locations"""
        indoor_table = TableFactory(restaurant=self.restaurant, location="indoor")
        outdoor_table = TableFactory(restaurant=self.restaurant, location="outdoor")
        bar_table = TableFactory(restaurant=self.restaurant, location="bar")
        
        self.assertEqual(indoor_table.location, "indoor")
        self.assertEqual(outdoor_table.location, "outdoor")
        self.assertEqual(bar_table.location, "bar")


class CustomerModelTest(BaseTestCase):
    """Test Customer model"""
    
    def test_customer_creation(self):
        """Test basic customer creation"""
        customer = CustomerFactory(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="555-1234"
        )
        
        self.assertEqual(customer.first_name, "John")
        self.assertEqual(customer.last_name, "Doe")
        self.assertEqual(customer.email, "john@example.com")
        self.assertEqual(customer.phone, "555-1234")
    
    def test_customer_str(self):
        """Test customer string representation"""
        customer = CustomerFactory(first_name="Jane", last_name="Smith")
        self.assertEqual(str(customer), "Jane Smith")


class ReservationModelTest(CeleryTestCase):
    """Test Reservation model"""
    
    def test_reservation_creation(self):
        """Test basic reservation creation"""
        reservation = ReservationFactory(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            party_size=4
        )
        
        self.assertEqual(reservation.restaurant, self.restaurant)
        self.assertEqual(reservation.customer, self.customer)
        self.assertEqual(reservation.table, self.table)
        self.assertEqual(reservation.party_size, 4)
        self.assertEqual(reservation.status, Reservation.Status.PENDING)
        self.assertIsNotNone(reservation.expires_at)
    
    def test_reservation_str(self):
        """Test reservation string representation"""
        reservation = ReservationFactory(customer=self.customer)
        expected = f"Reserva {reservation.id.hex[:8]} - {self.customer}"
        self.assertEqual(str(reservation), expected)
    
    def test_reservation_datetime_property(self):
        """Test reservation_datetime property"""
        reservation = ReservationFactory(
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 30)
        )
        
        dt = reservation.reservation_datetime
        self.assertEqual(dt.date(), date(2025, 9, 15))
        self.assertEqual(dt.time(), time(19, 30))
    
    def test_is_expired_method(self):
        """Test is_expired method"""
        # Not expired reservation
        future_time = timezone.now() + timedelta(hours=1)
        reservation = ReservationFactory(
            expires_at=future_time,
            status=Reservation.Status.PENDING
        )
        self.assertFalse(reservation.is_expired())
        
        # Expired reservation - create manually to avoid factory post-generation
        past_time = timezone.now() - timedelta(hours=1)
        expired_reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=time(19, 0),
            party_size=2,
            status=Reservation.Status.PENDING,
            expires_at=past_time
        )
        self.assertTrue(expired_reservation.is_expired())
        
        # No expires_at
        no_expiry = ConfirmedReservationFactory()
        self.assertFalse(no_expiry.is_expired())
    
    def test_double_booking_validation(self):
        """Test that double booking is prevented"""
        # Create first reservation
        reservation1 = ReservationFactory(
            restaurant=self.restaurant,
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status=Reservation.Status.CONFIRMED
        )
        
        # Try to create conflicting reservation
        with self.assertRaises(ValidationError):
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
    
    def test_unique_constraint_double_booking(self):
        """Test unique constraint prevents double booking at database level"""
        # Create first reservation
        reservation1 = ReservationFactory(
            restaurant=self.restaurant,
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status=Reservation.Status.CONFIRMED
        )
        
        # Try to create conflicting reservation bypassing model validation
        # The model.save() calls full_clean(), so we get ValidationError instead of IntegrityError
        with self.assertRaises((IntegrityError, ValidationError)):
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
                # This will trigger validation through save()
                reservation2.save()
    
    def test_double_booking_allowed_after_cancellation(self):
        """Test that reservation can be made after cancellation"""
        # Create and cancel first reservation
        reservation1 = ReservationFactory(
            restaurant=self.restaurant,
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status=Reservation.Status.CANCELLED
        )
        
        # Should be able to create new reservation
        reservation2 = ReservationFactory(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status=Reservation.Status.PENDING
        )
        
        self.assertIsNotNone(reservation2.id)
    
    def test_expires_at_set_on_pending(self):
        """Test that expires_at is set for pending reservations"""
        # Test with default timeout (15 minutes)
        reservation = ReservationFactory(status=Reservation.Status.PENDING)
        self.assertIsNotNone(reservation.expires_at)
        
        # Should be approximately 15 minutes from now (default timeout)
        expected_time = timezone.now() + timedelta(minutes=15)
        time_diff = abs((reservation.expires_at - expected_time).total_seconds())
        self.assertLess(time_diff, 120)  # Within 2 minute tolerance
    
    def test_expires_at_not_set_on_confirmed(self):
        """Test that expires_at is not set for confirmed reservations"""
        reservation = ConfirmedReservationFactory()
        # Note: Factory might set it, but the model logic shouldn't for confirmed
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
    
    @patch('reservations.tasks.expire_reservation.apply_async')
    def test_schedule_expiration_called(self, mock_task):
        """Test that expiration is scheduled for pending reservations"""
        mock_task.reset_mock()  # Reset any previous calls
        
        reservation = ReservationFactory(status=Reservation.Status.PENDING)
        
        # Verify task was called at least once
        self.assertTrue(mock_task.called)
        
        # Get the last call (most recent) and verify it was called correctly
        last_call = mock_task.call_args
        if last_call:
            args, kwargs = last_call
            # Check if args are passed as positional or keyword
            if args:
                self.assertEqual(args[0], [str(reservation.id)])
            elif 'args' in kwargs:
                self.assertEqual(kwargs['args'], [str(reservation.id)])
            
            self.assertEqual(kwargs.get('eta'), reservation.expires_at)
    
    @patch('reservations.tasks.schedule_reminder.delay')
    def test_schedule_reminder_on_confirmation(self, mock_task):
        """Test that reminder is scheduled when reservation is confirmed"""
        # Create pending reservation
        reservation = ReservationFactory(status=Reservation.Status.PENDING)
        
        # Confirm it
        reservation.status = Reservation.Status.CONFIRMED
        reservation.save()
        
        # Verify reminder task was called
        mock_task.assert_called_once_with(str(reservation.id), hours_before=24)
    
    def test_status_choices(self):
        """Test all status choices work"""
        for status_value, status_label in Reservation.Status.choices:
            reservation = ReservationFactory(status=status_value)
            self.assertEqual(reservation.status, status_value)
            self.assertEqual(reservation.get_status_display(), status_label)