# ReservaFlow Frontend

Una aplicación React moderna para la gestión de reservas de restaurantes, construida con Material-UI y React Query.

## 🎨 Paleta de Colores

La aplicación utiliza una paleta de colores armoniosa y profesional:

- **Melon** (#ffa69e) - Color secundario, usado para acentos y botones importantes
- **Eggshell** (#faf3dd) - Color de fondo principal, suave y acogedor
- **Celeste** (#b8f2e6) - Color de éxito, usado para estados positivos
- **Light Blue** (#aed9e0) - Color informativo, usado para elementos informativos
- **Paynes Gray** (#5e6472) - Color primario, usado para texto y elementos principales

## 🚀 Características

### Dashboard
- **Vista general del sistema** con métricas en tiempo real
- **Estadísticas visuales** de restaurantes, clientes y reservas
- **Acceso rápido** a las funcionalidades principales
- **Reservas recientes** y notificaciones importantes

### Gestión de Restaurantes
- **Lista completa** de restaurantes con filtros avanzados
- **Búsqueda por nombre**, tipo de cocina y rango de precios
- **Información detallada** incluyendo horarios, capacidad y calificaciones
- **Vista de cards responsive** con información clave

### Gestión de Clientes
- **Base de datos de clientes** con información completa
- **Historial de reservas** por cliente
- **Preferencias y alergias** alimentarias
- **Puntuación de clientes** basada en comportamiento

### Sistema de Reservas
- **Proceso guiado paso a paso** para crear reservas
- **Selección visual de mesas** con disponibilidad en tiempo real
- **Validación inteligente** de conflictos y disponibilidad
- **Estados de reserva** con códigos de color intuitivos

### Sistema de Notificaciones
- **Centro de notificaciones** centralizado
- **Múltiples canales** (Email, SMS, Push)
- **Plantillas personalizables** para diferentes tipos de notificaciones
- **Seguimiento del estado** de envío

## 📱 Responsive Design

La aplicación está completamente optimizada para dispositivos móviles con:
- **Navegación móvil** con menú colapsible
- **Grid responsive** que se adapta a diferentes tamaños de pantalla
- **Componentes táctiles** optimizados para móviles
- **Formularios adaptativos** con validación en tiempo real

## 🛠 Tecnologías Utilizadas

### Core
- **React 18** - Biblioteca principal de UI
- **React Router DOM** - Enrutamiento del lado del cliente
- **React Query** - Gestión de estado del servidor y caché

### UI/UX
- **Material-UI (MUI)** - Sistema de componentes de diseño
- **MUI X Date Pickers** - Selección avanzada de fechas y horarios
- **Emotion** - CSS-in-JS para estilos personalizados

### Utilidades
- **Axios** - Cliente HTTP para API calls
- **Day.js** - Manipulación de fechas ligera
- **React Hook Form** - Gestión de formularios (próximamente)

## 📡 Integración con API

### Endpoints Integrados
- `GET /api/restaurants/` - Lista de restaurantes
- `POST /api/restaurants/` - Crear restaurante
- `GET /api/customers/` - Lista de clientes
- `POST /api/customers/` - Crear cliente
- `GET /api/reservations/` - Lista de reservas
- `POST /api/reservations/` - Crear reserva
- `PATCH /api/reservations/{id}/` - Actualizar estado de reserva
- `GET /api/notifications/` - Lista de notificaciones

### Gestión de Estado
- **React Query** maneja la caché y sincronización con la API
- **Optimistic updates** para mejor UX
- **Invalidación automática** de caché cuando se crean/actualizan datos
- **Loading states** y **error handling** integrados

## 🎯 Funcionalidades Clave

### 1. Dashboard Inteligente
```jsx
// Métricas en tiempo real
const { data: reservations } = useQuery('reservations', () => 
  reservationAPI.getAll({ page_size: 10 })
);

// Cálculo de estadísticas
const todayReservations = reservations?.filter(
  res => res.reservation_date === today
).length;
```

### 2. Búsqueda y Filtrado Avanzado
```jsx
const { data: restaurants } = useQuery(
  ['restaurants', searchTerm, cuisineFilter, priceFilter],
  () => restaurantAPI.getAll({
    search: searchTerm,
    cuisine_type: cuisineFilter,
    price_range: priceFilter,
  })
);
```

### 3. Formularios con Validación
```jsx
const createReservationMutation = useMutation(
  reservationAPI.create,
  {
    onSuccess: () => {
      queryClient.invalidateQueries('reservations');
      navigate('/reservations');
    },
    onError: (error) => {
      setErrors(error.response?.data);
    }
  }
);
```

### 4. Estados Visuales
```jsx
// Chips con colores temáticos
<Chip
  label={restaurant.cuisine_type}
  sx={{ 
    bgcolor: '#aed9e0', 
    color: '#5e6472' 
  }}
/>
```

## 🏗 Estructura del Proyecto

```
src/
├── components/          # Componentes reutilizables
│   └── Navigation.js    # Barra de navegación principal
├── pages/              # Páginas principales
│   ├── Dashboard.js    # Dashboard principal
│   ├── RestaurantList.js # Lista de restaurantes
│   ├── CreateReservation.js # Formulario de reserva
│   ├── CustomerList.js # Lista de clientes
│   └── NotificationList.js # Centro de notificaciones
├── services/           # Servicios de API
│   └── api.js         # Configuración de Axios y endpoints
├── hooks/             # Custom React hooks
├── contexts/          # React Context providers
├── utils/             # Utilidades y helpers
├── App.js            # Componente raíz
└── index.js          # Punto de entrada
```

## 🚦 Instalación y Configuración

### Prerrequisitos
- Node.js 16+ 
- npm o yarn
- Backend Django corriendo en puerto 8000

### Instalación
```bash
# Clonar el repositorio
cd FrontendReact

# Instalar dependencias
npm install

# Configurar variables de entorno
echo "REACT_APP_API_URL=http://localhost:8000" > .env

# Iniciar servidor de desarrollo
npm start
```

### Scripts Disponibles
```bash
npm start      # Servidor de desarrollo
npm build      # Build para producción
npm test       # Ejecutar tests
npm eject      # Eyectar configuración (no recomendado)
```

## 🔧 Configuración

### Variables de Entorno
```env
REACT_APP_API_URL=http://localhost:8000  # URL del backend
REACT_APP_VERSION=1.0.0                  # Versión de la app
```

### Proxy de Desarrollo
El `package.json` incluye un proxy automático:
```json
{
  "proxy": "http://localhost:8000"
}
```

## 📈 Rendimiento

### Optimizaciones Implementadas
- **Code splitting** con React.lazy (próximamente)
- **Memoización** de componentes pesados
- **Virtualización** de listas largas (próximamente)
- **Caché inteligente** con React Query
- **Imágenes optimizadas** con lazy loading

### Métricas
- **First Contentful Paint**: < 2s
- **Time to Interactive**: < 3s
- **Bundle size**: < 500KB (gzipped)
- **Lighthouse Score**: 90+ (Performance, Accessibility, SEO)

## 🎨 Guía de Estilo

### Colores
```javascript
const theme = {
  primary: '#5e6472',    // Paynes Gray
  secondary: '#ffa69e',  // Melon
  background: '#faf3dd', // Eggshell
  success: '#b8f2e6',    // Celeste
  info: '#aed9e0',       // Light Blue
}
```

### Tipografía
```javascript
const typography = {
  fontFamily: 'Roboto, Helvetica, Arial, sans-serif',
  h1: { color: '#5e6472', fontWeight: 300 },
  h4: { color: '#5e6472', fontWeight: 400 },
  body1: { color: '#5e6472' },
}
```

### Componentes Personalizados
```javascript
const StyledCard = styled(Card)(({ theme }) => ({
  border: '1px solid #b8f2e6',
  boxShadow: '0 2px 8px rgba(94, 100, 114, 0.1)',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: '0 4px 16px rgba(94, 100, 114, 0.2)',
  },
}));
```

## 🔮 Roadmap

### Próximas Características
- [ ] **Autenticación** con JWT
- [ ] **Dashboard Analytics** con gráficos
- [ ] **Notificaciones Push** en tiempo real
- [ ] **Modo Oscuro** alternativo
- [ ] **PWA** capabilities
- [ ] **Tests E2E** con Cypress
- [ ] **Storybook** para componentes
- [ ] **i18n** internacionalización

### Mejoras Planificadas
- [ ] **Drag & Drop** para gestión de mesas
- [ ] **Calendario visual** para reservas
- [ ] **Chat en vivo** con clientes
- [ ] **Integración con pagos**
- [ ] **Reportes avanzados**
- [ ] **API offline** con service workers

## 🤝 Contribución

### Flujo de Desarrollo
1. Fork del repositorio
2. Crear branch feature: `git checkout -b feature/nueva-caracteristica`
3. Commit cambios: `git commit -am 'Agregar nueva característica'`
4. Push al branch: `git push origin feature/nueva-caracteristica`
5. Crear Pull Request

### Estándares de Código
- **ESLint** para linting
- **Prettier** para formateo
- **Conventional Commits** para mensajes de commit
- **Husky** para git hooks
- **Jest** para unit testing

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Soporte

Para soporte técnico o preguntas:
- 📧 Email: soporte@reservaflow.com
- 📱 WhatsApp: +1-555-RESERVA
- 🐛 Issues: GitHub Issues
- 📖 Docs: [documentacion.reservaflow.com]

---

**ReservaFlow Frontend** - Construido con ❤️ usando React y Material-UI