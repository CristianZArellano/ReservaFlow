"""
Test factories for creating test data
"""
import factory
import random
from datetime import time, timedelta
from django.utils import timezone

from restaurants.models import Restaurant, Table
from customers.models import Customer
from reservations.models import Reservation


class RestaurantFactory(factory.django.DjangoModelFactory):
    """Factory for Restaurant model"""
    
    class Meta:
        model = Restaurant
    
    name = factory.Sequence(lambda n: f"Restaurant {n}")
    description = factory.Faker('text', max_nb_chars=200)
    address = factory.Faker('address')
    phone = factory.LazyAttribute(lambda _: f"+{random.randint(1,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}")
    email = factory.Faker('email')
    opening_time = time(9, 0)
    closing_time = time(22, 0)
    reservation_duration = 120
    advance_booking_days = 30
    is_active = True


class TableFactory(factory.django.DjangoModelFactory):
    """Factory for Table model"""
    
    class Meta:
        model = Table
    
    restaurant = factory.SubFactory(RestaurantFactory)
    number = factory.Sequence(lambda n: f"{n}")
    capacity = factory.Faker('random_int', min=2, max=8)
    location = factory.Faker('random_element', elements=['indoor', 'outdoor', 'bar'])
    is_active = True


class CustomerFactory(factory.django.DjangoModelFactory):
    """Factory for Customer model"""
    
    class Meta:
        model = Customer
    
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    phone = factory.LazyAttribute(lambda _: f"+{random.randint(1,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}")


class ReservationFactory(factory.django.DjangoModelFactory):
    """Factory for Reservation model"""
    
    class Meta:
        model = Reservation
    
    restaurant = factory.SubFactory(RestaurantFactory)
    customer = factory.SubFactory(CustomerFactory)
    table = factory.SubFactory(TableFactory)
    reservation_date = factory.LazyFunction(lambda: timezone.now().date() + timedelta(days=1))
    reservation_time = factory.Faker('random_element', elements=[
        time(10, 0), time(12, 0), time(14, 0), time(16, 0), time(18, 0), time(19, 0), time(20, 0), time(21, 0)
    ])
    party_size = factory.LazyAttribute(lambda obj: random.randint(1, obj.table.capacity))
    status = Reservation.Status.PENDING
    
    @factory.post_generation
    def set_expires_at(obj, create, extracted, **kwargs):
        """Set expires_at for pending reservations"""
        if create and obj.status == Reservation.Status.PENDING:
            obj.expires_at = timezone.now() + timedelta(minutes=15)
            obj.save(update_fields=['expires_at'])


class ConfirmedReservationFactory(ReservationFactory):
    """Factory for confirmed reservations"""
    status = Reservation.Status.CONFIRMED
    expires_at = None


class ExpiredReservationFactory(ReservationFactory):
    """Factory for expired reservations"""
    status = Reservation.Status.EXPIRED
    expires_at = factory.LazyFunction(lambda: timezone.now() - timedelta(minutes=30))


class CancelledReservationFactory(ReservationFactory):
    """Factory for cancelled reservations"""
    status = Reservation.Status.CANCELLED
    expires_at = None