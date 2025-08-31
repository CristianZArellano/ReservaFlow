import os
import logging
from celery import Celery
from celery.signals import task_success, task_prerun, task_postrun, task_failure

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Configure logging
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery("reservaflow")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


# Debug task to test Celery functionality
@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery functionality"""
    logger.info("Request: {0!r}".format(self.request))
    return f"Debug task executed successfully: {self.request}"


# Custom task failure handler
@app.task(bind=True)
def task_failure_handler(self, task_id, error, traceback):
    """Handle task failures"""
    logger.error(
        f"Task {task_id} failed: {error}",
        extra={"task_id": task_id, "error": str(error), "traceback": traceback},
    )


# Task success handler
def task_success_handler(sender=None, headers=None, body=None, **kwargs):
    """Handle task success"""
    logger.info(f"Task {sender} completed successfully")


# Task prerun handler
def task_prerun_handler(
    sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds
):
    """Handle task prerun"""
    logger.debug(f"Task {task.name} [{task_id}] starting")


# Task postrun handler
def task_postrun_handler(
    sender=None,
    task_id=None,
    task=None,
    args=None,
    kwargs=None,
    retval=None,
    state=None,
    **kwds,
):
    """Handle task postrun"""
    logger.debug(f"Task {task.name} [{task_id}] finished with state: {state}")


# Task failure handler
def task_failure_handler_signal(
    sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds
):
    """Handle task failure"""
    logger.error(f"Task {sender.name} [{task_id}] failed: {exception}")


# Connect default signals
task_success.connect(task_success_handler)
task_prerun.connect(task_prerun_handler)
task_postrun.connect(task_postrun_handler)
task_failure.connect(task_failure_handler_signal)

# Import monitoring signals (they auto-connect via decorators)
try:
    import config.monitoring  # noqa: F401 - Import needed for signal registration

    logger.info("Task monitoring enabled")
except ImportError as e:
    logger.warning(f"Task monitoring not available: {e}")

if __name__ == "__main__":
    app.start()
