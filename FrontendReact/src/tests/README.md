# 🧪 Frontend Tests - ReservaFlow React

Esta carpeta contiene todos los tests del frontend React organizados por categorías y funcionalidad.

## 📁 Estructura de Tests

```
src/
├── 📂 __tests__/               # Tests principales
│   ├── 📄 App.test.js          # Test del componente principal
│   ├── 📄 setupTests.js        # Configuración de Jest/Testing Library
│   └── 📄 testUtils.js         # Utilidades para testing
│
├── 📂 components/
│   ├── 📂 __tests__/           # Tests de componentes
│   │   ├── 📄 Layout.test.js
│   │   ├── 📄 Sidebar.test.js
│   │   └── 📄 StatCard.test.js
│   └── 📂 common/
│       └── 📂 __tests__/       # Tests de componentes comunes
│           ├── 📄 LoadingSpinner.test.js
│           └── 📄 ErrorBoundary.test.js
│
├── 📂 pages/
│   ├── 📂 __tests__/           # Tests de páginas
│   │   ├── 📄 Dashboard.test.js
│   │   ├── 📄 CustomerList.test.js
│   │   ├── 📄 RestaurantList.test.js
│   │   ├── 📄 ReservationList.test.js
│   │   └── 📄 NotificationList.test.js
│   └── 📂 forms/
│       └── 📂 __tests__/       # Tests de formularios
│           ├── 📄 CustomerForm.test.js
│           └── 📄 ReservationForm.test.js
│
├── 📂 services/
│   └── 📂 __tests__/           # Tests de servicios
│       ├── 📄 api.test.js      # Tests de cliente API
│       └── 📄 utils.test.js    # Tests de utilidades
│
├── 📂 hooks/
│   └── 📂 __tests__/           # Tests de custom hooks
│       ├── 📄 useApi.test.js
│       └── 📄 useDebounce.test.js
│
└── 📂 integration/             # Tests de integración
    ├── 📄 userFlow.test.js     # Flujos de usuario completos
    └── 📄 apiIntegration.test.js # Integración con API
```

## 🎯 Tipos de Tests

### 🧩 Tests de Componentes
Tests que verifican el comportamiento de componentes individuales:
- **Renderizado**: El componente se renderiza correctamente
- **Props**: Manejo correcto de propiedades
- **Estado**: Gestión de estado interno
- **Eventos**: Respuesta a eventos de usuario

### 📄 Tests de Páginas
Tests que verifican páginas completas:
- **Layout**: Estructura y elementos principales
- **Navegación**: Links y routing
- **Datos**: Carga y muestra de información
- **Formularios**: Validación y envío

### 🔌 Tests de Servicios
Tests de la capa de servicios:
- **API Calls**: Llamadas correctas a la API
- **Error Handling**: Manejo de errores
- **Data Transformation**: Transformación de datos
- **Caching**: Gestión de caché

### 🎣 Tests de Hooks
Tests de custom hooks:
- **Logic**: Lógica de negocio
- **Side Effects**: Efectos secundarios
- **Dependencies**: Dependencias y re-renders
- **Cleanup**: Limpieza de recursos

### 🌐 Tests de Integración
Tests que verifican la integración entre componentes:
- **User Flows**: Flujos completos de usuario
- **API Integration**: Integración real con backend
- **State Management**: Gestión global de estado
- **Routing**: Navegación entre páginas

## 🛠️ Herramientas de Testing

### Principales Librerías
- **Jest**: Framework de testing
- **React Testing Library**: Testing de componentes React
- **@testing-library/user-event**: Simulación de eventos de usuario
- **@testing-library/jest-dom**: Matchers adicionales para DOM
- **MSW (Mock Service Worker)**: Mocking de APIs (opcional)

### Configuración (`setupTests.js`)
```javascript
import '@testing-library/jest-dom';
import { configure } from '@testing-library/react';

// Configuración global
configure({ testIdAttribute: 'data-testid' });

// Mocks globales
global.matchMedia = global.matchMedia || function (query) {
  return {
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  };
};
```

## 🚀 Comandos de Testing

### Comandos Básicos
```bash
# Ejecutar todos los tests
npm test

# Tests en modo watch
npm test -- --watch

# Tests sin watch
npm test -- --watchAll=false

# Tests con cobertura
npm test -- --coverage --watchAll=false

# Tests específicos
npm test -- --testNamePattern="Dashboard"
npm test -- --testPathPattern="components"
```

### Tests Avanzados
```bash
# Tests en paralelo
npm test -- --maxWorkers=4

# Tests con reporte detallado
npm test -- --verbose

# Tests con información de cobertura
npm test -- --coverage --coverageReporters=text-lcov

# Tests solo de archivos cambiados
npm test -- --onlyChanged
```

## 📊 Patrones de Testing

### Test de Componente Básico
```javascript
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from '../Dashboard';

// Test wrapper con providers
const renderWithProviders = (component) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('Dashboard Component', () => {
  test('renders dashboard title', () => {
    renderWithProviders(<Dashboard />);
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  test('displays loading state initially', () => {
    renderWithProviders(<Dashboard />);
    
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });
});
```

### Test con User Events
```javascript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CustomerForm from '../CustomerForm';

describe('CustomerForm', () => {
  test('submits form with valid data', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    
    render(<CustomerForm onSubmit={onSubmit} />);
    
    await user.type(screen.getByLabelText(/nombre/i), 'Juan');
    await user.type(screen.getByLabelText(/email/i), 'juan@email.com');
    await user.click(screen.getByRole('button', { name: /guardar/i }));
    
    expect(onSubmit).toHaveBeenCalledWith({
      name: 'Juan',
      email: 'juan@email.com'
    });
  });
});
```

### Test de API Service
```javascript
import axios from 'axios';
import { customerAPI } from '../api';

jest.mock('axios');
const mockedAxios = axios;

describe('Customer API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('fetches customers successfully', async () => {
    const mockCustomers = [
      { id: 1, name: 'Juan', email: 'juan@email.com' }
    ];
    
    mockedAxios.get.mockResolvedValue({
      data: { results: mockCustomers, count: 1 }
    });

    const result = await customerAPI.getAll();

    expect(mockedAxios.get).toHaveBeenCalledWith('/api/customers/', { params: {} });
    expect(result.data.results).toEqual(mockCustomers);
  });
});
```

### Test de Custom Hook
```javascript
import { renderHook, act } from '@testing-library/react';
import { useDebounce } from '../useDebounce';

describe('useDebounce', () => {
  test('debounces value changes', () => {
    jest.useFakeTimers();
    
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 500 } }
    );

    expect(result.current).toBe('initial');

    rerender({ value: 'updated', delay: 500 });
    expect(result.current).toBe('initial'); // Still old value

    act(() => {
      jest.advanceTimersByTime(500);
    });
    
    expect(result.current).toBe('updated'); // Now updated

    jest.useRealTimers();
  });
});
```

## 🎯 Utilidades de Testing

### Test Utilities (`testUtils.js`)
```javascript
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material';
import theme from '../theme';

// Provider wrapper para todos los tests
export const AllProviders = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          {children}
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

// Custom render con todos los providers
export const renderWithProviders = (ui, options) => {
  return render(ui, { wrapper: AllProviders, ...options });
};

// Mock data factories
export const mockCustomer = (overrides = {}) => ({
  id: 1,
  first_name: 'Juan',
  last_name: 'Pérez',
  email: 'juan@email.com',
  phone: '+1234567890',
  ...overrides,
});

export const mockRestaurant = (overrides = {}) => ({
  id: 1,
  name: 'La Bella Italia',
  cuisine_type: 'italiana',
  address: 'Calle Principal 123',
  ...overrides,
});

// Async utilities
export const waitForLoadingToFinish = () =>
  waitForElementToBeRemoved(screen.queryByTestId('loading-spinner'));
```

## 📋 Configuración de Jest

### `package.json` Scripts
```json
{
  "scripts": {
    "test": "react-scripts test",
    "test:coverage": "npm test -- --coverage --watchAll=false",
    "test:ci": "npm test -- --coverage --ci --watchAll=false"
  },
  "jest": {
    "collectCoverageFrom": [
      "src/**/*.{js,jsx}",
      "!src/index.js",
      "!src/serviceWorker.js",
      "!src/**/*.test.js"
    ],
    "coverageThreshold": {
      "global": {
        "branches": 80,
        "functions": 80,
        "lines": 80,
        "statements": 80
      }
    }
  }
}
```

## 🎨 Testing con Material-UI

### Testing de Componentes MUI
```javascript
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from '@mui/material';
import theme from '../theme';
import StatCard from '../StatCard';

const renderWithTheme = (component) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('StatCard', () => {
  test('renders with correct styling', () => {
    renderWithTheme(
      <StatCard title="Total Clientes" value="150" color="primary" />
    );
    
    const card = screen.getByRole('article');
    expect(card).toHaveClass('MuiCard-root');
  });
});
```

## 📊 Métricas y Cobertura

### Objetivos de Cobertura
- **Statements**: >80%
- **Branches**: >80%
- **Functions**: >80%
- **Lines**: >80%

### Archivos Excluidos
- `index.js`
- `serviceWorker.js`
- `reportWebVitals.js`
- `*.test.js`
- `setupTests.js`

### Reportes
- **HTML Report**: `coverage/lcov-report/index.html`
- **JSON Report**: `coverage/coverage-final.json`
- **LCOV Report**: `coverage/lcov.info`

## 🐛 Debugging Tests

### Debug en Consola
```javascript
import { screen, logRoles, prettyDOM } from '@testing-library/react';

// Ver todos los roles disponibles
logRoles(container);

// Ver el DOM actual
console.log(prettyDOM(container));

// Debug específico
screen.debug(); // Todo el documento
screen.debug(screen.getByTestId('customer-list')); // Elemento específico
```

### Debug con VS Code
1. Crear `.vscode/launch.json`
2. Configurar debugging para Jest
3. Poner breakpoints en tests
4. Ejecutar en modo debug

## 🎯 Mejores Prácticas

### Principios
- **AAA**: Arrange, Act, Assert
- **DRY**: Don't Repeat Yourself en utilities
- **Isolation**: Cada test debe ser independiente
- **Descriptive**: Nombres de test descriptivos

### Nomenclatura
- **Files**: `ComponentName.test.js`
- **Describe blocks**: Component/functionality name
- **Test cases**: `should do X when Y` or `does X when Y`

### Performance
- **Mock heavy operations**: API calls, large computations
- **Use fake timers**: Para tests que involucren tiempo
- **Cleanup**: Limpiar mocks entre tests
- **Parallel execution**: Configurar workers para CI

---

**Objetivo**: Mantener una suite de tests robusta que garantice la calidad del frontend y facilite el desarrollo con confianza.