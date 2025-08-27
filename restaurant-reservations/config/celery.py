# restaurant-reservations/config/celery.py
import os

from celery import Celery

# Configurar Django settings para Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("restaurant_reservations")

# Usar string aquí significa que el worker no tiene que serializar
# el objeto de configuración para los procesos hijo.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Cargar tareas de todas las apps registradas de Django
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
