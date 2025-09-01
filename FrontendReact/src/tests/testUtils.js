import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

// Tema personalizado para tests
const testTheme = createTheme({
  palette: {
    primary: {
      main: '#ffa69e', // Melon
    },
    secondary: {
      main: '#b8f2e6', // Celeste
    },
    background: {
      default: '#faf3dd', // Eggshell
    },
    text: {
      primary: '#5e6472', // Paynes Gray
    },
  },
});

// Provider wrapper para todos los tests
export const AllProviders = ({ children, initialEntries = ['/'] }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { 
        retry: false,
        staleTime: Infinity,
        cacheTime: Infinity,
      },
      mutations: { 
        retry: false,
      },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <ThemeProvider theme={testTheme}>
          {children}
        </ThemeProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

// Provider wrapper con BrowserRouter (para tests que necesiten URL real)
export const BrowserProviders = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider theme={testTheme}>
          {children}
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

// Custom render con todos los providers
export const renderWithProviders = (ui, options = {}) => {
  const { initialEntries, ...renderOptions } = options;
  
  const Wrapper = ({ children }) => (
    <AllProviders initialEntries={initialEntries}>
      {children}
    </AllProviders>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

// Custom render con BrowserRouter
export const renderWithBrowserProviders = (ui, options) => {
  return render(ui, { wrapper: BrowserProviders, ...options });
};

// Mock data factories
export const mockCustomer = (overrides = {}) => ({
  id: '1',
  first_name: 'Juan',
  last_name: 'Pérez',
  email: 'juan@email.com',
  phone: '+1234567890',
  date_of_birth: '1985-05-15',
  dietary_preferences: null,
  special_requests: null,
  created_at: '2023-01-01T10:00:00Z',
  updated_at: '2023-01-01T10:00:00Z',
  ...overrides,
});

export const mockRestaurant = (overrides = {}) => ({
  id: '1',
  name: 'La Bella Italia',
  description: 'Auténtica cocina italiana',
  cuisine_type: 'italiana',
  address: 'Calle Principal 123',
  phone: '+1234567890',
  email: 'info@bellaitalia.com',
  price_range: '$$',
  opening_time: '12:00:00',
  closing_time: '23:00:00',
  total_tables: 10,
  accepts_reservations: true,
  created_at: '2023-01-01T10:00:00Z',
  updated_at: '2023-01-01T10:00:00Z',
  ...overrides,
});

export const mockTable = (overrides = {}) => ({
  id: '1',
  restaurant: '1',
  number: 1,
  capacity: 4,
  location: 'Ventana',
  has_view: true,
  is_accessible: false,
  created_at: '2023-01-01T10:00:00Z',
  updated_at: '2023-01-01T10:00:00Z',
  ...overrides,
});

export const mockReservation = (overrides = {}) => ({
  id: '1',
  customer: mockCustomer(),
  restaurant: mockRestaurant(),
  table: mockTable(),
  reservation_date: '2023-12-25',
  reservation_time: '19:30:00',
  party_size: 4,
  status: 'confirmed',
  special_requests: null,
  created_at: '2023-01-01T10:00:00Z',
  updated_at: '2023-01-01T10:00:00Z',
  expires_at: '2023-12-25T19:15:00Z',
  ...overrides,
});

export const mockNotification = (overrides = {}) => ({
  id: '1',
  customer: mockCustomer(),
  notification_type: 'reservation_confirmation',
  channel: 'email',
  subject: 'Confirmación de Reserva',
  message: 'Su reserva ha sido confirmada',
  recipient: 'juan@email.com',
  recipient_name: 'Juan Pérez',
  status: 'sent',
  created_at: '2023-01-01T10:00:00Z',
  sent_at: '2023-01-01T10:01:00Z',
  delivered_at: '2023-01-01T10:02:00Z',
  read_at: null,
  ...overrides,
});

// API Response factories
export const mockApiResponse = (data, overrides = {}) => ({
  data: {
    results: Array.isArray(data) ? data : [data],
    count: Array.isArray(data) ? data.length : 1,
    next: null,
    previous: null,
    ...overrides,
  },
});

export const mockPaginatedResponse = (data, page = 1, pageSize = 10) => ({
  data: {
    results: data,
    count: data.length,
    next: data.length === pageSize ? `?page=${page + 1}` : null,
    previous: page > 1 ? `?page=${page - 1}` : null,
  },
});

// Async utilities
export const waitForLoadingToFinish = async () => {
  const { waitForElementToBeRemoved, screen } = await import('@testing-library/react');
  await waitForElementToBeRemoved(
    () => screen.queryByTestId('loading-spinner') || screen.queryByText(/cargando/i),
    { timeout: 3000 }
  );
};

// User event helpers
export const setupUser = () => {
  const userEvent = require('@testing-library/user-event');
  return userEvent.setup();
};

// Mock window.matchMedia
export const mockMatchMedia = (matches = false) => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
      matches,
      media: query,
      onchange: null,
      addListener: jest.fn(), // deprecated
      removeListener: jest.fn(), // deprecated
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
};

// Mock IntersectionObserver
export const mockIntersectionObserver = () => {
  global.IntersectionObserver = class IntersectionObserver {
    constructor() {}
    observe() {
      return null;
    }
    disconnect() {
      return null;
    }
    unobserve() {
      return null;
    }
  };
};

// Mock ResizeObserver
export const mockResizeObserver = () => {
  global.ResizeObserver = class ResizeObserver {
    constructor() {}
    observe() {
      return null;
    }
    disconnect() {
      return null;
    }
    unobserve() {
      return null;
    }
  };
};

// Setup all common mocks
export const setupTestMocks = () => {
  mockMatchMedia();
  mockIntersectionObserver();
  mockResizeObserver();
};

// Custom matchers for better assertions
export const customMatchers = {
  toHaveBeenCalledWithApiParams: (received, expected) => {
    const pass = received.mock.calls.some(call => {
      const actualParams = call[1]?.params || call[0];
      return JSON.stringify(actualParams) === JSON.stringify(expected);
    });

    return {
      pass,
      message: () => 
        pass
          ? `Expected not to be called with API params ${JSON.stringify(expected)}`
          : `Expected to be called with API params ${JSON.stringify(expected)}, but was called with ${JSON.stringify(received.mock.calls)}`,
    };
  },
};

// Test data sets
export const testDataSets = {
  customers: [
    mockCustomer({ id: '1', first_name: 'Juan', last_name: 'Pérez' }),
    mockCustomer({ id: '2', first_name: 'María', last_name: 'González' }),
    mockCustomer({ id: '3', first_name: 'Carlos', last_name: 'López' }),
  ],
  
  restaurants: [
    mockRestaurant({ id: '1', name: 'La Bella Italia', cuisine_type: 'italiana' }),
    mockRestaurant({ id: '2', name: 'Sushi Zen', cuisine_type: 'japonesa' }),
    mockRestaurant({ id: '3', name: 'Taco Loco', cuisine_type: 'mexicana' }),
  ],
  
  reservations: [
    mockReservation({ id: '1', status: 'pending' }),
    mockReservation({ id: '2', status: 'confirmed' }),
    mockReservation({ id: '3', status: 'completed' }),
  ],
};

// Environment setup
export const setupTestEnvironment = () => {
  setupTestMocks();
  
  // Mock console methods to avoid noise in tests
  const originalError = console.error;
  const originalWarn = console.warn;
  
  beforeAll(() => {
    console.error = (...args) => {
      if (
        typeof args[0] === 'string' &&
        args[0].includes('Warning: ReactDOM.render is deprecated')
      ) {
        return;
      }
      originalError.call(console, ...args);
    };
    
    console.warn = (...args) => {
      if (
        typeof args[0] === 'string' &&
        (args[0].includes('React Router Future Flag Warning') ||
         args[0].includes('deprecated'))
      ) {
        return;
      }
      originalWarn.call(console, ...args);
    };
  });
  
  afterAll(() => {
    console.error = originalError;
    console.warn = originalWarn;
  });
};