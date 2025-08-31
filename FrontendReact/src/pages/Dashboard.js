import React from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import {
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Box,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Restaurant,
  People,
  EventNote,
  Notifications,
  TrendingUp,
  Schedule,
} from '@mui/icons-material';
import { restaurantAPI, customerAPI, reservationAPI, notificationAPI } from '../services/api';

const Dashboard = () => {
  // Fetch dashboard data
  const { data: restaurants, isLoading: loadingRestaurants } = useQuery(
    'restaurants',
    () => restaurantAPI.getAll({ page_size: 5 }),
    {
      select: (data) => data.data.results,
    }
  );

  const { data: customers, isLoading: loadingCustomers } = useQuery(
    'customers',
    () => customerAPI.getAll({ page_size: 5 }),
    {
      select: (data) => data.data.results,
    }
  );

  const { data: reservations, isLoading: loadingReservations } = useQuery(
    'reservations',
    () => reservationAPI.getAll({ page_size: 10 }),
    {
      select: (data) => data.data,
    }
  );

  const { data: notifications, isLoading: loadingNotifications } = useQuery(
    'notifications',
    () => notificationAPI.getAll({ page_size: 5 }),
    {
      select: (data) => data.data.results,
    }
  );

  // Calculate stats
  const totalReservations = reservations?.count || 0;
  const todayReservations = reservations?.results?.filter(
    (res) => res.reservation_date === new Date().toISOString().split('T')[0]
  ).length || 0;
  const pendingReservations = reservations?.results?.filter(
    (res) => res.status === 'pending'
  ).length || 0;
  const confirmedReservations = reservations?.results?.filter(
    (res) => res.status === 'confirmed'
  ).length || 0;

  const statsCards = [
    {
      title: 'Total Restaurantes',
      value: restaurants?.length || 0,
      icon: <Restaurant fontSize="large" />,
      color: '#5e6472', // paynes-gray
      link: '/restaurants',
    },
    {
      title: 'Total Clientes',
      value: customers?.length || 0,
      icon: <People fontSize="large" />,
      color: '#b8f2e6', // celeste
      link: '/customers',
    },
    {
      title: 'Reservas Totales',
      value: totalReservations,
      icon: <EventNote fontSize="large" />,
      color: '#ffa69e', // melon
      link: '/reservations',
    },
    {
      title: 'Reservas Hoy',
      value: todayReservations,
      icon: <Schedule fontSize="large" />,
      color: '#aed9e0', // light-blue
      link: '/reservations',
    },
    {
      title: 'Reservas Pendientes',
      value: pendingReservations,
      icon: <TrendingUp fontSize="large" />,
      color: '#ffa69e', // melon
      link: '/reservations?status=pending',
    },
    {
      title: 'Notificaciones',
      value: notifications?.length || 0,
      icon: <Notifications fontSize="large" />,
      color: '#5e6472', // paynes-gray
      link: '/notifications',
    },
  ];

  if (loadingRestaurants || loadingCustomers || loadingReservations || loadingNotifications) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {statsCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={4} key={index}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box display="flex" alignItems="center" mb={2}>
                  <Box sx={{ color: card.color, mr: 2 }}>
                    {card.icon}
                  </Box>
                  <Typography variant="h6" component="div">
                    {card.title}
                  </Typography>
                </Box>
                <Typography variant="h3" component="div" sx={{ color: card.color }}>
                  {card.value}
                </Typography>
              </CardContent>
              <CardActions>
                <Button
                  size="small"
                  component={Link}
                  to={card.link}
                  sx={{ color: card.color }}
                >
                  Ver más
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Recent Activities */}
      <Grid container spacing={3}>
        {/* Recent Reservations */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Reservas Recientes
              </Typography>
              {reservations?.results?.slice(0, 5).map((reservation) => (
                <Box key={reservation.id} sx={{ mb: 2, pb: 2, borderBottom: '1px solid #eee' }}>
                  <Typography variant="body1">
                    Mesa {reservation.table} - {reservation.party_size} personas
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {reservation.reservation_date} a las {reservation.reservation_time}
                  </Typography>
                  <Box
                    sx={{
                      display: 'inline-block',
                      px: 1,
                      py: 0.5,
                      borderRadius: 1,
                      bgcolor: reservation.status === 'confirmed' ? 'success.light' : 
                               reservation.status === 'pending' ? 'warning.light' : 'error.light',
                      color: 'white',
                      fontSize: '0.75rem',
                    }}
                  >
                    {reservation.status}
                  </Box>
                </Box>
              ))}
              <CardActions>
                <Button size="small" component={Link} to="/reservations">
                  Ver todas las reservas
                </Button>
              </CardActions>
            </CardContent>
          </Card>
        </Grid>

        {/* Quick Actions */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Acciones Rápidas
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                <Button
                  variant="contained"
                  startIcon={<EventNote />}
                  component={Link}
                  to="/create-reservation"
                  fullWidth
                >
                  Nueva Reserva
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Restaurant />}
                  component={Link}
                  to="/restaurants"
                  fullWidth
                >
                  Gestionar Restaurantes
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<People />}
                  component={Link}
                  to="/customers"
                  fullWidth
                >
                  Gestionar Clientes
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Notifications />}
                  component={Link}
                  to="/notifications"
                  fullWidth
                >
                  Ver Notificaciones
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* System Status */}
      {(confirmedReservations > 0 || pendingReservations > 0) && (
        <Alert severity="info" sx={{ mt: 3 }}>
          Tienes {pendingReservations} reservas pendientes de confirmación y {confirmedReservations} reservas confirmadas para hoy.
        </Alert>
      )}
    </Box>
  );
};

export default Dashboard;