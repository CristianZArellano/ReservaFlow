import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Container } from '@mui/material';
import Navigation from './components/Navigation';
import Dashboard from './pages/Dashboard';
import RestaurantList from './pages/RestaurantList';
import RestaurantDetail from './pages/RestaurantDetail';
import CustomerList from './pages/CustomerList';
import CustomerDetail from './pages/CustomerDetail';
import ReservationList from './pages/ReservationList';
import ReservationDetail from './pages/ReservationDetail';
import CreateReservation from './pages/CreateReservation';
import NotificationList from './pages/NotificationList';

function App() {
  return (
    <div className="App">
      <Navigation />
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          
          {/* Restaurants */}
          <Route path="/restaurants" element={<RestaurantList />} />
          <Route path="/restaurants/:id" element={<RestaurantDetail />} />
          
          {/* Customers */}
          <Route path="/customers" element={<CustomerList />} />
          <Route path="/customers/:id" element={<CustomerDetail />} />
          
          {/* Reservations */}
          <Route path="/reservations" element={<ReservationList />} />
          <Route path="/reservations/:id" element={<ReservationDetail />} />
          <Route path="/create-reservation" element={<CreateReservation />} />
          
          {/* Notifications */}
          <Route path="/notifications" element={<NotificationList />} />
        </Routes>
      </Container>
    </div>
  );
}

export default App;