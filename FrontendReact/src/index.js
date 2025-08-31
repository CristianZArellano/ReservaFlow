import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import App from './App';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

const theme = createTheme({
  palette: {
    primary: {
      main: '#5e6472', // paynes-gray
      light: '#aed9e0', // light-blue
      dark: '#4a4f5a',
      contrastText: '#faf3dd', // eggshell
    },
    secondary: {
      main: '#ffa69e', // melon
      light: '#ffb8b1',
      dark: '#e8948d',
      contrastText: '#5e6472',
    },
    background: {
      default: '#faf3dd', // eggshell
      paper: '#ffffff',
    },
    success: {
      main: '#b8f2e6', // celeste
      dark: '#9ee8d7',
      contrastText: '#5e6472',
    },
    info: {
      main: '#aed9e0', // light-blue
      dark: '#9bc8d1',
      contrastText: '#5e6472',
    },
    warning: {
      main: '#ffa69e', // melon
      dark: '#e8948d',
      contrastText: '#5e6472',
    },
    error: {
      main: '#ff6b6b',
      dark: '#e85555',
      contrastText: '#ffffff',
    },
    text: {
      primary: '#5e6472', // paynes-gray
      secondary: '#7a808e',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      color: '#5e6472',
    },
    h2: {
      color: '#5e6472',
    },
    h3: {
      color: '#5e6472',
    },
    h4: {
      color: '#5e6472',
    },
    h5: {
      color: '#5e6472',
    },
    h6: {
      color: '#5e6472',
    },
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: 'linear-gradient(135deg, #5e6472, #aed9e0)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          background: '#ffffff',
          border: '1px solid #b8f2e6',
          boxShadow: '0 2px 8px rgba(94, 100, 114, 0.1)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        contained: {
          background: 'linear-gradient(45deg, #ffa69e, #ff9b93)',
          '&:hover': {
            background: 'linear-gradient(45deg, #e8948d, #e88984)',
          },
        },
      },
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <App />
        </ThemeProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
);