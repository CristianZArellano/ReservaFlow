# customers/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Administrador para el modelo Customer"""
    
    list_display = [
        'full_name', 'email', 'phone', 'customer_score', 
        'total_reservations', 'cancelled_reservations', 
        'no_show_count', 'is_active', 'created_at'
    ]
    
    list_filter = [
        'is_active', 'customer_score', 'created_at', 'birth_date'
    ]
    
    search_fields = [
        'first_name', 'last_name', 'email', 'phone'
    ]
    
    readonly_fields = [
        'created_at', 'updated_at', 'total_reservations', 
        'cancelled_reservations', 'no_show_count', 'customer_score'
    ]
    
    fieldsets = (
        ('Información Personal', {
            'fields': (
                ('first_name', 'last_name'), 
                'email', 'phone', 'birth_date'
            )
        }),
        ('Preferencias y Alergias', {
            'fields': ('preferences', 'allergies'),
            'classes': ('collapse',)
        }),
        ('Estadísticas del Cliente', {
            'fields': (
                'customer_score', 'total_reservations', 
                'cancelled_reservations', 'no_show_count'
            ),
            'classes': ('collapse',)
        }),
        ('Estado y Fechas', {
            'fields': ('is_active', 'created_at', 'updated_at')
        })
    )
    
    actions = ['activate_customers', 'deactivate_customers', 'reset_customer_score']
    
    def full_name(self, obj):
        """Mostrar nombre completo"""
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = "Nombre Completo"
    full_name.admin_order_field = 'first_name'
    
    def activate_customers(self, request, queryset):
        """Activar clientes seleccionados"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} clientes activados.')
    activate_customers.short_description = "Activar clientes seleccionados"
    
    def deactivate_customers(self, request, queryset):
        """Desactivar clientes seleccionados"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} clientes desactivados.')
    deactivate_customers.short_description = "Desactivar clientes seleccionados"
    
    def reset_customer_score(self, request, queryset):
        """Resetear puntuación de clientes seleccionados"""
        updated = queryset.update(customer_score=0.0)
        self.message_user(request, f'Puntuación reseteada para {updated} clientes.')
    reset_customer_score.short_description = "Resetear puntuación de clientes"