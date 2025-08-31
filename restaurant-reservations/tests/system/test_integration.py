# tests/system/test_integration.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.core.cache import cache

from reservations.models import Reservation
from reservations.tasks import (
    expire_reservation,
    send_confirmation_email,
    send_reminder,
    schedule_reminder,
)
from notifications.models import Notification
from notifications.tasks import (
    send_notification_task,
    process_notification_queue,
    cleanup_old_notifications,
)
from config.monitoring import TaskMonitor
from tests.fixtures.factories import (
    RestaurantFactory,
    TableFactory,
    CustomerFactory,
)


@pytest.mark.integration
class TestSystemIntegration(TransactionTestCase):
    """Comprehensive system integration tests"""

    def setUp(self):
        """Set up test data"""
        cache.clear()
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer = CustomerFactory(email="integration@test.com")

    def test_complete_reservation_lifecycle(self):
        """Test complete reservation lifecycle with all systems"""
        # 1. Create pending reservation
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=4,
            status=Reservation.Status.PENDING,
            expires_at=timezone.now() + timedelta(minutes=15),
        )

        # 2. Confirm reservation and send confirmation email
        reservation.status = Reservation.Status.CONFIRMED
        reservation.save()

        with patch("reservations.tasks.send_mail") as mock_send_mail:
            mock_send_mail.return_value = 1

            # Send confirmation email
            email_result = send_confirmation_email(str(reservation.id))
            self.assertEqual(email_result["status"], "email_sent")

            # Verify email was called correctly
            mock_send_mail.assert_called_once()
            call_args = mock_send_mail.call_args
            self.assertIn("Confirmación", call_args[1]["subject"])

        # 3. Schedule reminder
        with patch("reservations.tasks.send_reminder.apply_async") as mock_schedule:
            reminder_result = schedule_reminder(str(reservation.id), hours_before=2)
            self.assertEqual(reminder_result["status"], "reminder_scheduled")
            mock_schedule.assert_called_once()

        # 4. Simulate reminder execution
        with patch("reservations.tasks.send_mail") as mock_send_mail:
            mock_send_mail.return_value = 1
            
            reminder_send_result = send_reminder(str(reservation.id))
            self.assertEqual(reminder_send_result["status"], "reminder_sent")

        # 5. Verify final state
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)

    def test_reservation_expiration_workflow(self):
        """Test reservation expiration with system cleanup"""
        # 1. Create expired reservation
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

        # 2. Execute expiration task
        expire_result = expire_reservation(str(reservation.id))
        self.assertEqual(expire_result["status"], "expired")

        # 3. Verify table availability restored
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)

        # 4. Verify no active reservations for this slot
        active_reservations = Reservation.objects.filter(
            table=self.table,
            reservation_date=reservation.reservation_date,
            reservation_time=reservation.reservation_time,
            status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED],
        )
        self.assertEqual(active_reservations.count(), 0)

    def test_notification_system_integration(self):
        """Test notification system with monitoring integration"""
        # 1. Create notification
        notification = Notification.objects.create(
            customer=self.customer,
            type=Notification.Type.EMAIL,
            channel="email",
            subject="Integration Test",
            message="Integration test notification",
            status=Notification.Status.PENDING,
        )

        # 2. Process notification with monitoring
        with patch("notifications.tasks.EmailMultiAlternatives") as mock_email:
            mock_instance = MagicMock()
            mock_email.return_value = mock_instance
            mock_instance.send.return_value = 1

            # Send notification
            result = send_notification_task(str(notification.id))
            self.assertEqual(result["status"], "sent")

        # 3. Verify notification status
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.SENT)
        self.assertIsNotNone(notification.sent_at)

        # 4. Process notification queue
        with patch("notifications.tasks.send_notification_task.delay") as mock_delay:
            queue_result = process_notification_queue()
            # Should be 0 since we already processed the pending one
            self.assertEqual(queue_result["processed"], 0)

    def test_monitoring_integration(self):
        """Test task monitoring across different task types"""
        task_names = [
            "reservations.tasks.expire_reservation",
            "notifications.tasks.send_notification_task",
            "customers.tasks.update_customer_stats",
        ]

        # Simulate task executions with monitoring
        for i, task_name in enumerate(task_names):
            task_id = f"monitor-test-{i}"
            
            # Record task start
            TaskMonitor.record_task_start(task_id, task_name)
            
            # Simulate success or failure
            if i % 2 == 0:
                TaskMonitor.record_task_success(task_id, task_name)
            else:
                TaskMonitor.record_task_failure(task_id, task_name, f"Error {i}")

        # Verify monitoring data
        for task_name in task_names:
            metrics = TaskMonitor.get_task_metrics(task_name)
            self.assertEqual(metrics["total_runs"], 1)

        # Generate health report
        with patch("config.monitoring.TaskMonitor.get_all_monitored_tasks",
                  return_value=task_names):
            report = TaskMonitor.generate_health_report()
            self.assertEqual(report["total_tasks"], 3)

    def test_bulk_operations_integration(self):
        """Test bulk operations across multiple systems"""
        # 1. Create multiple reservations
        reservations = []
        for i in range(5):
            reservation = Reservation.objects.create(
                restaurant=self.restaurant,
                customer=self.customer,
                table=self.table,
                reservation_date=timezone.now().date() + timedelta(days=i+1),
                reservation_time=datetime.now().time(),
                party_size=2,
                status=Reservation.Status.CONFIRMED,
            )
            reservations.append(reservation)

        # 2. Create notifications for each reservation
        notifications = []
        for reservation in reservations:
            notification = Notification.objects.create(
                customer=self.customer,
                type=Notification.Type.EMAIL,
                channel="email",
                subject=f"Reservation {reservation.id}",
                message="Bulk test notification",
                status=Notification.Status.PENDING,
            )
            notifications.append(notification)

        # 3. Process all notifications
        with patch("notifications.tasks.send_notification_task.delay") as mock_delay:
            queue_result = process_notification_queue()
            self.assertEqual(queue_result["processed"], 5)
            self.assertEqual(mock_delay.call_count, 5)

        # 4. Send confirmation emails for all reservations
        with patch("reservations.tasks.send_mail") as mock_send_mail:
            mock_send_mail.return_value = 1
            
            email_results = []
            for reservation in reservations:
                result = send_confirmation_email(str(reservation.id))
                email_results.append(result)

            # Verify all emails sent
            self.assertEqual(len(email_results), 5)
            for result in email_results:
                self.assertEqual(result["status"], "email_sent")

    def test_error_handling_and_recovery(self):
        """Test system error handling and recovery mechanisms"""
        # 1. Create reservation for error testing
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=2,
            status=Reservation.Status.CONFIRMED,
        )

        # 2. Test email failure with retry
        with patch("reservations.tasks.send_mail") as mock_send_mail:
            import smtplib
            mock_send_mail.side_effect = smtplib.SMTPServerDisconnected("Connection lost")

            # Test retry mechanism
            with patch.object(
                send_confirmation_email, "retry"
            ) as mock_retry, patch.object(
                send_confirmation_email, "request", MagicMock(retries=0)
            ):
                try:
                    send_confirmation_email(str(reservation.id))
                except Exception:
                    pass  # Expected retry exception

                # Verify retry was attempted
                mock_retry.assert_called_once()

        # 3. Test task with non-existent reservation
        invalid_result = send_confirmation_email("non-existent-id")
        self.assertEqual(invalid_result["error"], "not_found")

        # 4. Test notification failure handling
        notification = Notification.objects.create(
            customer=self.customer,
            type=Notification.Type.EMAIL,
            channel="email",
            subject="Error Test",
            message="Error test notification",
            status=Notification.Status.PENDING,
        )

        with patch("notifications.tasks.EmailMultiAlternatives") as mock_email:
            import smtplib
            mock_instance = MagicMock()
            mock_email.return_value = mock_instance
            mock_instance.send.side_effect = smtplib.SMTPServerDisconnected()

            # Test notification retry
            with patch.object(
                send_notification_task, "retry"
            ) as mock_retry, patch.object(
                send_notification_task, "request", MagicMock(retries=0)
            ):
                try:
                    send_notification_task(str(notification.id))
                except Exception:
                    pass  # Expected retry exception

                mock_retry.assert_called_once()

    def test_performance_and_scalability(self):
        """Test system performance with large data sets"""
        # 1. Create large batch of reservations
        reservations = []
        for i in range(20):
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
            reservations.append(reservation)

        # 2. Batch expire reservations (simulate expired state)
        expired_count = 0
        for reservation in reservations[:10]:  # Expire first 10
            # Set them as expired
            reservation.expires_at = timezone.now() - timedelta(minutes=30)
            reservation.save()
            
            result = expire_reservation(str(reservation.id))
            if result["status"] == "expired":
                expired_count += 1

        self.assertEqual(expired_count, 10)

        # 3. Process remaining reservations
        confirmed_count = 0
        with patch("reservations.tasks.send_mail") as mock_send_mail:
            mock_send_mail.return_value = 1
            
            for reservation in reservations[10:]:  # Confirm remaining 10
                reservation.status = Reservation.Status.CONFIRMED
                reservation.save()
                
                result = send_confirmation_email(str(reservation.id))
                if result["status"] == "email_sent":
                    confirmed_count += 1

        self.assertEqual(confirmed_count, 10)

        # 4. Verify final states
        expired_reservations = Reservation.objects.filter(
            id__in=[r.id for r in reservations[:10]],
            status=Reservation.Status.EXPIRED
        ).count()
        
        confirmed_reservations = Reservation.objects.filter(
            id__in=[r.id for r in reservations[10:]],
            status=Reservation.Status.CONFIRMED
        ).count()

        self.assertEqual(expired_reservations, 10)
        self.assertEqual(confirmed_reservations, 10)

    def test_cleanup_operations(self):
        """Test system cleanup operations"""
        # 1. Create old notifications for cleanup
        old_date = timezone.now() - timedelta(days=35)
        old_notifications = []
        
        for i in range(5):
            notification = Notification.objects.create(
                customer=self.customer,
                type=Notification.Type.EMAIL,
                channel="email",
                subject=f"Old notification {i}",
                message="Old message",
                status=Notification.Status.SENT,
            )
            # Manually set old date
            Notification.objects.filter(id=notification.id).update(created_at=old_date)
            old_notifications.append(notification)

        # 2. Create recent notifications (should not be cleaned)
        recent_notifications = []
        for i in range(3):
            notification = Notification.objects.create(
                customer=self.customer,
                type=Notification.Type.EMAIL,
                channel="email",
                subject=f"Recent notification {i}",
                message="Recent message",
                status=Notification.Status.SENT,
            )
            recent_notifications.append(notification)

        # 3. Perform cleanup
        cleanup_result = cleanup_old_notifications(days=30)
        self.assertEqual(cleanup_result["deleted"], 5)

        # 4. Verify cleanup results
        remaining_old = Notification.objects.filter(
            id__in=[n.id for n in old_notifications]
        ).count()
        remaining_recent = Notification.objects.filter(
            id__in=[n.id for n in recent_notifications]
        ).count()

        self.assertEqual(remaining_old, 0)  # All old notifications deleted
        self.assertEqual(remaining_recent, 3)  # Recent notifications preserved


@pytest.mark.integration
class TestAsyncTaskIntegration(TestCase):
    """Test asynchronous task execution integration"""

    def setUp(self):
        """Set up test data"""
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer = CustomerFactory()

    def test_task_chaining(self):
        """Test task chaining and workflow coordination"""
        # Create reservation for task chaining test
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=datetime.now().time(),
            party_size=4,
            status=Reservation.Status.PENDING,
        )

        # Simulate task chain: confirm -> email -> schedule reminder
        with patch("reservations.tasks.send_mail") as mock_send_mail, \
             patch("reservations.tasks.send_reminder.apply_async") as mock_schedule:
            
            mock_send_mail.return_value = 1

            # 1. Confirm reservation
            reservation.status = Reservation.Status.CONFIRMED
            reservation.save()

            # 2. Send confirmation email
            email_result = send_confirmation_email(str(reservation.id))
            self.assertEqual(email_result["status"], "email_sent")

            # 3. Schedule reminder
            reminder_result = schedule_reminder(str(reservation.id))
            self.assertEqual(reminder_result["status"], "reminder_scheduled")

            # Verify chain execution
            mock_send_mail.assert_called_once()
            mock_schedule.assert_called_once()

    def test_parallel_task_execution(self):
        """Test parallel task execution for multiple operations"""
        # Create multiple reservations for parallel processing
        reservations = []
        for i in range(5):
            reservation = Reservation.objects.create(
                restaurant=self.restaurant,
                customer=self.customer,
                table=self.table,
                reservation_date=timezone.now().date() + timedelta(days=i+1),
                reservation_time=datetime.now().time(),
                party_size=2,
                status=Reservation.Status.CONFIRMED,
            )
            reservations.append(reservation)

        # Simulate parallel email sending
        with patch("reservations.tasks.send_mail") as mock_send_mail:
            mock_send_mail.return_value = 1
            
            # Process all reservations "in parallel" (simulated)
            results = []
            for reservation in reservations:
                result = send_confirmation_email(str(reservation.id))
                results.append(result)

            # Verify all tasks executed successfully
            self.assertEqual(len(results), 5)
            for result in results:
                self.assertEqual(result["status"], "email_sent")
            
            # Verify all emails sent
            self.assertEqual(mock_send_mail.call_count, 5)