# Documentación de la Carpeta `staticfiles/`

## ¿Qué es la carpeta `staticfiles/`?

La carpeta `staticfiles/` es donde Django **recopila automáticamente** todos los archivos estáticos de la aplicación durante el proceso de deployment o cuando se ejecuta el comando `collectstatic`.

## 🎯 **Propósito Principal**

Django usa esta carpeta para:
1. **Centralizar archivos estáticos**: Recopilar CSS, JavaScript, imágenes, etc. desde todas las apps
2. **Servir archivos en producción**: Permitir que un servidor web (nginx, Apache) sirva archivos estáticos directamente
3. **Optimización**: Facilitar el cacheo y compresión de archivos estáticos

## 📁 **Contenido Actual**

```bash
staticfiles/                    # Total: 4.5MB
├── admin/                     # Archivos estáticos del Django Admin
│   ├── css/                   # Estilos del admin (24 archivos CSS)
│   ├── js/                    # JavaScript del admin (96 archivos JS)
│   ├── img/                   # Imágenes del admin (23 archivos SVG)
│   └── fonts/                 # Fuentes del admin
└── rest_framework/            # Archivos estáticos de Django REST Framework
    ├── css/                   # Estilos de DRF (Bootstrap-based)
    ├── js/                    # JavaScript de DRF
    ├── img/                   # Imágenes de DRF
    └── fonts/                 # Fuentes de DRF
```

### Estadísticas:
- **Tamaño total**: 4.5 MB
- **Archivos CSS**: 24 archivos de estilos
- **Archivos JS**: 96 archivos JavaScript
- **Imágenes SVG**: 23 iconos vectoriales

## 🔄 **Cómo se genera**

Esta carpeta se crea automáticamente cuando Django ejecuta:

```bash
# Comando manual
python manage.py collectstatic

# En Docker (automático en entrypoint)
uv run python manage.py collectstatic --noinput
```

## ⚙️ **Configuración en Settings**

```python
# config/settings.py
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Destino para collectstatic

# config/settings_test.py
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = []
```

## 📂 **Fuentes de los archivos**

Los archivos en `staticfiles/` provienen de:

### 1. **Django Admin** (`admin/`)
- **Fuente**: Instalación de Django
- **Contiene**: Interfaz completa del Django Admin
- **Archivos**: CSS, JS, imágenes, iconos SVG, fuentes

### 2. **Django REST Framework** (`rest_framework/`)
- **Fuente**: Paquete `djangorestframework` 
- **Contiene**: Interfaz web navegable de la API
- **Archivos**: Estilos Bootstrap, JavaScript, iconos

### 3. **Apps personalizadas** (futuro)
Si agregas archivos en `[app]/static/`, aparecerán aquí después de `collectstatic`

## 🚀 **En Producción**

### Servidor Web (nginx/Apache)
```nginx
# nginx configuration
location /static/ {
    alias /path/to/staticfiles/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

### CDN Integration
```python
# Para CDN como AWS S3, CloudFront
STATIC_URL = 'https://cdn.reservaflow.com/static/'
```

## 🔧 **Docker Integration**

En el `docker-compose.yml`, el comando web incluye:
```bash
command: >
  bash -c "uv run python manage.py migrate &&
           uv run python manage.py collectstatic --noinput &&
           uv run python manage.py runserver 0.0.0.0:8000"
```

## 📝 **Git y .gitignore**

La carpeta `staticfiles/` **debe estar en .gitignore** porque:
- ✅ Se genera automáticamente
- ✅ Cambia con cada deploy
- ✅ No es código fuente
- ✅ Se puede recrear con `collectstatic`

```gitignore
# .gitignore
staticfiles/
!staticfiles/.gitkeep  # Opcional: mantener carpeta vacía
```

## 🧪 **En Tests**

Durante tests realistas, Django:
- **Crea**: `staticfiles/` temporalmente
- **Llena**: Con archivos de admin y DRF
- **Usa**: Para servir archivos en tests que requieren interfaz web
- **Limpia**: Al finalizar tests (opcional)

## ⚡ **Optimizaciones Posibles**

### Compresión (futuro)
```python
# settings.py
INSTALLED_APPS += ['compressor']
STATICFILES_FINDERS += ['compressor.finders.CompressorFinder']
```

### Versionado (futuro)
```python
# settings.py  
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
```

## 🏷️ **Resumen**

| Aspecto | Detalle |
|---------|---------|
| **Propósito** | Recopilar archivos estáticos para producción |
| **Contenido** | CSS, JS, imágenes de Django Admin + DRF |
| **Generación** | Automática con `collectstatic` |
| **En Git** | ❌ NO incluir (se genera automáticamente) |
| **En Docker** | ✅ Se crea automáticamente |
| **En Tests** | ✅ Necesario para interfaces web |

La carpeta `staticfiles/` es **esencial para el funcionamiento correcto** de Django Admin y la interfaz web de la API, pero **no requiere mantenimiento manual**.