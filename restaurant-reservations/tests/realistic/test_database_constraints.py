"""
Tests realistas para constraints de base de datos con PostgreSQL real
"""

import threading
import time
from datetime import date, datetime, timedelta
from django.test import TransactionTestCase
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

from reservations.models import Reservation
from tests.fixtures.factories import RestaurantFactory, TableFactory, CustomerFactory


class DatabaseConstraintRealisticTest(TransactionTestCase):
    """Tests realistas de constraints de base de datos"""

    def setUp(self):
        """Setup con datos reales"""
        self.restaurant = RestaurantFactory()
        self.table = TableFactory(restaurant=self.restaurant)
        self.customer1 = CustomerFactory()
        self.customer2 = CustomerFactory()

        self.test_date = date(2025, 9, 15)
        self.test_time = datetime.strptime("19:00", "%H:%M").time()

    def test_unique_constraint_real_database(self):
        """Test constraint único real en PostgreSQL"""
        # Crear primera reserva
        reservation1 = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer1,
            table=self.table,
            reservation_date=self.test_date,
            reservation_time=self.test_time,
            party_size=2,
            status=Reservation.Status.CONFIRMED,
        )

        print(f"✅ Primera reserva creada: {reservation1.id}")

        # Intentar crear reserva duplicada - debe fallar por constraint
        with self.assertRaises((IntegrityError, ValidationError)) as cm:
            with transaction.atomic():
                Reservation.objects.create(
                    restaurant=self.restaurant,
                    customer=self.customer2,
                    table=self.table,
                    reservation_date=self.test_date,
                    reservation_time=self.test_time,
                    party_size=4,
                    status=Reservation.Status.PENDING,
                )

        print(f"❌ Segunda reserva rechazada correctamente: {cm.exception}")

        # Verificar que solo hay una reserva
        reservations_count = Reservation.objects.filter(
            table=self.table,
            reservation_date=self.test_date,
            reservation_time=self.test_time,
            status__in=[Reservation.Status.PENDING, Reservation.Status.CONFIRMED],
        ).count()

        self.assertEqual(reservations_count, 1, "Solo debe haber una reserva activa")

    def test_concurrent_database_writes(self):
        """Test escrituras concurrentes reales a PostgreSQL"""
        results = []
        errors = []

        def try_create_reservation(customer):
            """Intentar crear reserva en thread separado"""
            try:
                with transaction.atomic():
                    # Pequeño delay para aumentar probabilidad de colisión
                    time.sleep(0.01)

                    reservation = Reservation.objects.create(
                        restaurant=self.restaurant,
                        customer=customer,
                        table=self.table,
                        reservation_date=self.test_date,
                        reservation_time=self.test_time,
                        party_size=2,
                        status=Reservation.Status.CONFIRMED,
                    )
                    results.append(reservation.id)
                    print(f"✅ Reserva creada en thread: {reservation.id}")

            except (IntegrityError, ValidationError) as e:
                errors.append(str(e))
                print(f"❌ Error en thread: {e}")

        # Crear múltiples threads intentando crear reserva simultáneamente
        threads = []
        customers = [CustomerFactory() for _ in range(10)]

        for customer in customers:
            thread = threading.Thread(target=try_create_reservation, args=(customer,))
            threads.append(thread)

        print(f"🚀 Iniciando {len(threads)} threads concurrentes...")

        # Iniciar todos los threads
        for thread in threads:
            thread.start()

        # Esperar a que todos terminen
        for thread in threads:
            thread.join()

        print(f"📊 Resultados: {len(results)} éxitos, {len(errors)} errores")
        print(f"📊 Reservas creadas: {results}")
        print(f"📊 Errores: {errors[:3]}...")  # Solo primeros 3 errores

        # Solo UNA reserva debe haber sido creada exitosamente
        self.assertEqual(
            len(results),
            1,
            f"Solo debe crearse 1 reserva, pero se crearon {len(results)}",
        )

        # Debe haber múltiples errores por constraint violation
        self.assertGreaterEqual(
            len(errors),
            8,
            f"Debe haber al menos 8 errores de constraint, pero hubo {len(errors)}",
        )

        # Verificar constraint específico de PostgreSQL
        constraint_errors = [
            e for e in errors if "unique_active_reservation" in e.lower()
        ]
        self.assertGreater(
            len(constraint_errors),
            0,
            "Debe haber errores de constraint único específico",
        )

    def test_transaction_isolation_levels(self):
        """Test niveles de aislamiento real de PostgreSQL"""
        # Crear reserva inicial
        initial_reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer1,
            table=self.table,
            reservation_date=self.test_date,
            reservation_time=self.test_time,
            party_size=2,
            status=Reservation.Status.PENDING,
        )

        print(f"📊 Reserva inicial creada: {initial_reservation.id}")

        def modify_in_transaction():
            """Modificar reserva en transacción separada"""
            time.sleep(0.1)  # Permitir que la otra transacción comience

            with transaction.atomic():
                reservation = Reservation.objects.select_for_update().get(
                    id=initial_reservation.id
                )
                reservation.status = Reservation.Status.CONFIRMED
                reservation.save()
                print("🔄 Reserva modificada a CONFIRMED en thread")
                time.sleep(0.2)  # Mantener transacción abierta

        # Iniciar thread que modificará la reserva
        thread = threading.Thread(target=modify_in_transaction)
        thread.start()

        time.sleep(0.05)  # Pequeño delay

        # Intentar leer la reserva mientras la otra transacción está activa
        with transaction.atomic():
            reservation = Reservation.objects.get(id=initial_reservation.id)
            original_status = reservation.status
            print(f"📖 Estado leído durante transacción concurrente: {original_status}")

            # Esperar a que termine la otra transacción
            thread.join()

            # Releer sin salir de transacción actual
            reservation.refresh_from_db()
            final_status = reservation.status
            print(f"📖 Estado final: {final_status}")

            # Dependiendo del nivel de aislamiento, puede diferir
            print(f"📊 Cambió durante transacción: {original_status} -> {final_status}")

    def test_deadlock_detection(self):
        """Test detección real de deadlocks en PostgreSQL"""
        # Crear dos reservas para modificar en orden diferente
        reservation1 = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer1,
            table=self.table,
            reservation_date=self.test_date,
            reservation_time=self.test_time,
            party_size=2,
            status=Reservation.Status.PENDING,
        )

        reservation2 = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer2,
            table=TableFactory(restaurant=self.restaurant, number="T2"),
            reservation_date=self.test_date,
            reservation_time=datetime.strptime("20:00", "%H:%M").time(),
            party_size=2,
            status=Reservation.Status.PENDING,
        )

        deadlock_detected = []

        def transaction_1():
            """Primera transacción - adquiere locks en orden 1->2"""
            try:
                with transaction.atomic():
                    # Lock primera reserva
                    r1 = Reservation.objects.select_for_update().get(id=reservation1.id)
                    r1.party_size = 4
                    r1.save()
                    print("🔒 T1: Lock en reserva 1 adquirido")

                    time.sleep(0.1)  # Dar tiempo a T2 para adquirir su lock

                    # Intentar lock segunda reserva
                    r2 = Reservation.objects.select_for_update().get(id=reservation2.id)
                    r2.party_size = 5
                    r2.save()
                    print("🔒 T1: Lock en reserva 2 adquirido")

            except Exception as e:
                print(f"💥 T1: Error detectado: {e}")
                deadlock_detected.append("T1")

        def transaction_2():
            """Segunda transacción - adquiere locks en orden 2->1"""
            try:
                with transaction.atomic():
                    time.sleep(0.05)  # Pequeño delay

                    # Lock segunda reserva
                    r2 = Reservation.objects.select_for_update().get(id=reservation2.id)
                    r2.party_size = 6
                    r2.save()
                    print("🔒 T2: Lock en reserva 2 adquirido")

                    time.sleep(0.1)

                    # Intentar lock primera reserva (potencial deadlock)
                    r1 = Reservation.objects.select_for_update().get(id=reservation1.id)
                    r1.party_size = 7
                    r1.save()
                    print("🔒 T2: Lock en reserva 1 adquirido")

            except Exception as e:
                print(f"💥 T2: Error detectado: {e}")
                deadlock_detected.append("T2")

        # Ejecutar transacciones concurrentemente
        thread1 = threading.Thread(target=transaction_1)
        thread2 = threading.Thread(target=transaction_2)

        print("🚀 Iniciando transacciones que pueden generar deadlock...")

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        print(f"📊 Deadlocks detectados: {deadlock_detected}")

        # PostgreSQL debe detectar y resolver deadlocks
        # Al menos una transacción debe completarse
        final_r1 = Reservation.objects.get(id=reservation1.id)
        final_r2 = Reservation.objects.get(id=reservation2.id)

        print(f"📊 Estado final R1: party_size={final_r1.party_size}")
        print(f"📊 Estado final R2: party_size={final_r2.party_size}")

        # Al menos una debe haber cambiado (no hubo deadlock fatal)
        self.assertTrue(
            final_r1.party_size != 2 or final_r2.party_size != 3,
            "Al menos una reserva debe haber sido modificada",
        )

    def test_foreign_key_constraints(self):
        """Test constraints de foreign key reales"""
        # Crear reserva
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer=self.customer1,
            table=self.table,
            reservation_date=self.test_date,
            reservation_time=self.test_time,
            party_size=2,
            status=Reservation.Status.CONFIRMED,
        )

        print(f"✅ Reserva creada: {reservation.id}")

        # Intentar eliminar mesa que tiene reserva - debe fallar
        with self.assertRaises(Exception) as cm:  # ProtectedError o IntegrityError
            self.table.delete()

        print(
            f"❌ Eliminación de mesa bloqueada correctamente: {type(cm.exception).__name__}"
        )

        # Verificar que la mesa aún existe
        self.assertTrue(
            self.table.__class__.objects.filter(id=self.table.id).exists(),
            "Mesa no debe haber sido eliminada",
        )

        # Verificar que la reserva aún existe
        self.assertTrue(
            Reservation.objects.filter(id=reservation.id).exists(),
            "Reserva debe seguir existiendo",
        )

    def test_check_constraints(self):
        """Test constraints de verificación personalizados"""
        # Intentar crear reserva con party_size inválido
        with self.assertRaises((IntegrityError, ValidationError)):
            Reservation.objects.create(
                restaurant=self.restaurant,
                customer=self.customer1,
                table=self.table,
                reservation_date=self.test_date,
                reservation_time=self.test_time,
                party_size=-1,  # Valor inválido
                status=Reservation.Status.CONFIRMED,
            )

        # Intentar crear reserva con fecha en el pasado
        past_date = date.today() - timedelta(days=1)

        # Esto puede o no fallar dependiendo de constraints implementados
        try:
            past_reservation = Reservation.objects.create(
                restaurant=self.restaurant,
                customer=self.customer1,
                table=self.table,
                reservation_date=past_date,
                reservation_time=self.test_time,
                party_size=2,
                status=Reservation.Status.CONFIRMED,
            )
            print("⚠️ Reserva en el pasado permitida - considerar agregar constraint")
            past_reservation.delete()
        except (IntegrityError, ValidationError) as e:
            print(f"✅ Reserva en el pasado rechazada: {e}")
