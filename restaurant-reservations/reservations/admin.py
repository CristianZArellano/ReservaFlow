# reservations/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """Administrador para el modelo Reservation"""
    
    list_display = [
        'id_short', 'customer_link', 'restaurant', 'table', 
        'reservation_datetime', 'party_size', 'status_badge', 
        'created_at', 'expires_at'
    ]
    
    list_filter = [
        'status', 'restaurant', 'reservation_date', 'created_at', 
        'table__location', 'party_size'
    ]
    
    search_fields = [
        'id', 'customer__first_name', 'customer__last_name', 
        'customer__email', 'restaurant__name', 'table__number'
    ]
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'expires_at'
    ]
    
    fieldsets = (
        ('Información de la Reserva', {
            'fields': (
                'id', 'customer', 'restaurant', 'table'
            )
        }),
        ('Fecha y Hora', {
            'fields': (
                ('reservation_date', 'reservation_time'),
                'party_size'
            )
        }),
        ('Estado y Timing', {
            'fields': (
                'status', 'expires_at'
            )
        }),
        ('Fechas del Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'confirm_reservations', 'cancel_reservations', 
        'complete_reservations', 'mark_no_show'
    ]
    
    date_hierarchy = 'reservation_date'
    
    def get_queryset(self, request):
        """Optimizar consultas con select_related"""
        return super().get_queryset(request).select_related(
            'customer', 'restaurant', 'table'
        )
    
    def id_short(self, obj):
        """Mostrar ID corto"""
        return str(obj.id)[:8] + "..."
    id_short.short_description = "ID"
    id_short.admin_order_field = 'id'
    
    def customer_link(self, obj):
        """Link al cliente"""
        url = reverse('admin:customers_customer_change', args=[obj.customer.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            f"{obj.customer.first_name} {obj.customer.last_name}"
        )
    customer_link.short_description = "Cliente"
    customer_link.admin_order_field = 'customer__first_name'
    
    def reservation_datetime(self, obj):
        """Mostrar fecha y hora de reserva"""
        return f"{obj.reservation_date} {obj.reservation_time}"
    reservation_datetime.short_description = "Fecha y Hora"
    reservation_datetime.admin_order_field = 'reservation_date'
    
    def status_badge(self, obj):
        """Mostrar estado con colores"""
        colors = {
            'pending': '#ffc107',     # amarillo
            'confirmed': '#28a745',   # verde
            'completed': '#007bff',   # azul
            'cancelled': '#dc3545',   # rojo
            'no_show': '#fd7e14',     # naranja
            'expired': '#6c757d',     # gris
        }
        color = colors.get(obj.status, '#6c757d')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Estado"
    status_badge.admin_order_field = 'status'
    
    def confirm_reservations(self, request, queryset):
        """Confirmar reservas seleccionadas"""
        updated = queryset.filter(status='pending').update(status='confirmed')
        self.message_user(request, f'{updated} reservas confirmadas.')
    confirm_reservations.short_description = "Confirmar reservas seleccionadas"
    
    def cancel_reservations(self, request, queryset):
        """Cancelar reservas seleccionadas"""
        updated = queryset.exclude(status__in=['cancelled', 'completed']).update(status='cancelled')
        self.message_user(request, f'{updated} reservas canceladas.')
    cancel_reservations.short_description = "Cancelar reservas seleccionadas"
    
    def complete_reservations(self, request, queryset):
        """Marcar reservas como completadas"""
        updated = queryset.filter(status='confirmed').update(status='completed')
        self.message_user(request, f'{updated} reservas marcadas como completadas.')
    complete_reservations.short_description = "Completar reservas seleccionadas"
    
    def mark_no_show(self, request, queryset):
        """Marcar como no show"""
        updated = queryset.filter(status='confirmed').update(status='no_show')
        self.message_user(request, f'{updated} reservas marcadas como no show.')
    mark_no_show.short_description = "Marcar como no show"