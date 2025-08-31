# tests/monitoring/test_task_monitoring.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
from django.test import TestCase
from django.utils import timezone
from django.core.cache import cache

from config.monitoring import (
    TaskMonitor,
    TaskMetrics,
    task_prerun_handler,
    task_postrun_handler,
    task_failure_handler,
    task_success_handler,
)


class TestTaskMonitor(TestCase):
    """Tests for TaskMonitor class"""

    def setUp(self):
        """Set up test data"""
        cache.clear()
        self.task_id = "test-task-123"
        self.task_name = "test.task"

    def test_record_task_start(self):
        """Test recording task start"""
        start_time = timezone.now()
        
        with patch("config.monitoring.timezone.now", return_value=start_time):
            TaskMonitor.record_task_start(self.task_id, self.task_name)

        # Verify cache entries
        self.assertEqual(
            cache.get(f"task_start:{self.task_id}"), start_time.isoformat()
        )
        
        # Verify counter incremented
        counter_key = f"task_count:{self.task_name}"
        self.assertEqual(cache.get(counter_key, 0), 1)

    def test_record_task_success(self):
        """Test recording task success"""
        start_time = timezone.now()
        end_time = start_time + timedelta(seconds=5)
        
        # Set up start time
        cache.set(f"task_start:{self.task_id}", start_time.isoformat())
        
        with patch("config.monitoring.timezone.now", return_value=end_time):
            TaskMonitor.record_task_success(self.task_id, self.task_name)

        # Verify success counter
        success_key = f"task_success:{self.task_name}"
        self.assertEqual(cache.get(success_key, 0), 1)
        
        # Verify duration recorded
        duration_key = f"task_duration:{self.task_name}"
        durations = cache.get(duration_key, [])
        self.assertEqual(len(durations), 1)
        self.assertEqual(durations[0], 5.0)

    def test_record_task_failure(self):
        """Test recording task failure"""
        error_message = "Test error"
        
        TaskMonitor.record_task_failure(self.task_id, self.task_name, error_message)

        # Verify failure counter
        failure_key = f"task_failure:{self.task_name}"
        self.assertEqual(cache.get(failure_key, 0), 1)
        
        # Verify error logged
        error_key = f"task_errors:{self.task_name}"
        errors = cache.get(error_key, [])
        self.assertEqual(len(errors), 1)
        self.assertIn(error_message, errors[0])

    @patch("config.monitoring.logger")
    def test_check_task_health_healthy(self, mock_logger):
        """Test health check for healthy task"""
        # Set up healthy metrics
        cache.set(f"task_count:{self.task_name}", 10)
        cache.set(f"task_success:{self.task_name}", 9)
        cache.set(f"task_failure:{self.task_name}", 1)
        
        result = TaskMonitor.check_task_health(self.task_name)
        
        self.assertTrue(result)
        mock_logger.info.assert_called_once()

    @patch("config.monitoring.logger")
    def test_check_task_health_unhealthy(self, mock_logger):
        """Test health check for unhealthy task"""
        # Set up unhealthy metrics (high failure rate)
        cache.set(f"task_count:{self.task_name}", 10)
        cache.set(f"task_success:{self.task_name}", 3)
        cache.set(f"task_failure:{self.task_name}", 7)
        
        result = TaskMonitor.check_task_health(self.task_name)
        
        self.assertFalse(result)
        mock_logger.warning.assert_called_once()

    def test_get_task_metrics(self):
        """Test getting task metrics"""
        # Set up metrics
        cache.set(f"task_count:{self.task_name}", 15)
        cache.set(f"task_success:{self.task_name}", 12)
        cache.set(f"task_failure:{self.task_name}", 3)
        cache.set(f"task_duration:{self.task_name}", [1.5, 2.0, 1.8, 2.2])
        
        metrics = TaskMonitor.get_task_metrics(self.task_name)
        
        self.assertEqual(metrics["total_runs"], 15)
        self.assertEqual(metrics["successes"], 12)
        self.assertEqual(metrics["failures"], 3)
        self.assertEqual(metrics["success_rate"], 80.0)
        self.assertEqual(metrics["avg_duration"], 1.875)

    def test_get_task_metrics_no_data(self):
        """Test getting metrics with no data"""
        metrics = TaskMonitor.get_task_metrics("nonexistent.task")
        
        self.assertEqual(metrics["total_runs"], 0)
        self.assertEqual(metrics["successes"], 0)
        self.assertEqual(metrics["failures"], 0)
        self.assertEqual(metrics["success_rate"], 0.0)
        self.assertEqual(metrics["avg_duration"], 0.0)

    @patch("config.monitoring.logger")
    def test_generate_health_report(self, mock_logger):
        """Test generating health report"""
        # Set up multiple task metrics
        tasks = ["task.one", "task.two", "task.three"]
        for i, task_name in enumerate(tasks):
            cache.set(f"task_count:{task_name}", (i + 1) * 5)
            cache.set(f"task_success:{task_name}", (i + 1) * 4)
            cache.set(f"task_failure:{task_name}", (i + 1) * 1)
        
        with patch("config.monitoring.TaskMonitor.get_all_monitored_tasks", 
                  return_value=tasks):
            report = TaskMonitor.generate_health_report()
        
        self.assertIn("total_tasks", report)
        self.assertIn("healthy_tasks", report)
        self.assertIn("unhealthy_tasks", report)
        self.assertIn("task_metrics", report)
        
        self.assertEqual(report["total_tasks"], 3)
        self.assertEqual(len(report["task_metrics"]), 3)


class TestTaskMetrics(TestCase):
    """Tests for TaskMetrics class"""

    def setUp(self):
        """Set up test data"""
        cache.clear()
        self.task_name = "test.metrics.task"

    def test_increment_counter(self):
        """Test incrementing counter"""
        key = "test_counter"
        
        TaskMetrics.increment_counter(key)
        self.assertEqual(cache.get(key, 0), 1)
        
        TaskMetrics.increment_counter(key)
        self.assertEqual(cache.get(key, 0), 2)

    def test_record_duration(self):
        """Test recording duration"""
        key = "test_duration"
        duration = 2.5
        
        TaskMetrics.record_duration(key, duration)
        
        durations = cache.get(key, [])
        self.assertEqual(len(durations), 1)
        self.assertEqual(durations[0], duration)

    def test_record_duration_with_limit(self):
        """Test recording duration with limit"""
        key = "test_duration_limit"
        
        # Record more than limit
        for i in range(150):
            TaskMetrics.record_duration(key, float(i))
        
        durations = cache.get(key, [])
        self.assertEqual(len(durations), 100)  # Should be limited to 100
        # Should keep the most recent 100
        self.assertEqual(durations[0], 50.0)
        self.assertEqual(durations[-1], 149.0)

    def test_get_average_duration(self):
        """Test getting average duration"""
        key = "test_avg_duration"
        durations = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        cache.set(key, durations)
        
        avg = TaskMetrics.get_average_duration(key)
        self.assertEqual(avg, 3.0)

    def test_get_average_duration_empty(self):
        """Test getting average duration with no data"""
        avg = TaskMetrics.get_average_duration("nonexistent_key")
        self.assertEqual(avg, 0.0)

    def test_add_error_log(self):
        """Test adding error log"""
        key = "test_errors"
        error_msg = "Test error occurred"
        
        TaskMetrics.add_error_log(key, error_msg)
        
        errors = cache.get(key, [])
        self.assertEqual(len(errors), 1)
        self.assertIn(error_msg, errors[0])
        self.assertIn(timezone.now().date().isoformat(), errors[0])


class TestSignalHandlers(TestCase):
    """Tests for Celery signal handlers"""

    def setUp(self):
        """Set up test data"""
        cache.clear()
        self.task_id = "signal-test-123"
        self.task_name = "test.signal.task"

    @patch("config.monitoring.TaskMonitor.record_task_start")
    def test_task_prerun_handler(self, mock_record_start):
        """Test task prerun signal handler"""
        # Mock task object
        mock_task = MagicMock()
        mock_task.name = self.task_name
        
        # Call handler
        task_prerun_handler(
            sender=None,
            task_id=self.task_id,
            task=mock_task,
            args=[],
            kwargs={}
        )
        
        # Verify monitoring called
        mock_record_start.assert_called_once_with(self.task_id, self.task_name)

    @patch("config.monitoring.TaskMonitor.record_task_success")
    def test_task_postrun_handler_success(self, mock_record_success):
        """Test task postrun handler for successful task"""
        mock_task = MagicMock()
        mock_task.name = self.task_name
        
        task_postrun_handler(
            sender=None,
            task_id=self.task_id,
            task=mock_task,
            args=[],
            kwargs={},
            retval="success",
            state="SUCCESS"
        )
        
        mock_record_success.assert_called_once_with(self.task_id, self.task_name)

    @patch("config.monitoring.TaskMonitor.record_task_failure")
    def test_task_postrun_handler_failure(self, mock_record_failure):
        """Test task postrun handler for failed task"""
        mock_task = MagicMock()
        mock_task.name = self.task_name
        
        task_postrun_handler(
            sender=None,
            task_id=self.task_id,
            task=mock_task,
            args=[],
            kwargs={},
            retval=None,
            state="FAILURE"
        )
        
        mock_record_failure.assert_called_once_with(
            self.task_id, self.task_name, "Task failed with state: FAILURE"
        )

    @patch("config.monitoring.TaskMonitor.record_task_failure")
    def test_task_failure_handler(self, mock_record_failure):
        """Test task failure signal handler"""
        mock_sender = MagicMock()
        mock_sender.name = self.task_name
        exception = Exception("Test exception")
        
        task_failure_handler(
            sender=mock_sender,
            task_id=self.task_id,
            exception=exception,
            traceback=None,
            einfo=None
        )
        
        mock_record_failure.assert_called_once_with(
            self.task_id, self.task_name, "Test exception"
        )

    @patch("config.monitoring.TaskMonitor.record_task_success")
    def test_task_success_handler(self, mock_record_success):
        """Test task success signal handler"""
        mock_sender = MagicMock()
        mock_sender.name = self.task_name
        
        task_success_handler(
            sender=mock_sender,
            headers={},
            body={}
        )
        
        # Note: success handler uses sender.request.id if available
        # For this test, we'll check it was called
        self.assertTrue(mock_record_success.called)


@pytest.mark.integration
class TestMonitoringIntegration(TestCase):
    """Integration tests for monitoring system"""

    def setUp(self):
        """Set up test data"""
        cache.clear()
        self.task_name = "integration.test.task"

    def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow"""
        task_id = "integration-task-123"
        
        # 1. Task starts
        with patch("config.monitoring.timezone.now") as mock_now:
            start_time = timezone.now()
            mock_now.return_value = start_time
            
            TaskMonitor.record_task_start(task_id, self.task_name)
            
            # 2. Task runs for 3 seconds and succeeds
            end_time = start_time + timedelta(seconds=3)
            mock_now.return_value = end_time
            
            TaskMonitor.record_task_success(task_id, self.task_name)

        # 3. Verify metrics
        metrics = TaskMonitor.get_task_metrics(self.task_name)
        
        self.assertEqual(metrics["total_runs"], 1)
        self.assertEqual(metrics["successes"], 1)
        self.assertEqual(metrics["failures"], 0)
        self.assertEqual(metrics["success_rate"], 100.0)
        self.assertEqual(metrics["avg_duration"], 3.0)

    def test_multiple_task_runs_with_failures(self):
        """Test monitoring multiple task runs with some failures"""
        task_id_base = "multi-task"
        
        # Run 10 tasks: 7 successes, 3 failures
        for i in range(10):
            task_id = f"{task_id_base}-{i}"
            
            # Record start
            TaskMonitor.record_task_start(task_id, self.task_name)
            
            # 70% success rate
            if i < 7:
                TaskMonitor.record_task_success(task_id, self.task_name)
            else:
                TaskMonitor.record_task_failure(
                    task_id, self.task_name, f"Error in task {i}"
                )

        # Verify aggregated metrics
        metrics = TaskMonitor.get_task_metrics(self.task_name)
        
        self.assertEqual(metrics["total_runs"], 10)
        self.assertEqual(metrics["successes"], 7)
        self.assertEqual(metrics["failures"], 3)
        self.assertEqual(metrics["success_rate"], 70.0)

    @patch("config.monitoring.logger")
    def test_health_monitoring_workflow(self, mock_logger):
        """Test health monitoring workflow"""
        # Set up multiple tasks with different health status
        healthy_task = "healthy.task"
        unhealthy_task = "unhealthy.task"
        
        # Healthy task: 90% success rate
        cache.set(f"task_count:{healthy_task}", 100)
        cache.set(f"task_success:{healthy_task}", 90)
        cache.set(f"task_failure:{healthy_task}", 10)
        
        # Unhealthy task: 40% success rate
        cache.set(f"task_count:{unhealthy_task}", 50)
        cache.set(f"task_success:{unhealthy_task}", 20)
        cache.set(f"task_failure:{unhealthy_task}", 30)
        
        # Check individual health
        self.assertTrue(TaskMonitor.check_task_health(healthy_task))
        self.assertFalse(TaskMonitor.check_task_health(unhealthy_task))
        
        # Generate health report
        with patch("config.monitoring.TaskMonitor.get_all_monitored_tasks",
                  return_value=[healthy_task, unhealthy_task]):
            report = TaskMonitor.generate_health_report()
        
        self.assertEqual(report["total_tasks"], 2)
        self.assertEqual(report["healthy_tasks"], 1)
        self.assertEqual(report["unhealthy_tasks"], 1)