# 📧 Configuración del Sistema de Emails - ReservaFlow

El sistema ReservaFlow envía automáticamente emails de confirmación y recordatorios de reservas. Esta guía te ayudará a configurar el sistema de emails.

## 🏃‍♂️ Configuración Rápida

### Para Desarrollo
```bash
# En tu archivo .env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=ReservaFlow <noreply@reservaflow.com>
```
Los emails se mostrarán en la consola en lugar de enviarse realmente.

### Para Producción (Gmail)
```bash
# En tu archivo .env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_email@gmail.com
EMAIL_HOST_PASSWORD=tu_contraseña_de_aplicación_gmail
DEFAULT_FROM_EMAIL=ReservaFlow <tu_email@gmail.com>
```

## 📋 Opciones de Configuración

### 1. 🖥️ Backend de Consola (Desarrollo)
**Ideal para:** Desarrollo y pruebas
**Ventajas:** No necesita configuración externa, emails visibles en logs
```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### 2. 📧 Gmail
**Ideal para:** Proyectos pequeños/medianos
**Ventajas:** Familiar, fácil de configurar
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_email@gmail.com
EMAIL_HOST_PASSWORD=contraseña_de_aplicación
DEFAULT_FROM_EMAIL=ReservaFlow <tu_email@gmail.com>
```

**📝 Pasos para Gmail:**
1. Habilitar autenticación de dos factores en tu cuenta Google
2. Generar contraseña de aplicación en https://myaccount.google.com/apppasswords
3. Usar la contraseña de aplicación (no tu contraseña normal)

### 3. 🚀 SendGrid (Recomendado para Producción)
**Ideal para:** Aplicaciones en producción
**Ventajas:** Confiable, estadísticas, sin límites de Gmail
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=tu_sendgrid_api_key
DEFAULT_FROM_EMAIL=ReservaFlow <noreply@tudominio.com>
```

**📝 Pasos para SendGrid:**
1. Registrarse en https://sendgrid.com
2. Crear API Key en Settings > API Keys
3. Verificar dominio emisor
4. Usar 'apikey' como usuario y tu API key como contraseña

### 4. 📮 Mailgun
**Ideal para:** Alternativa a SendGrid
**Ventajas:** Potente API, buen soporte
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=postmaster@mg.tudominio.com
EMAIL_HOST_PASSWORD=tu_mailgun_password
DEFAULT_FROM_EMAIL=ReservaFlow <noreply@tudominio.com>
```

### 5. ☁️ Amazon SES
**Ideal para:** Aplicaciones AWS, alto volumen
**Ventajas:** Muy económico, integración con AWS
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_aws_access_key_id
EMAIL_HOST_PASSWORD=tu_aws_secret_access_key
DEFAULT_FROM_EMAIL=ReservaFlow <noreply@tudominio.com>
```

## 🧪 Probar la Configuración

### Prueba Manual
```bash
# Ejecutar script de prueba
uv run python test_email_config.py
```

### Prueba con Reserva Real
```bash
# Crear reserva y confirmarla para disparar emails automáticos
uv run python test_full_reservation_flow.py
```

## 📊 Tipos de Emails que Envía el Sistema

### 1. 📧 Email de Confirmación
- **Cuándo:** Al confirmar una reserva
- **Contenido:** Detalles de la reserva, fecha, hora, mesa

### 2. ⏰ Email de Recordatorio  
- **Cuándo:** 24 horas antes de la reserva
- **Contenido:** Recordatorio con detalles de la reserva

### 3. ⚠️ Email de Expiración
- **Cuándo:** Si una reserva pendiente expira
- **Contenido:** Notificación de que la reserva expiró

## 🔧 Configuración en Docker

El `docker-compose.yml` ya incluye las variables de entorno necesarias:

```yaml
environment:
  - EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
  - DEFAULT_FROM_EMAIL=ReservaFlow <noreply@reservaflow.com>
  - RESERVATION_PENDING_TIMEOUT=15
```

Para cambiar a producción, modifica las variables en docker-compose.yml o usa un archivo `.env`.

## 🚨 Solución de Problemas

### Error: "SMTPAuthenticationError"
- ✅ Verifica usuario y contraseña
- ✅ Para Gmail, usa contraseña de aplicación
- ✅ Habilita "Acceso de aplicaciones menos seguras" si es necesario

### Error: "SMTPConnectTimeoutError"  
- ✅ Verifica HOST y PORT
- ✅ Revisa configuración de firewall
- ✅ Prueba con diferentes puertos (25, 465, 587)

### Emails no llegan
- ✅ Revisa carpeta de spam
- ✅ Verifica dominio emisor
- ✅ Para producción, configura SPF/DKIM records

### Para Desarrollo: Emails no se muestran
- ✅ Verifica que usas `console.EmailBackend`
- ✅ Revisa los logs de Django
- ✅ Ejecuta `test_email_config.py`

## 📚 Referencias Útiles

- [Documentación Django Email](https://docs.djangoproject.com/en/stable/topics/email/)
- [SendGrid Python SDK](https://github.com/sendgrid/sendgrid-python)
- [Contraseñas de Aplicación Gmail](https://support.google.com/accounts/answer/185833)
- [Amazon SES Setup](https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html)

---

## 🎯 Resumen de Archivos

- `.env` - Tu configuración local
- `.env.example` - Plantilla con todas las opciones
- `test_email_config.py` - Script para probar configuración
- `docker-compose.yml` - Variables de entorno para Docker
- `reservations/tasks.py` - Tareas Celery que envían emails