# restaurants/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Restaurant, Table


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    """Administrador para el modelo Restaurant"""
    
    list_display = [
        'name', 'cuisine_type', 'price_range', 'phone', 'email', 
        'is_active', 'total_capacity', 'average_rating', 'created_at'
    ]
    
    list_filter = [
        'cuisine_type', 'price_range', 'is_active', 'accepts_walk_ins',
        'requires_deposit', 'created_at'
    ]
    
    search_fields = [
        'name', 'description', 'address', 'phone', 'email'
    ]
    
    readonly_fields = [
        'created_at', 'updated_at', 'total_reservations'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'address', 'phone', 'email', 'website')
        }),
        ('Configuración del Restaurante', {
            'fields': (
                'cuisine_type', 'price_range', 'min_party_size', 'max_party_size',
                'accepts_walk_ins', 'requires_deposit', 'cancellation_hours'
            )
        }),
        ('Horarios', {
            'fields': (
                ('opening_time', 'closing_time'),
                ('monday_open', 'tuesday_open', 'wednesday_open', 'thursday_open'),
                ('friday_open', 'saturday_open', 'sunday_open')
            ),
            'classes': ('collapse',)
        }),
        ('Configuración de Reservas', {
            'fields': (
                'reservation_duration', 'advance_booking_days'
            )
        }),
        ('Estadísticas', {
            'fields': (
                'total_capacity', 'total_reservations', 'average_rating'
            ),
            'classes': ('collapse',)
        }),
        ('Estado y Fechas', {
            'fields': ('is_active', 'created_at', 'updated_at')
        })
    )
    
    actions = ['activate_restaurants', 'deactivate_restaurants']
    
    def activate_restaurants(self, request, queryset):
        """Activar restaurantes seleccionados"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} restaurantes activados.')
    activate_restaurants.short_description = "Activar restaurantes seleccionados"
    
    def deactivate_restaurants(self, request, queryset):
        """Desactivar restaurantes seleccionados"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} restaurantes desactivados.')
    deactivate_restaurants.short_description = "Desactivar restaurantes seleccionados"


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    """Administrador para el modelo Table"""
    
    list_display = [
        'number', 'restaurant', 'capacity', 'location', 
        'is_active', 'is_accessible', 'has_view', 'shape'
    ]
    
    list_filter = [
        'restaurant', 'location', 'is_active', 'is_accessible', 
        'has_view', 'is_quiet', 'has_high_chairs', 'shape'
    ]
    
    search_fields = [
        'number', 'restaurant__name', 'special_notes'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('restaurant', 'number', 'capacity', 'min_capacity', 'location')
        }),
        ('Características', {
            'fields': (
                'shape', 'is_accessible', 'has_view', 'is_quiet', 
                'has_high_chairs', 'requires_special_request'
            )
        }),
        ('Notas', {
            'fields': ('special_notes',),
            'classes': ('collapse',)
        }),
        ('Estado y Fechas', {
            'fields': ('is_active', 'created_at', 'updated_at')
        })
    )
    
    actions = ['activate_tables', 'deactivate_tables']
    
    def activate_tables(self, request, queryset):
        """Activar mesas seleccionadas"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} mesas activadas.')
    activate_tables.short_description = "Activar mesas seleccionadas"
    
    def deactivate_tables(self, request, queryset):
        """Desactivar mesas seleccionadas"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} mesas desactivadas.')
    deactivate_tables.short_description = "Desactivar mesas seleccionadas"
    
    def get_queryset(self, request):
        """Optimizar consultas con select_related"""
        return super().get_queryset(request).select_related('restaurant')


# Configuración adicional del admin
admin.site.site_header = "ReservaFlow Administración"
admin.site.site_title = "ReservaFlow Admin"
admin.site.index_title = "Panel de Administración"