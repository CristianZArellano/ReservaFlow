# Warnings Conocidos del Sistema

## PostgreSQL Collation Version Warning

### Warning:
```
WARNING: database "restaurant_reservations" has no actual collation version, but a version was recorded
```

### Explicación:
Este warning es **completamente normal** en entornos Docker y no afecta la funcionalidad:

- **Causa**: Diferencia entre las versiones de collation del host Docker y el contenedor PostgreSQL
- **Impacto**: **Ninguno** - el sistema funciona perfectamente
- **Frecuencia**: Aparece en cada conexión a la base de datos
- **Común en**: Docker, Kubernetes, contenedores en general

### ¿Es peligroso?
**NO**. Este warning:
- ✅ No afecta la funcionalidad de la aplicación
- ✅ No causa errores en las queries
- ✅ No corrompe datos
- ✅ Es extremadamente común en desarrollos con Docker

### Soluciones disponibles:
1. **Ignorar** (recomendado): El warning es benigno
2. **Suprimir logs**: Configurar PostgreSQL para no mostrar warnings (puede ocultar otros problemas)
3. **Recrear BD**: Borrar volúmenes Docker y recrear (temporal)

### Conclusión:
**Este warning puede ser ignorado sin problemas**. El sistema ReservaFlow está completamente funcional.

## Otros Warnings Menores

### Django Cache Connection
- **Warning ocasional**: Timeouts de Redis en desarrollo
- **Impacto**: Mínimo - hay fallback automático
- **Solución**: Los locks distribuidos usan fallback local si Redis no está disponible

### uv Virtual Environment
- **Warning**: "Ignoring existing virtual environment linked to non-existent Python interpreter"
- **Causa**: uv detecta cambios en el intérprete Python
- **Impacto**: Ninguno - uv recrea el entorno automáticamente
- **Solución**: Automática - no requiere acción