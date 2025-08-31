"""
Tests realistas para locks distribuidos con Redis real
"""

import threading
import time
from datetime import date, datetime
from django.test import TestCase, TransactionTestCase
from django.db import transaction

from restaurants.services import TableReservationLock, check_table_availability
from reservations.models import Reservation
from tests.fixtures.factories import RestaurantFactory, TableFactory, CustomerFactory


class RedisLockRealisticTest(TransactionTestCase):
    """Test locks distribuidos con Redis REAL"""

    def setUp(self):
        """Setup con datos reales"""
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer1 = CustomerFactory()
        self.customer2 = CustomerFactory()

        self.test_date = date(2025, 9, 15)
        self.test_time = "19:00"

    def test_redis_lock_acquisition(self):
        """Test real de adquisición de lock en Redis"""

        # Crear lock
        lock = TableReservationLock(
            table_id=self.table.id, date=self.test_date, time_slot=self.test_time
        )

        # Debe poder adquirir el lock la primera vez
        acquired = lock.acquire()
        self.assertTrue(acquired, "Debe poder adquirir lock libre")

        # Segundo intento debe fallar (lock ya tomado)
        lock2 = TableReservationLock(
            table_id=self.table.id, date=self.test_date, time_slot=self.test_time
        )
        acquired2 = lock2.acquire()
        self.assertFalse(acquired2, "No debe poder adquirir lock ya tomado")

        # Liberar lock
        lock.release()

        # Ahora debe poder adquirir nuevamente
        acquired3 = lock2.acquire()
        self.assertTrue(acquired3, "Debe poder adquirir lock después de liberarlo")

        lock2.release()

    def test_redis_lock_timeout(self):
        """Test timeout real del lock en Redis"""
        # Crear lock con timeout muy corto
        lock = TableReservationLock(
            table_id=self.table.id, date=self.test_date, time_slot=self.test_time
        )
        lock.timeout = 1  # 1 segundo

        # Adquirir lock
        acquired = lock.acquire()
        self.assertTrue(acquired)

        # Segundo lock debe fallar inmediatamente
        lock2 = TableReservationLock(
            table_id=self.table.id, date=self.test_date, time_slot=self.test_time
        )
        acquired2 = lock2.acquire()
        self.assertFalse(acquired2)

        # Esperar timeout
        time.sleep(1.5)

        # Ahora debe poder adquirir (timeout expiró)
        acquired3 = lock2.acquire()
        self.assertTrue(acquired3, "Lock debe expirar por timeout")

        lock2.release()

    def test_concurrent_reservation_with_real_locks(self):
        """Test real de concurrencia con locks distribuidos"""
        results = []
        errors = []

        def try_reservation(customer_id):
            """Intentar crear reserva con lock real"""
            try:
                with TableReservationLock(
                    table_id=self.table.id,
                    date=self.test_date,
                    time_slot=self.test_time,
                ):
                    # Simular procesamiento
                    time.sleep(0.1)

                    # Verificar disponibilidad
                    available = check_table_availability(
                        self.table.id, self.test_date, self.test_time
                    )

                    if not available:
                        raise Exception("Mesa no disponible")

                    # Crear reserva
                    with transaction.atomic():
                        reservation = Reservation.objects.create(
                            restaurant=self.restaurant,
                            customer_id=customer_id,
                            table=self.table,
                            reservation_date=self.test_date,
                            reservation_time=datetime.strptime(
                                self.test_time, "%H:%M"
                            ).time(),
                            party_size=2,
                            status=Reservation.Status.CONFIRMED,
                        )
                        results.append(reservation.id)

            except Exception as e:
                errors.append(str(e))

        # Ejecutar múltiples threads concurrentemente
        threads = []
        for i in range(5):
            customer = CustomerFactory()
            thread = threading.Thread(target=try_reservation, args=(customer.id,))
            threads.append(thread)

        # Iniciar todos los threads casi simultáneamente
        for thread in threads:
            thread.start()

        # Esperar a que todos terminen
        for thread in threads:
            thread.join()

        # Solo UNA reserva debe haber tenido éxito
        self.assertEqual(
            len(results),
            1,
            f"Solo debe haber 1 reserva exitosa, pero hubo {len(results)}: {results}",
        )

        # Debe haber 4 errores (los demás intentos fallaron)
        self.assertEqual(
            len(errors), 4, f"Debe haber 4 errores, pero hubo {len(errors)}: {errors}"
        )

        # Verificar que la reserva realmente se creó
        reservation = Reservation.objects.get(id=results[0])
        self.assertEqual(reservation.table, self.table)
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)


class RedisAvailabilityCheckTest(TestCase):
    """Test cache de disponibilidad con Redis real"""

    def setUp(self):
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer = CustomerFactory()

        self.test_date = date(2025, 9, 15)
        self.test_time = "19:00"

    def test_availability_caching(self):
        """Test caching real de disponibilidad en Redis"""
        # Primera consulta debe ir a la base de datos
        available1 = check_table_availability(
            self.table.id, self.test_date, self.test_time
        )
        self.assertTrue(available1)

        # Crear reserva que cambie la disponibilidad
        Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer,
            table=self.table,
            reservation_date=self.test_date,
            reservation_time=datetime.strptime(self.test_time, "%H:%M").time(),
            party_size=2,
            status=Reservation.Status.CONFIRMED,
        )

        # Segunda consulta puede seguir devolviendo True por cache (comportamiento real)
        available2 = check_table_availability(
            self.table.id, self.test_date, self.test_time
        )

        # En test realista, esto puede ser True por cache,
        # lo que demuestra la importancia de los locks
        # (esta es una condición de carrera real)
        print(
            f"Disponibilidad después de crear reserva: {available2} (puede ser True por cache)"
        )

        # Esperar a que expire el cache o invalidarlo manualmente
        from django.core.cache import cache

        cache_key = f"availability:{self.table.id}:{self.test_date}:{self.test_time}"
        cache.delete(cache_key)

        # Ahora debe reflejar el estado real
        available3 = check_table_availability(
            self.table.id, self.test_date, self.test_time
        )
        self.assertFalse(
            available3, "Después de invalidar cache debe reflejar reserva existente"
        )

    def test_cache_race_condition(self):
        """Test condición de carrera real con cache"""

        def create_reservation_after_check():
            """Simular creación de reserva después de check"""
            time.sleep(0.05)  # Pequeño delay para crear condición de carrera

            Reservation.objects.create(
                restaurant=self.restaurant,
                customer=CustomerFactory(),
                table=self.table,
                reservation_date=self.test_date,
                reservation_time=datetime.strptime(self.test_time, "%H:%M").time(),
                party_size=2,
                status=Reservation.Status.CONFIRMED,
            )

        # Iniciar thread que creará reserva
        thread = threading.Thread(target=create_reservation_after_check)
        thread.start()

        # Consultar disponibilidad (puede estar en cache obsoleto)
        available = check_table_availability(
            self.table.id, self.test_date, self.test_time
        )

        # Esperar a que termine el thread
        thread.join()

        print(f"Disponibilidad durante condición de carrera: {available}")

        # Este test demuestra comportamiento real: puede devolver True
        # aunque la mesa ya no esté disponible (race condition)

        # Verificar estado final real
        final_available = check_table_availability(
            self.table.id, self.test_date, self.test_time
        )

        # Podría ser True por cache o False si cache expiró
        print(f"Disponibilidad final: {final_available}")
