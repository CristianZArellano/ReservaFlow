from django.core.cache import cache


def get_table_availability_key(table_id, date, time_slot):
    """Crea una key única para cache de disponibilidad"""
    return f"table_availability:{table_id}:{date}:{time_slot}"


def cache_table_availability(table_id, date, time_slot, available=True):
    """Guarda en cache si una mesa está disponible"""
    key = get_table_availability_key(table_id, date, time_slot)
    cache.set(key, available, timeout=300)  # 5 minutos en cache


def is_table_available_cached(table_id, date, time_slot):
    """Verifica disponibilidad desde cache"""
    key = get_table_availability_key(table_id, date, time_slot)
    return cache.get(key)
