# tests/notifications/test_notification_tasks.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone

from notifications.tasks import (
    send_notification_task,
    process_notification_queue,
    send_bulk_notifications,
    cleanup_old_notifications,
    generate_notification_report,
)
from notifications.models import Notification
from tests.fixtures.factories import CustomerFactory


class TestNotificationTasks(TestCase):
    """Tests for notification Celery tasks"""

    def setUp(self):
        """Set up test data"""
        self.customer = CustomerFactory(email="test@example.com", phone="+1234567890")

    @patch("notifications.tasks.EmailMultiAlternatives")
    def test_send_notification_email_success(self, mock_email):
        """Test successful email notification sending"""
        # Create email notification
        notification = Notification.objects.create(
            customer=self.customer,
            type=Notification.Type.EMAIL,
            channel="email",
            subject="Test Email",
            message="This is a test email message",
            status=Notification.Status.PENDING,
        )

        # Mock email sending
        mock_instance = MagicMock()
        mock_email.return_value = mock_instance
        mock_instance.send.return_value = 1

        # Execute task
        result = send_notification_task(str(notification.id))

        # Verify result
        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["channel"], "email")
        mock_instance.send.assert_called_once()

        # Verify notification status updated
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.SENT)

    @patch("notifications.tasks.client")
    def test_send_notification_sms_success(self, mock_twilio_client):
        """Test successful SMS notification sending"""
        # Create SMS notification
        notification = Notification.objects.create(
            customer=self.customer,
            type=Notification.Type.SMS,
            channel="sms",
            message="This is a test SMS message",
            status=Notification.Status.PENDING,
        )

        # Mock SMS sending
        mock_message = MagicMock()
        mock_message.sid = "test-sid-123"
        mock_twilio_client.messages.create.return_value = mock_message

        # Execute task
        result = send_notification_task(str(notification.id))

        # Verify result
        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["channel"], "sms")
        mock_twilio_client.messages.create.assert_called_once()

        # Verify notification status updated
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.SENT)

    @patch("notifications.tasks.webpush")
    def test_send_notification_push_success(self, mock_webpush):
        """Test successful push notification sending"""
        # Create push notification
        notification = Notification.objects.create(
            customer=self.customer,
            type=Notification.Type.PUSH,
            channel="push",
            subject="Test Push",
            message="This is a test push notification",
            status=Notification.Status.PENDING,
        )

        # Mock push sending
        mock_webpush.send.return_value = True

        # Execute task
        result = send_notification_task(str(notification.id))

        # Verify result
        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["channel"], "push")

        # Verify notification status updated
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.SENT)

    def test_send_notification_not_found(self):
        """Test task with non-existent notification"""
        result = send_notification_task("non-existent-id")
        self.assertEqual(result["error"], "not_found")

    @patch("notifications.tasks.EmailMultiAlternatives")
    def test_send_notification_email_failure(self, mock_email):
        """Test email notification failure and retry"""
        import smtplib

        # Create email notification
        notification = Notification.objects.create(
            customer=self.customer,
            type=Notification.Type.EMAIL,
            channel="email",
            subject="Test Email",
            message="This is a test email message",
            status=Notification.Status.PENDING,
        )

        # Mock email failure
        mock_instance = MagicMock()
        mock_email.return_value = mock_instance
        mock_instance.send.side_effect = smtplib.SMTPServerDisconnected("Connection lost")

        # Execute task with mock retry
        with patch.object(
            send_notification_task, "retry"
        ) as mock_retry, patch.object(
            send_notification_task, "request", MagicMock(retries=0)
        ):
            try:
                send_notification_task(str(notification.id))
            except Exception:
                pass  # Expected retry exception

        # Verify retry was called
        mock_retry.assert_called_once()

    @patch("notifications.tasks.send_notification_task.delay")
    def test_process_notification_queue_success(self, mock_delay):
        """Test processing notification queue"""
        # Create pending notifications
        notifications = []
        for i in range(3):
            notification = Notification.objects.create(
                customer=self.customer,
                type=Notification.Type.EMAIL,
                channel="email",
                subject=f"Test Email {i}",
                message=f"Message {i}",
                status=Notification.Status.PENDING,
            )
            notifications.append(notification)

        # Execute task
        result = process_notification_queue()

        # Verify result
        self.assertEqual(result["processed"], 3)
        self.assertEqual(result["status"], "completed")
        
        # Verify tasks were queued
        self.assertEqual(mock_delay.call_count, 3)

    @patch("notifications.tasks.send_notification_task.delay")
    def test_send_bulk_notifications_success(self, mock_delay):
        """Test bulk notification sending"""
        # Create notifications for bulk sending
        notification_ids = []
        for i in range(5):
            notification = Notification.objects.create(
                customer=self.customer,
                type=Notification.Type.EMAIL,
                channel="email",
                subject=f"Bulk Email {i}",
                message=f"Bulk message {i}",
                status=Notification.Status.PENDING,
            )
            notification_ids.append(str(notification.id))

        # Execute task
        result = send_bulk_notifications(notification_ids)

        # Verify result
        self.assertEqual(result["total"], 5)
        self.assertEqual(result["queued"], 5)
        self.assertEqual(result["status"], "completed")
        
        # Verify all tasks were queued
        self.assertEqual(mock_delay.call_count, 5)

    def test_cleanup_old_notifications_success(self):
        """Test cleanup of old notifications"""
        # Create old notifications
        old_date = timezone.now() - timedelta(days=35)
        old_notifications = []
        for i in range(3):
            notification = Notification.objects.create(
                customer=self.customer,
                type=Notification.Type.EMAIL,
                channel="email",
                subject=f"Old Email {i}",
                message=f"Old message {i}",
                status=Notification.Status.SENT,
            )
            # Manually set old date
            Notification.objects.filter(id=notification.id).update(created_at=old_date)
            old_notifications.append(notification)

        # Create recent notifications
        recent_notification = Notification.objects.create(
            customer=self.customer,
            type=Notification.Type.EMAIL,
            channel="email",
            subject="Recent Email",
            message="Recent message",
            status=Notification.Status.SENT,
        )

        # Execute cleanup
        result = cleanup_old_notifications(days=30)

        # Verify result
        self.assertEqual(result["deleted"], 3)
        self.assertEqual(result["status"], "completed")

        # Verify old notifications deleted, recent kept
        self.assertFalse(
            Notification.objects.filter(
                id__in=[n.id for n in old_notifications]
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(id=recent_notification.id).exists()
        )

    def test_generate_notification_report_success(self):
        """Test notification report generation"""
        # Create various notifications
        statuses = [
            Notification.Status.PENDING,
            Notification.Status.SENT,
            Notification.Status.FAILED,
        ]
        channels = ["email", "sms", "push"]
        
        for status in statuses:
            for channel in channels:
                Notification.objects.create(
                    customer=self.customer,
                    type=Notification.Type.EMAIL,
                    channel=channel,
                    subject=f"{channel} notification",
                    message="Test message",
                    status=status,
                )

        # Execute report generation
        result = generate_notification_report()

        # Verify result structure
        self.assertIn("total_notifications", result)
        self.assertIn("by_status", result)
        self.assertIn("by_channel", result)
        self.assertIn("by_type", result)
        self.assertIn("success_rate", result)
        
        # Verify counts
        self.assertEqual(result["total_notifications"], 9)
        self.assertEqual(result["by_status"]["pending"], 3)
        self.assertEqual(result["by_status"]["sent"], 3)
        self.assertEqual(result["by_status"]["failed"], 3)
        
        # Verify channel counts
        for channel in channels:
            self.assertEqual(result["by_channel"][channel], 3)


@pytest.mark.integration
class TestNotificationTasksIntegration(TestCase):
    """Integration tests for notification tasks"""

    def setUp(self):
        """Set up test data"""
        self.customer = CustomerFactory(email="integration@test.com")

    @patch("notifications.tasks.EmailMultiAlternatives")
    def test_full_notification_workflow(self, mock_email):
        """Test complete notification workflow"""
        # Mock successful email sending
        mock_instance = MagicMock()
        mock_email.return_value = mock_instance
        mock_instance.send.return_value = 1

        # 1. Create notification
        notification = Notification.objects.create(
            customer=self.customer,
            type=Notification.Type.EMAIL,
            channel="email",
            subject="Integration Test",
            message="Integration test message",
            status=Notification.Status.PENDING,
        )

        initial_status = notification.status
        self.assertEqual(initial_status, Notification.Status.PENDING)

        # 2. Process notification
        result = send_notification_task(str(notification.id))

        # 3. Verify workflow completion
        self.assertEqual(result["status"], "sent")
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.SENT)
        self.assertIsNotNone(notification.sent_at)

    def test_bulk_processing_workflow(self):
        """Test bulk notification processing workflow"""
        # Create multiple pending notifications
        notifications = []
        for i in range(10):
            notification = Notification.objects.create(
                customer=self.customer,
                type=Notification.Type.EMAIL,
                channel="email",
                subject=f"Bulk Test {i}",
                message=f"Bulk message {i}",
                status=Notification.Status.PENDING,
            )
            notifications.append(notification)

        # Process queue
        with patch("notifications.tasks.send_notification_task.delay") as mock_delay:
            result = process_notification_queue()

        # Verify bulk processing
        self.assertEqual(result["processed"], 10)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(mock_delay.call_count, 10)

    def test_cleanup_and_reporting_workflow(self):
        """Test cleanup and reporting workflow"""
        # Create test notifications
        old_date = timezone.now() - timedelta(days=35)
        
        # Old notifications (should be cleaned)
        for i in range(5):
            notification = Notification.objects.create(
                customer=self.customer,
                type=Notification.Type.EMAIL,
                channel="email",
                subject=f"Old {i}",
                message="Old message",
                status=Notification.Status.SENT,
            )
            Notification.objects.filter(id=notification.id).update(created_at=old_date)

        # Recent notifications (should remain)
        for i in range(3):
            Notification.objects.create(
                customer=self.customer,
                type=Notification.Type.SMS,
                channel="sms",
                message=f"Recent {i}",
                status=Notification.Status.SENT,
            )

        # Generate report before cleanup
        before_report = generate_notification_report()
        self.assertEqual(before_report["total_notifications"], 8)

        # Perform cleanup
        cleanup_result = cleanup_old_notifications(days=30)
        self.assertEqual(cleanup_result["deleted"], 5)

        # Generate report after cleanup
        after_report = generate_notification_report()
        self.assertEqual(after_report["total_notifications"], 3)