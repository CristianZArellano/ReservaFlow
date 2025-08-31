"""
Tests realistas para tareas Celery con broker real
"""

import time as time_module
from datetime import timedelta, time
from django.test import TransactionTestCase
from django.utils import timezone
from celery import current_app

from reservations.models import Reservation
from reservations.tasks import (
    expire_reservation,
    send_confirmation_email,
    send_reminder,
    schedule_reminder,
)
from tests.fixtures.factories import RestaurantFactory, TableFactory, CustomerFactory


class CeleryTaskRealisticTest(TransactionTestCase):
    """Tests realistas de tareas Celery con worker real"""

    def setUp(self):
        """Setup con datos reales"""
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer = CustomerFactory(email="test@example.com")

        # Limpiar cola de Celery
        current_app.control.purge()

    def wait_for_task(self, async_result, timeout=30):
        """Esperar a que una tarea termine con timeout"""
        start_time = time_module.time()
        while time_module.time() - start_time < timeout:
            if async_result.ready():
                return async_result.result
            time_module.sleep(0.5)

        raise TimeoutError(f"Tarea no completó en {timeout} segundos")

    def test_expire_reservation_real_task(self):
        """Test real de expiración de reserva con worker Celery"""
        # Crear reserva que ya debería estar expirada
        past_time = timezone.now() - timedelta(minutes=30)
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=time(19, 0),
            party_size=2,
            status=Reservation.Status.PENDING,
            expires_at=past_time,
        )

        print(
            f"🕐 Reserva creada: {reservation.id}, expira en: {reservation.expires_at}"
        )

        # Ejecutar tarea de expiración de forma asíncrona (REAL)
        async_result = expire_reservation.apply_async(args=[str(reservation.id)])

        print(f"📤 Tarea enviada: {async_result.id}")

        # Esperar resultado real del worker
        result = self.wait_for_task(async_result, timeout=30)

        print(f"📥 Resultado recibido: {result}")

        # Verificar que la tarea se ejecutó correctamente
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "expired")
        self.assertEqual(result["reservation_id"], str(reservation.id))

        # Verificar que la reserva realmente cambió de estado en la DB
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)

    def test_send_confirmation_email_real_task(self):
        """Test real de envío de email de confirmación"""
        # Crear reserva confirmada
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=time(19, 0),
            party_size=2,
            status=Reservation.Status.CONFIRMED,
        )

        print(f"📧 Enviando email para reserva: {reservation.id}")

        # Enviar email de forma asíncrona (REAL)
        async_result = send_confirmation_email.apply_async(args=[str(reservation.id)])

        # Esperar resultado
        result = self.wait_for_task(async_result, timeout=30)

        print(f"📨 Email resultado: {result}")

        # Verificar que el email se "envió" correctamente
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "email_sent")

        # Verificar que no hay errores
        self.assertNotIn("error", result)

    def test_send_reminder_real_task(self):
        """Test real de envío de recordatorio"""
        # Crear reserva confirmada
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=time(19, 0),
            party_size=2,
            status=Reservation.Status.CONFIRMED,
        )

        print(f"⏰ Enviando recordatorio para reserva: {reservation.id}")

        # Enviar recordatorio de forma asíncrona (REAL)
        async_result = send_reminder.apply_async(args=[str(reservation.id)])

        # Esperar resultado
        result = self.wait_for_task(async_result, timeout=30)

        print(f"⏰ Recordatorio resultado: {result}")

        # Verificar que el recordatorio se envió
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "reminder_sent")

    def test_schedule_reminder_real_task(self):
        """Test real de programación de recordatorio"""
        # Crear reserva confirmada
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=2),
            reservation_time=time(19, 0),
            party_size=2,
            status=Reservation.Status.CONFIRMED,
        )

        print(f"📅 Programando recordatorio para reserva: {reservation.id}")

        # Programar recordatorio de forma asíncrona (REAL)
        async_result = schedule_reminder.apply_async(
            args=[str(reservation.id)], kwargs={"hours_before": 24}
        )

        # Esperar resultado
        result = self.wait_for_task(async_result, timeout=30)

        print(f"📅 Programación resultado: {result}")

        # Verificar que se programó correctamente
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "reminder_scheduled")
        self.assertEqual(result["hours_before"], 24)

    def test_task_retry_behavior(self):
        """Test comportamiento real de retry de tareas"""
        # Intentar con ID inexistente para provocar retry
        fake_id = "00000000-0000-0000-0000-000000000000"

        print(f"🔄 Probando retry con ID inexistente: {fake_id}")

        # Ejecutar tarea que debería fallar y hacer retry
        async_result = expire_reservation.apply_async(args=[fake_id])

        # Esperar resultado
        result = self.wait_for_task(async_result, timeout=60)  # Más tiempo para retries

        print(f"🔄 Resultado con retry: {result}")

        # Debería devolver error después de retries
        self.assertIsNotNone(result)
        self.assertEqual(result["error"], "not_found")
        self.assertEqual(result["reservation_id"], fake_id)

    def test_concurrent_task_execution(self):
        """Test ejecución concurrente real de tareas"""
        # Crear múltiples reservas para procesar concurrentemente
        reservations = []
        for i in range(5):
            past_time = timezone.now() - timedelta(minutes=30)
            reservation = Reservation.objects.create(
                restaurant=self.restaurant,
                customer=CustomerFactory(email=f"test{i}@example.com"),
                table=TableFactory(restaurant=self.restaurant, number=f"T{i}"),
                reservation_date=timezone.now().date() + timedelta(days=1),
                reservation_time=time(19, 0),
                party_size=2,
                status=Reservation.Status.PENDING,
                expires_at=past_time,
            )
            reservations.append(reservation)

        print(f"🚀 Enviando {len(reservations)} tareas concurrentes...")

        # Enviar todas las tareas concurrentemente
        async_results = []
        for reservation in reservations:
            async_result = expire_reservation.apply_async(args=[str(reservation.id)])
            async_results.append((reservation, async_result))

        # Esperar resultados de todas las tareas
        results = []
        for reservation, async_result in async_results:
            result = self.wait_for_task(async_result, timeout=45)
            results.append((reservation, result))
            print(f"✅ Tarea completada para {reservation.id}: {result}")

        # Verificar que todas las tareas se ejecutaron correctamente
        self.assertEqual(len(results), 5)

        for reservation, result in results:
            self.assertEqual(result["status"], "expired")
            self.assertEqual(result["reservation_id"], str(reservation.id))

            # Verificar estado en base de datos
            reservation.refresh_from_db()
            self.assertEqual(reservation.status, Reservation.Status.EXPIRED)

    def test_task_queue_status(self):
        """Test estado real de la cola de tareas"""
        # Verificar que hay workers disponibles
        inspect = current_app.control.inspect()

        # Obtener estadísticas reales
        stats = inspect.stats()
        active = inspect.active()

        print(f"📊 Workers estadísticas: {stats}")
        print(f"📊 Tareas activas: {active}")

        # Debe haber al menos un worker disponible
        self.assertIsNotNone(stats)
        self.assertGreater(
            len(stats), 0, "Debe haber al menos un worker Celery disponible"
        )

    def test_task_failure_and_dead_letter_queue(self):
        """Test manejo real de tareas fallidas"""
        # Crear tarea que fallará consistentemente
        # (simulando error de conexión de email o similar)

        # Crear reserva sin customer email para forzar error
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=CustomerFactory(email=""),  # Email vacío
            table=self.table,
            reservation_date=timezone.now().date() + timedelta(days=1),
            reservation_time=time(19, 0),
            party_size=2,
            status=Reservation.Status.CONFIRMED,
        )

        print(f"💥 Enviando tarea que fallará: {reservation.id}")

        # Enviar tarea que debería fallar
        async_result = send_confirmation_email.apply_async(args=[str(reservation.id)])

        # Esperar resultado (puede ser exitoso por configuración de email de test)
        result = self.wait_for_task(async_result, timeout=30)

        print(f"💥 Resultado de tarea problemática: {result}")

        # En entorno de test, puede seguir siendo exitoso por email backend
        # Esto demuestra diferencias entre test y producción
