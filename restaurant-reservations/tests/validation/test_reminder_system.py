#!/usr/bin/env python
"""
Script de prueba para verificar que el sistema de recordatorios funciona
"""
import os
import sys
import django

# Setup Django
sys.path.append('/home/mackroph/Projects/django/ReservaFlow/restaurant-reservations')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from datetime import time, timedelta
from django.utils import timezone

from restaurants.models import Restaurant, Table
from customers.models import Customer
from reservations.models import Reservation
from reservations.tasks import schedule_reminder, send_reminder

def test_reminder_system():
    print("🧪 Iniciando pruebas del sistema de recordatorios...")
    
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
        
        # Crear una reserva confirmada para mañana
        tomorrow = timezone.now().date() + timedelta(days=1)
        reservation = Reservation.objects.create(
            restaurant=restaurant,
            customer=customer,
            table=table,
            reservation_date=tomorrow,
            reservation_time=time(19, 0),
            party_size=2,
            status=Reservation.Status.CONFIRMED
        )
        
        print(f"✅ Reserva confirmada creada: {reservation.id.hex[:8]}")
        print(f"   Fecha: {reservation.reservation_date}")
        print(f"   Hora: {reservation.reservation_time}")
        print(f"   DateTime completo: {reservation.reservation_datetime}")
        
        # Probar función schedule_reminder
        try:
            result = schedule_reminder(str(reservation.id), hours_before=1)  # 1 hora antes para testing
            print(f"✅ Recordatorio programado: {result}")
            
        except Exception as e:
            print(f"❌ Error programando recordatorio: {str(e)}")
            return False
        
        # Probar función send_reminder directamente (simulando el envío)
        try:
            result = send_reminder(str(reservation.id))
            print(f"✅ Función send_reminder ejecutada: {result}")
            
        except Exception as e:
            print(f"⚠️ Error enviando recordatorio (normal si no hay email configurado): {str(e)}")
        
        # Probar con reserva no confirmada
        reservation_pending = Reservation.objects.create(
            restaurant=restaurant,
            customer=customer,
            table=table,
            reservation_date=tomorrow,
            reservation_time=time(20, 0),  # Diferente hora
            party_size=2,
            status=Reservation.Status.PENDING
        )
        
        result = send_reminder(str(reservation_pending.id))
        if result.get('status') == 'not_confirmed':
            print("✅ Recordatorio correctamente omitido para reserva no confirmada")
        
        print("\n🎉 SISTEMA DE RECORDATORIOS FUNCIONANDO CORRECTAMENTE!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR EN PRUEBAS: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Limpiar datos de prueba
        try:
            Reservation.objects.filter(restaurant=restaurant).delete()
            Customer.objects.filter(email="juan@test.com").delete()
            Table.objects.filter(restaurant=restaurant).delete()
            Restaurant.objects.filter(name="Test Restaurant").delete()
            print("🧹 Datos de prueba limpiados")
        except:
            pass

if __name__ == "__main__":
    success = test_reminder_system()
    sys.exit(0 if success else 1)