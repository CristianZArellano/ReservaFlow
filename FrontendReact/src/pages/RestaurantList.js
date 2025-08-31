import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  TextField,
  InputAdornment,
  Chip,
  Rating,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Search,
  Restaurant,
  Phone,
  Email,
  Schedule,
  People,
} from '@mui/icons-material';
import { restaurantAPI } from '../services/api';

const RestaurantList = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [cuisineFilter, setCuisineFilter] = useState('');
  const [priceFilter, setPriceFilter] = useState('');

  const { data: restaurants, isLoading, isError, error } = useQuery(
    ['restaurants', searchTerm, cuisineFilter, priceFilter],
    () => restaurantAPI.getAll({
      search: searchTerm,
      cuisine_type: cuisineFilter,
      price_range: priceFilter,
    }),
    {
      select: (data) => data.data.results,
      keepPreviousData: true,
    }
  );

  const cuisineTypes = [
    { value: 'mexican', label: 'Mexicana' },
    { value: 'italian', label: 'Italiana' },
    { value: 'japanese', label: 'Japonesa' },
    { value: 'american', label: 'Americana' },
    { value: 'french', label: 'Francesa' },
    { value: 'chinese', label: 'China' },
    { value: 'indian', label: 'India' },
    { value: 'mediterranean', label: 'Mediterránea' },
    { value: 'fusion', label: 'Fusión' },
    { value: 'other', label: 'Otra' },
  ];

  const priceRanges = [
    { value: 'low', label: 'Económico' },
    { value: 'mid', label: 'Medio' },
    { value: 'high', label: 'Alto' },
    { value: 'luxury', label: 'Lujo' },
  ];

  const getPriceRangeColor = (priceRange) => {
    const colors = {
      low: '#b8f2e6',      // celeste
      mid: '#aed9e0',      // light-blue
      high: '#ffa69e',     // melon
      luxury: '#5e6472',   // paynes-gray
    };
    return colors[priceRange] || '#5e6472';
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (isError) {
    return (
      <Alert severity="error">
        Error al cargar los restaurantes: {error.message}
      </Alert>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Restaurantes
        </Typography>
        <Button
          variant="contained"
          startIcon={<Restaurant />}
          component={Link}
          to="/restaurants/new"
        >
          Nuevo Restaurante
        </Button>
      </Box>

      {/* Filtros */}
      <Box mb={3}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              placeholder="Buscar restaurantes..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Tipo de Cocina</InputLabel>
              <Select
                value={cuisineFilter}
                label="Tipo de Cocina"
                onChange={(e) => setCuisineFilter(e.target.value)}
              >
                <MenuItem value="">Todos</MenuItem>
                {cuisineTypes.map((cuisine) => (
                  <MenuItem key={cuisine.value} value={cuisine.value}>
                    {cuisine.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Rango de Precio</InputLabel>
              <Select
                value={priceFilter}
                label="Rango de Precio"
                onChange={(e) => setPriceFilter(e.target.value)}
              >
                <MenuItem value="">Todos</MenuItem>
                {priceRanges.map((price) => (
                  <MenuItem key={price.value} value={price.value}>
                    {price.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Box>

      {/* Lista de Restaurantes */}
      <Grid container spacing={3}>
        {restaurants?.map((restaurant) => (
          <Grid item xs={12} md={6} lg={4} key={restaurant.id}>
            <Card 
              sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s, box-shadow 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: `0 4px 16px rgba(94, 100, 114, 0.2)`,
                },
              }}
            >
              <CardContent sx={{ flexGrow: 1 }}>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                  <Typography variant="h6" component="h2" sx={{ color: '#5e6472' }}>
                    {restaurant.name}
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    {restaurant.is_active ? (
                      <Chip label="Activo" size="small" sx={{ bgcolor: '#b8f2e6', color: '#5e6472' }} />
                    ) : (
                      <Chip label="Inactivo" size="small" color="error" />
                    )}
                  </Box>
                </Box>

                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {restaurant.description?.substring(0, 100)}...
                </Typography>

                <Box mb={2}>
                  <Box display="flex" alignItems="center" mb={1}>
                    <Chip
                      label={cuisineTypes.find(c => c.value === restaurant.cuisine_type)?.label || restaurant.cuisine_type}
                      size="small"
                      sx={{ 
                        bgcolor: '#aed9e0', 
                        color: '#5e6472',
                        mr: 1
                      }}
                    />
                    <Chip
                      label={priceRanges.find(p => p.value === restaurant.price_range)?.label || restaurant.price_range}
                      size="small"
                      sx={{ 
                        bgcolor: getPriceRangeColor(restaurant.price_range),
                        color: '#5e6472',
                      }}
                    />
                  </Box>
                  
                  {restaurant.average_rating && (
                    <Box display="flex" alignItems="center" mb={1}>
                      <Rating
                        value={restaurant.average_rating}
                        precision={0.1}
                        readOnly
                        size="small"
                      />
                      <Typography variant="body2" sx={{ ml: 1, color: '#5e6472' }}>
                        ({restaurant.average_rating})
                      </Typography>
                    </Box>
                  )}
                </Box>

                <Box>
                  <Box display="flex" alignItems="center" mb={1}>
                    <Phone sx={{ fontSize: 16, mr: 1, color: '#5e6472' }} />
                    <Typography variant="body2" color="text.secondary">
                      {restaurant.phone}
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" mb={1}>
                    <Email sx={{ fontSize: 16, mr: 1, color: '#5e6472' }} />
                    <Typography variant="body2" color="text.secondary">
                      {restaurant.email}
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" mb={1}>
                    <Schedule sx={{ fontSize: 16, mr: 1, color: '#5e6472' }} />
                    <Typography variant="body2" color="text.secondary">
                      {restaurant.opening_time} - {restaurant.closing_time}
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center">
                    <People sx={{ fontSize: 16, mr: 1, color: '#5e6472' }} />
                    <Typography variant="body2" color="text.secondary">
                      Capacidad: {restaurant.total_capacity} personas
                    </Typography>
                  </Box>
                </Box>
              </CardContent>

              <CardActions sx={{ p: 2, pt: 0 }}>
                <Button
                  size="small"
                  component={Link}
                  to={`/restaurants/${restaurant.id}`}
                  sx={{ color: '#5e6472' }}
                >
                  Ver Detalles
                </Button>
                <Button
                  size="small"
                  component={Link}
                  to={`/create-reservation?restaurant=${restaurant.id}`}
                  sx={{ color: '#ffa69e' }}
                >
                  Nueva Reserva
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {restaurants?.length === 0 && (
        <Box textAlign="center" py={4}>
          <Typography variant="h6" color="text.secondary">
            No se encontraron restaurantes
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Intenta ajustar los filtros de búsqueda
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default RestaurantList;