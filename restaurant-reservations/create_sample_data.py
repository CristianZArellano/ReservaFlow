#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from restaurants.models import Restaurant, Table
from customers.models import Customer  
from reservations.models import Reservation
from datetime import datetime, timedelta, time

def create_sample_data():
    print("🚀 Creando datos de prueba...")
    
    # Create test restaurants
    r1, created = Restaurant.objects.get_or_create(
        name="La Bella Italia",
        defaults={
            'description': "Auténtica cocina italiana en el corazón de la ciudad",
            'address': "Av. Principal 123, Centro",
            'phone': "+1234567890",
            'email': "info@bellaitalia.com",
            'cuisine_type': "italiana",
            'price_range': "$$",
            'opening_time': time(12, 0),
            'closing_time': time(23, 0)
        }
    )
    print(f"✅ Restaurante: {r1.name}")

    r2, created = Restaurant.objects.get_or_create(
        name="Sushi Zen",
        defaults={
            'description': "Sushi fresco y tradicional japonés",
            'address': "Calle Sakura 456, Zona Rosa",
            'phone': "+1234567891",
            'email': "contact@sushizen.com",
            'cuisine_type': "japonesa",
            'price_range': "$$$",
            'opening_time': time(18, 0),
            'closing_time': time(24, 0)
        }
    )
    print(f"✅ Restaurante: {r2.name}")

    r3, created = Restaurant.objects.get_or_create(
        name="Taco Loco",
        defaults={
            'description': "Los mejores tacos de la ciudad",
            'address': "Calle México 789, Barrio Latino",
            'phone': "+1234567892",
            'email': "hola@tacoloco.com",
            'cuisine_type': "mexicana",
            'price_range': "$",
            'opening_time': time(11, 0),
            'closing_time': time(22, 0)
        }
    )
    print(f"✅ Restaurante: {r3.name}")

    # Create test tables
    tables_data = [
        (r1, 1, 2, "Ventana", False, False),
        (r1, 2, 4, "Centro", True, False),
        (r1, 3, 6, "Terraza", True, True),
        (r2, 1, 4, "Barra", False, False),
        (r2, 2, 6, "Privado", False, True),
        (r2, 3, 8, "Salón Principal", True, False),
        (r3, 1, 2, "Ventana", False, False),
        (r3, 2, 4, "Centro", False, False),
        (r3, 3, 6, "Patio", True, True),
    ]

    for restaurant, number, capacity, location, has_view, is_accessible in tables_data:
        table, created = Table.objects.get_or_create(
            restaurant=restaurant,
            number=number,
            defaults={
                'capacity': capacity,
                'location': location,
                'has_view': has_view,
                'is_accessible': is_accessible
            }
        )
        if created:
            print(f"✅ Mesa: {restaurant.name} - Mesa {number}")

    # Create test customers
    customers_data = [
        ("Juan", "Pérez", "juan.perez@email.com", "+1234567892", "1985-05-15", None, None),
        ("María", "González", "maria.gonzalez@email.com", "+1234567893", "1990-03-20", "Vegetariana", None),
        ("Carlos", "López", "carlos.lopez@email.com", "+1234567894", "1988-12-10", None, "Alérgico a mariscos"),
        ("Ana", "Martín", "ana.martin@email.com", "+1234567895", "1995-07-25", "Vegana", None),
        ("Pedro", "García", "pedro.garcia@email.com", "+1234567896", "1982-11-30", None, "Prefiere mesa silenciosa"),
    ]

    for first_name, last_name, email, phone, dob, dietary, special in customers_data:
        customer, created = Customer.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'date_of_birth': dob,
                'dietary_preferences': dietary,
                'special_requests': special
            }
        )
        if created:
            print(f"✅ Cliente: {first_name} {last_name}")

    # Create test reservations
    customers = Customer.objects.all()
    tables = Table.objects.all()
    
    today = datetime.now().date()
    
    reservations_data = [
        (customers[0], tables[0], today + timedelta(days=1), "19:30:00", 2, "pending"),
        (customers[1], tables[1], today + timedelta(days=2), "20:00:00", 4, "confirmed"),
        (customers[2], tables[3], today + timedelta(days=3), "18:45:00", 4, "confirmed"),
        (customers[3], tables[2], today - timedelta(days=1), "19:00:00", 6, "completed"),
        (customers[4], tables[6], today, "12:30:00", 2, "cancelled"),
    ]

    for customer, table, date, time_str, party_size, status in reservations_data:
        reservation, created = Reservation.objects.get_or_create(
            customer=customer,
            table=table,
            reservation_date=date,
            reservation_time=time_str,
            defaults={
                'party_size': party_size,
                'status': status,
                'restaurant_id': table.restaurant_id
            }
        )
        if created:
            print(f"✅ Reserva: {customer.first_name} {customer.last_name} - {table.restaurant.name}")

    print("\n🎉 ¡Datos de prueba creados exitosamente!")
    print(f"📊 Restaurantes: {Restaurant.objects.count()}")
    print(f"🍽️  Mesas: {Table.objects.count()}")
    print(f"👥 Clientes: {Customer.objects.count()}")
    print(f"📅 Reservas: {Reservation.objects.count()}")

if __name__ == '__main__':
    create_sample_data()