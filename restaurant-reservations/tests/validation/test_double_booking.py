#!/usr/bin/env python
"""
Script de prueba simple para verificar que el sistema previene dobles reservas
"""
import os
import sys
import django

# Setup Django
sys.path.append('/home/mackroph/Projects/django/ReservaFlow/restaurant-reservations')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from datetime import date, time

from restaurants.models import Restaurant, Table
from customers.models import Customer
from reservations.models import Reservation

def test_double_booking_prevention():
    print("🧪 Iniciando pruebas de prevención de dobles reservas...")
    
    try:
        # Crear datos de prueba
        restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            address="Test Address",
            phone="123456789",
            email="test@test.com",
            opening_time=time(9, 0),
            closing_time=time(22, 0)
        )
        
        table = Table.objects.create(
            restaurant=restaurant,
            number="1",
            capacity=4
        )
        
        customer = Customer.objects.create(
            first_name="Juan",
            last_name="Pérez",
            email="juan@test.com",
            phone="123456789"
        )
        
        print("✅ Datos de prueba creados")
        
        # Crear primera reserva
        reservation1 = Reservation.objects.create(
            restaurant=restaurant,
            customer=customer,
            table=table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            party_size=2
        )
        
        print(f"✅ Primera reserva creada: {reservation1.id.hex[:8]}")
        
        # Intentar crear segunda reserva para la misma mesa/fecha/hora
        try:
            with transaction.atomic():
                reservation2 = Reservation.objects.create(
                    restaurant=restaurant,
                    customer=customer,
                    table=table,
                    reservation_date=date(2025, 9, 15),
                    reservation_time=time(19, 0),
                    party_size=3
                )
            print("❌ ERROR: Se permitió crear reserva duplicada!")
            return False
            
        except (ValidationError, IntegrityError) as e:
            print(f"✅ Doble reserva bloqueada correctamente: {str(e)[:100]}...")
        
        # Probar reserva en horario diferente (debe funcionar)
        reservation3 = Reservation.objects.create(
            restaurant=restaurant,
            customer=customer,
            table=table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(20, 0),  # Hora diferente
            party_size=2
        )
        print(f"✅ Reserva en horario diferente permitida: {reservation3.id.hex[:8]}")
        
        # Probar cambiar estado de la primera reserva a cancelada
        reservation1.status = Reservation.Status.CANCELLED
        reservation1.save()
        print("✅ Primera reserva cancelada")
        
        # Ahora debería poder crear reserva en el mismo horario
        reservation4 = Reservation.objects.create(
            restaurant=restaurant,
            customer=customer,
            table=table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),  # Mismo horario que la cancelada
            party_size=4
        )
        print(f"✅ Nueva reserva después de cancelación permitida: {reservation4.id.hex[:8]}")
        
        print("\n🎉 TODAS LAS PRUEBAS PASARON - Sistema de prevención de dobles reservas funcionando correctamente!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR EN PRUEBAS: {str(e)}")
        return False
    
    finally:
        # Limpiar datos de prueba
        Reservation.objects.filter(restaurant=restaurant).delete()
        Customer.objects.filter(email="juan@test.com").delete()
        Table.objects.filter(restaurant=restaurant).delete()
        Restaurant.objects.filter(name="Test Restaurant").delete()
        print("🧹 Datos de prueba limpiados")

if __name__ == "__main__":
    success = test_double_booking_prevention()
    sys.exit(0 if success else 1)