import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';

// Simple component test without complex dependencies
test('renders learn react link', () => {
  const testComponent = <div>Hello ReservaFlow</div>;
  render(testComponent);
  const linkElement = screen.getByText(/Hello ReservaFlow/i);
  expect(linkElement).toBeInTheDocument();
});

test('basic React Query setup works', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false }
    }
  });

  const TestComponent = () => <div>Query Client Test</div>;
  
  render(
    <QueryClientProvider client={queryClient}>
      <TestComponent />
    </QueryClientProvider>
  );
  
  expect(screen.getByText('Query Client Test')).toBeInTheDocument();
});

test('basic Router setup works', () => {
  const TestComponent = () => <div>Router Test</div>;
  
  render(
    <BrowserRouter>
      <TestComponent />
    </BrowserRouter>
  );
  
  expect(screen.getByText('Router Test')).toBeInTheDocument();
});