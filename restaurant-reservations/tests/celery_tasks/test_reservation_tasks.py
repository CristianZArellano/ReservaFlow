# tests/celery/test_reservation_tasks.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone

from reservations.tasks import (
    expire_reservation,
    send_confirmation_email,
    send_reminder,
    schedule_reminder,
)
from reservations.models import Reservation
from tests.fixtures.factories import RestaurantFactory, TableFactory, CustomerFactory


class TestReservationTasks(TestCase):
    """Tests for reservation Celery tasks"""

    def setUp(self):
        """Set up test data"""
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer = CustomerFactory(email="test@example.com")

    def test_expire_reservation_success(self):
        """Test successful reservation expiration"""
        # Create expired reservation
        past_time = timezone.now() - timedelta(minutes=30)
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=2,
            status=Reservation.Status.PENDING,
            expires_at=past_time,
        )

        # Execute task
        result = expire_reservation(str(reservation.id))

        # Verify result
        self.assertEqual(result["status"], "expired")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)

    def test_expire_reservation_not_expired(self):
        """Test task with non-expired reservation"""
        # Create future reservation
        future_time = timezone.now() + timedelta(hours=1)
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=2,
            status=Reservation.Status.PENDING,
            expires_at=future_time,
        )

        # Execute task
        result = expire_reservation(str(reservation.id))

        # Verify result
        self.assertEqual(result["status"], "pending")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.PENDING)

    def test_expire_reservation_not_found(self):
        """Test task with non-existent reservation"""
        result = expire_reservation("non-existent-id")
        self.assertEqual(result["error"], "not_found")

    @patch("reservations.tasks.send_mail")
    def test_send_confirmation_email_success(self, mock_send_mail):
        """Test successful email sending"""
        # Create confirmed reservation
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=2,
            status=Reservation.Status.CONFIRMED,
        )

        # Mock email sending
        mock_send_mail.return_value = 1

        # Execute task
        result = send_confirmation_email(str(reservation.id))

        # Verify result
        self.assertEqual(result["status"], "email_sent")
        mock_send_mail.assert_called_once()

        # Verify email content
        call_args = mock_send_mail.call_args
        self.assertIn("Confirmación de reserva", call_args[1]["subject"])
        self.assertIn(self.customer.first_name, call_args[1]["message"])

    @patch("reservations.tasks.send_mail")
    def test_send_confirmation_email_smtp_error(self, mock_send_mail):
        """Test email task with SMTP error and retry"""
        import smtplib

        # Create reservation
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=2,
            status=Reservation.Status.CONFIRMED,
        )

        # Mock SMTP error
        mock_send_mail.side_effect = smtplib.SMTPServerDisconnected("Connection lost")

        # Execute task with mock retry
        with patch.object(
            send_confirmation_email, "retry"
        ) as mock_retry, patch.object(
            send_confirmation_email, "request", MagicMock(retries=0)
        ):
            try:
                send_confirmation_email(str(reservation.id))
            except Exception:
                pass  # Expected retry exception

        # Verify retry was called
        mock_retry.assert_called_once()

    @patch("reservations.tasks.send_mail")
    def test_send_reminder_success(self, mock_send_mail):
        """Test successful reminder sending"""
        # Create confirmed reservation
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=4,
            status=Reservation.Status.CONFIRMED,
        )

        # Mock email sending
        mock_send_mail.return_value = 1

        # Execute task
        result = send_reminder(str(reservation.id))

        # Verify result
        self.assertEqual(result["status"], "reminder_sent")
        mock_send_mail.assert_called_once()

        # Verify email content
        call_args = mock_send_mail.call_args
        self.assertIn("Recordatorio", call_args[1]["subject"])
        self.assertIn(self.customer.first_name, call_args[1]["message"])

    def test_send_reminder_not_confirmed(self):
        """Test reminder task with non-confirmed reservation"""
        # Create pending reservation
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=2,
            status=Reservation.Status.PENDING,
        )

        # Execute task
        result = send_reminder(str(reservation.id))

        # Verify result
        self.assertEqual(result["status"], "not_confirmed")

    @patch("reservations.tasks.send_reminder.apply_async")
    def test_schedule_reminder_success(self, mock_apply_async):
        """Test successful reminder scheduling"""
        # Create confirmed reservation for tomorrow
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=2,
            status=Reservation.Status.CONFIRMED,
        )

        # Execute task
        result = schedule_reminder(str(reservation.id), hours_before=2)

        # Verify result
        self.assertEqual(result["status"], "reminder_scheduled")
        self.assertIn("scheduled_time", result)
        mock_apply_async.assert_called_once()

    def test_schedule_reminder_not_found(self):
        """Test reminder scheduling with non-existent reservation"""
        result = schedule_reminder("non-existent-id")
        self.assertEqual(result["error"], "not_found")


@pytest.mark.integration
class TestReservationTasksIntegration(TestCase):
    """Integration tests for reservation tasks with real dependencies"""

    def setUp(self):
        """Set up test data"""
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer = CustomerFactory(email="integration@test.com")

    def test_full_reservation_workflow(self):
        """Test complete reservation workflow with tasks"""
        # 1. Create pending reservation
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=2,
            status=Reservation.Status.PENDING,
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        initial_status = reservation.status
        self.assertEqual(initial_status, Reservation.Status.PENDING)

        # 2. Confirm reservation (triggers email)
        reservation.status = Reservation.Status.CONFIRMED
        reservation.save()

        with patch("reservations.tasks.send_mail") as mock_send_mail:
            mock_send_mail.return_value = 1
            
            # Send confirmation email
            email_result = send_confirmation_email(str(reservation.id))
            self.assertEqual(email_result["status"], "email_sent")

            # Schedule reminder
            with patch("reservations.tasks.send_reminder.apply_async") as mock_schedule:
                reminder_result = schedule_reminder(str(reservation.id))
                self.assertEqual(reminder_result["status"], "reminder_scheduled")

        # 3. Verify final state
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)

    def test_expiration_workflow(self):
        """Test reservation expiration workflow"""
        # Create expired reservation
        past_time = timezone.now() - timedelta(minutes=30)
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=2,
            status=Reservation.Status.PENDING,
            expires_at=past_time,
        )

        # Execute expiration task
        result = expire_reservation(str(reservation.id))

        # Verify expiration
        self.assertEqual(result["status"], "expired")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)

        # Verify table is available again (no active reservation)
        active_reservations = Reservation.objects.filter(
            table=self.table,
            reservation_date=reservation.reservation_date,
            reservation_time=reservation.reservation_time,
            status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED],
        )
        self.assertEqual(active_reservations.count(), 0)