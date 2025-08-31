# notifications/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Notification, NotificationTemplate, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Administrador para el modelo Notification"""
    
    list_display = [
        'id_short', 'customer', 'type', 'channel', 
        'subject_short', 'status_badge', 'created_at', 'sent_at'
    ]
    
    list_filter = [
        'type', 'channel', 'status', 'created_at', 'sent_at'
    ]
    
    search_fields = [
        'id', 'customer__first_name', 'customer__last_name', 
        'customer__email', 'subject', 'message'
    ]
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'sent_at', 
        'delivered_at', 'read_at', 'retry_count'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'customer', 'type', 'channel')
        }),
        ('Contenido', {
            'fields': ('subject', 'message', 'metadata')
        }),
        ('Estado', {
            'fields': ('status', 'sent_at', 'delivered_at', 'read_at', 'retry_count')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['retry_failed_notifications', 'mark_as_sent']
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        return super().get_queryset(request).select_related('customer')
    
    def id_short(self, obj):
        """Mostrar ID corto"""
        return str(obj.id)[:8] + "..."
    id_short.short_description = "ID"
    
    def subject_short(self, obj):
        """Mostrar asunto corto"""
        if obj.subject:
            return obj.subject[:30] + "..." if len(obj.subject) > 30 else obj.subject
        return "-"
    subject_short.short_description = "Asunto"
    
    def status_badge(self, obj):
        """Mostrar estado con colores"""
        colors = {
            'pending': '#ffc107',
            'sent': '#28a745', 
            'failed': '#dc3545',
            'retry': '#fd7e14'
        }
        color = colors.get(obj.status, '#6c757d')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Estado"
    
    def retry_failed_notifications(self, request, queryset):
        """Reintentar notificaciones fallidas"""
        updated = queryset.filter(status='failed').update(status='pending')
        self.message_user(request, f'{updated} notificaciones marcadas para reintento.')
    retry_failed_notifications.short_description = "Reintentar notificaciones fallidas"
    
    def mark_as_sent(self, request, queryset):
        """Marcar como enviadas"""
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='sent', 
            sent_at=timezone.now()
        )
        self.message_user(request, f'{updated} notificaciones marcadas como enviadas.')
    mark_as_sent.short_description = "Marcar como enviadas"


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Administrador para plantillas de notificaciones"""
    
    list_display = [
        'name', 'type', 'channel', 'is_active', 
        'created_at', 'updated_at'
    ]
    
    list_filter = ['type', 'channel', 'is_active', 'created_at']
    
    search_fields = ['name', 'subject', 'template_content']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'type', 'channel', 'is_active')
        }),
        ('Contenido', {
            'fields': ('subject', 'template_content')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Administrador para preferencias de notificaciones"""
    
    list_display = [
        'customer', 'email_enabled', 'sms_enabled', 
        'push_enabled', 'created_at'
    ]
    
    list_filter = [
        'email_enabled', 'sms_enabled', 'push_enabled', 'created_at'
    ]
    
    search_fields = [
        'customer__first_name', 'customer__last_name', 'customer__email'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        return super().get_queryset(request).select_related('customer')