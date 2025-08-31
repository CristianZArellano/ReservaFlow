#!/usr/bin/env python
"""
Script para probar la configuración de email
"""
import os
import sys
import django

# Setup Django
sys.path.append('/home/mackroph/Projects/django/ReservaFlow/restaurant-reservations')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email_configuration():
    print("📧 Probando configuración de email...\n")
    
    print("🔧 Configuración actual:")
    print(f"   EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"   EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'No configurado')}")
    print(f"   EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'No configurado')}")
    print(f"   EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'No configurado')}")
    print(f"   EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'No configurado')}")
    print(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    # Determinar tipo de backend
    if 'console' in settings.EMAIL_BACKEND.lower():
        print("✅ Backend de consola detectado - Los emails se mostrarán aquí")
        backend_type = "console"
    elif 'smtp' in settings.EMAIL_BACKEND.lower():
        print("📨 Backend SMTP detectado - Se intentará envío real")
        backend_type = "smtp"
    else:
        print("⚠️ Backend desconocido")
        backend_type = "unknown"
    
    print("\n📤 Enviando email de prueba...")
    
    try:
        result = send_mail(
            subject='Prueba de configuración - ReservaFlow',
            message=(
                'Este es un email de prueba del sistema ReservaFlow.\n\n'
                'Si recibes este mensaje, la configuración de email está funcionando correctamente.\n\n'
                f'Backend utilizado: {settings.EMAIL_BACKEND}\n'
                f'Enviado desde: {settings.DEFAULT_FROM_EMAIL}'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['test@example.com'],
            fail_silently=False,
        )
        
        if backend_type == "console":
            print("✅ Email enviado exitosamente (mostrado arriba en consola)")
        else:
            print(f"✅ Email enviado exitosamente. Resultado: {result}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error enviando email: {str(e)}")
        
        if backend_type == "smtp":
            print("\n🔍 Posibles soluciones:")
            print("   1. Verificar credenciales EMAIL_HOST_USER y EMAIL_HOST_PASSWORD")
            print("   2. Verificar que EMAIL_HOST y EMAIL_PORT son correctos")
            print("   3. Para Gmail, usar contraseña de aplicación en lugar de contraseña normal")
            print("   4. Verificar configuración de firewall/red")
            
        return False

def show_email_setup_guide():
    print("\n" + "="*60)
    print("📋 GUÍA DE CONFIGURACIÓN DE EMAIL")
    print("="*60)
    print()
    print("Para configurar email en producción, edita tu archivo .env:")
    print()
    print("🔸 Para Gmail:")
    print("   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend")
    print("   EMAIL_HOST=smtp.gmail.com")
    print("   EMAIL_PORT=587")
    print("   EMAIL_USE_TLS=True")
    print("   EMAIL_HOST_USER=tu_email@gmail.com")
    print("   EMAIL_HOST_PASSWORD=tu_contraseña_de_aplicación")
    print("   DEFAULT_FROM_EMAIL=ReservaFlow <tu_email@gmail.com>")
    print()
    print("🔸 Para SendGrid:")
    print("   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend")
    print("   EMAIL_HOST=smtp.sendgrid.net")
    print("   EMAIL_PORT=587")
    print("   EMAIL_USE_TLS=True")
    print("   EMAIL_HOST_USER=apikey")
    print("   EMAIL_HOST_PASSWORD=tu_api_key_de_sendgrid")
    print("   DEFAULT_FROM_EMAIL=ReservaFlow <noreply@tudominio.com>")
    print()
    print("📝 Notas importantes:")
    print("   - Para Gmail necesitas habilitar autenticación de dos factores")
    print("   - Usa contraseñas de aplicación, no tu contraseña normal")
    print("   - SendGrid y Mailgun son más confiables para producción")
    print("   - El backend de consola es perfecto para desarrollo")

if __name__ == "__main__":
    success = test_email_configuration()
    show_email_setup_guide()
    
    print("\n" + "="*60)
    if success:
        print("✅ CONFIGURACIÓN DE EMAIL FUNCIONANDO")
    else:
        print("❌ CONFIGURACIÓN DE EMAIL NECESITA AJUSTES")
    print("="*60)
    
    sys.exit(0 if success else 1)