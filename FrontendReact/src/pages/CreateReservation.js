import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
  Paper,
  Chip,
} from '@mui/material';
import { DatePicker, TimePicker } from '@mui/x-date-pickers';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs from 'dayjs';
import {
  Restaurant,
  Person,
  Schedule,
  TableRestaurant,
  Save,
  ArrowBack,
} from '@mui/icons-material';
import {
  restaurantAPI,
  tableAPI,
  customerAPI,
  reservationAPI,
} from '../services/api';

const CreateReservation = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const preselectedRestaurant = searchParams.get('restaurant');

  const [activeStep, setActiveStep] = useState(0);
  const [formData, setFormData] = useState({
    customer_id: '',
    restaurant_id: preselectedRestaurant || '',
    table_id: '',
    reservation_date: dayjs(),
    reservation_time: dayjs().hour(19).minute(0),
    party_size: 2,
    special_requests: '',
  });
  const [errors, setErrors] = useState({});

  const steps = ['Seleccionar Restaurante', 'Elegir Mesa', 'Datos del Cliente', 'Confirmar Reserva'];

  // Fetch data
  const { data: restaurants, isLoading: loadingRestaurants } = useQuery(
    'restaurants',
    () => restaurantAPI.getAll(),
    {
      select: (data) => data.data.results,
    }
  );

  const { data: tables, isLoading: loadingTables } = useQuery(
    ['tables', formData.restaurant_id],
    () => tableAPI.getAll({ restaurant: formData.restaurant_id }),
    {
      enabled: !!formData.restaurant_id,
      select: (data) => data.data.results,
    }
  );

  const { data: customers, isLoading: loadingCustomers } = useQuery(
    'customers',
    () => customerAPI.getAll(),
    {
      select: (data) => data.data.results,
    }
  );

  const createReservationMutation = useMutation(
    (reservationData) => reservationAPI.create(reservationData),
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries('reservations');
        navigate(`/reservations/${data.data.id}`);
      },
      onError: (error) => {
        setErrors(error.response?.data || { general: 'Error al crear la reserva' });
      },
    }
  );

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: null,
      }));
    }
  };

  const handleNext = () => {
    setActiveStep(prev => prev + 1);
  };

  const handleBack = () => {
    setActiveStep(prev => prev - 1);
  };

  const handleSubmit = () => {
    const reservationData = {
      customer_id: parseInt(formData.customer_id),
      restaurant_id: parseInt(formData.restaurant_id),
      table_id: parseInt(formData.table_id),
      reservation_date: formData.reservation_date.format('YYYY-MM-DD'),
      reservation_time: formData.reservation_time.format('HH:mm:ss'),
      party_size: parseInt(formData.party_size),
      special_requests: formData.special_requests,
    };

    createReservationMutation.mutate(reservationData);
  };

  const getStepContent = (step) => {
    switch (step) {
      case 0:
        return (
          <Box>
            <Typography variant="h6" sx={{ mb: 3, color: '#5e6472' }}>
              Selecciona un Restaurante
            </Typography>
            <Grid container spacing={2}>
              {loadingRestaurants ? (
                <Grid item xs={12}>
                  <Box display="flex" justifyContent="center">
                    <CircularProgress />
                  </Box>
                </Grid>
              ) : (
                restaurants?.map((restaurant) => (
                  <Grid item xs={12} md={6} key={restaurant.id}>
                    <Card 
                      sx={{ 
                        cursor: 'pointer',
                        border: formData.restaurant_id == restaurant.id ? 
                          '2px solid #ffa69e' : '1px solid #b8f2e6',
                        '&:hover': {
                          boxShadow: '0 4px 16px rgba(94, 100, 114, 0.2)',
                        },
                      }}
                      onClick={() => handleInputChange('restaurant_id', restaurant.id)}
                    >
                      <CardContent>
                        <Typography variant="h6" sx={{ color: '#5e6472' }}>
                          {restaurant.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {restaurant.description?.substring(0, 80)}...
                        </Typography>
                        <Box display="flex" gap={1} mb={1}>
                          <Chip 
                            label={restaurant.cuisine_type} 
                            size="small" 
                            sx={{ bgcolor: '#aed9e0', color: '#5e6472' }}
                          />
                          <Chip 
                            label={restaurant.price_range} 
                            size="small" 
                            sx={{ bgcolor: '#b8f2e6', color: '#5e6472' }}
                          />
                        </Box>
                        <Typography variant="body2" color="text.secondary">
                          {restaurant.opening_time} - {restaurant.closing_time}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))
              )}
            </Grid>
          </Box>
        );

      case 1:
        return (
          <Box>
            <Typography variant="h6" sx={{ mb: 3, color: '#5e6472' }}>
              Selecciona una Mesa
            </Typography>
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={6}>
                <DatePicker
                  label="Fecha de la Reserva"
                  value={formData.reservation_date}
                  onChange={(value) => handleInputChange('reservation_date', value)}
                  renderInput={(params) => <TextField {...params} fullWidth />}
                  minDate={dayjs()}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TimePicker
                  label="Hora de la Reserva"
                  value={formData.reservation_time}
                  onChange={(value) => handleInputChange('reservation_time', value)}
                  renderInput={(params) => <TextField {...params} fullWidth />}
                />
              </Grid>
            </Grid>
            
            <Grid container spacing={2}>
              {loadingTables ? (
                <Grid item xs={12}>
                  <Box display="flex" justifyContent="center">
                    <CircularProgress />
                  </Box>
                </Grid>
              ) : (
                tables?.filter(table => table.capacity >= formData.party_size).map((table) => (
                  <Grid item xs={12} sm={6} md={4} key={table.id}>
                    <Card 
                      sx={{ 
                        cursor: 'pointer',
                        border: formData.table_id == table.id ? 
                          '2px solid #ffa69e' : '1px solid #b8f2e6',
                        '&:hover': {
                          boxShadow: '0 4px 16px rgba(94, 100, 114, 0.2)',
                        },
                      }}
                      onClick={() => handleInputChange('table_id', table.id)}
                    >
                      <CardContent>
                        <Typography variant="h6" sx={{ color: '#5e6472' }}>
                          Mesa {table.number}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Capacidad: {table.capacity} personas
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Ubicación: {table.location}
                        </Typography>
                        {table.has_view && (
                          <Chip 
                            label="Con vista" 
                            size="small" 
                            sx={{ bgcolor: '#b8f2e6', color: '#5e6472', mt: 1 }}
                          />
                        )}
                        {table.is_accessible && (
                          <Chip 
                            label="Accesible" 
                            size="small" 
                            sx={{ bgcolor: '#aed9e0', color: '#5e6472', mt: 1, ml: 1 }}
                          />
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                ))
              )}
            </Grid>
          </Box>
        );

      case 2:
        return (
          <Box>
            <Typography variant="h6" sx={{ mb: 3, color: '#5e6472' }}>
              Información del Cliente
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Cliente</InputLabel>
                  <Select
                    value={formData.customer_id}
                    label="Cliente"
                    onChange={(e) => handleInputChange('customer_id', e.target.value)}
                    error={!!errors.customer_id}
                  >
                    {customers?.map((customer) => (
                      <MenuItem key={customer.id} value={customer.id}>
                        {customer.first_name} {customer.last_name} - {customer.email}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Número de Personas"
                  type="number"
                  value={formData.party_size}
                  onChange={(e) => handleInputChange('party_size', e.target.value)}
                  error={!!errors.party_size}
                  helperText={errors.party_size}
                  inputProps={{ min: 1, max: 12 }}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Solicitudes Especiales"
                  multiline
                  rows={3}
                  value={formData.special_requests}
                  onChange={(e) => handleInputChange('special_requests', e.target.value)}
                  placeholder="Ej: Mesa cerca de la ventana, celebración especial, alergias alimentarias..."
                />
              </Grid>
            </Grid>
          </Box>
        );

      case 3:
        const selectedRestaurant = restaurants?.find(r => r.id == formData.restaurant_id);
        const selectedTable = tables?.find(t => t.id == formData.table_id);
        const selectedCustomer = customers?.find(c => c.id == formData.customer_id);

        return (
          <Box>
            <Typography variant="h6" sx={{ mb: 3, color: '#5e6472' }}>
              Confirmar Reserva
            </Typography>
            <Paper sx={{ p: 3, bgcolor: '#faf3dd' }}>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: '#5e6472' }}>
                    Restaurante: {selectedRestaurant?.name}
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="body1">
                    Mesa: {selectedTable?.number} (Capacidad: {selectedTable?.capacity})
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="body1">
                    Cliente: {selectedCustomer?.first_name} {selectedCustomer?.last_name}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body1">
                    Fecha: {formData.reservation_date.format('DD/MM/YYYY')}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body1">
                    Hora: {formData.reservation_time.format('HH:mm')}
                  </Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="body1">
                    Número de personas: {formData.party_size}
                  </Typography>
                </Grid>
                {formData.special_requests && (
                  <Grid item xs={12}>
                    <Typography variant="body1">
                      Solicitudes especiales: {formData.special_requests}
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </Paper>
          </Box>
        );

      default:
        return 'Unknown step';
    }
  };

  const isStepValid = (step) => {
    switch (step) {
      case 0:
        return !!formData.restaurant_id;
      case 1:
        return !!formData.table_id && formData.reservation_date && formData.reservation_time;
      case 2:
        return !!formData.customer_id && formData.party_size > 0;
      default:
        return true;
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <Box>
        <Box display="flex" alignItems="center" mb={3}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/reservations')}
            sx={{ mr: 2, color: '#5e6472' }}
          >
            Volver
          </Button>
          <Typography variant="h4" component="h1" sx={{ color: '#5e6472' }}>
            Nueva Reserva
          </Typography>
        </Box>

        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {errors.general && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {errors.general}
          </Alert>
        )}

        <Card>
          <CardContent sx={{ p: 4 }}>
            {getStepContent(activeStep)}

            <Box display="flex" justifyContent="space-between" mt={4}>
              <Button
                disabled={activeStep === 0}
                onClick={handleBack}
                sx={{ color: '#5e6472' }}
              >
                Anterior
              </Button>
              
              <Box>
                {activeStep === steps.length - 1 ? (
                  <Button
                    variant="contained"
                    onClick={handleSubmit}
                    disabled={createReservationMutation.isLoading}
                    startIcon={createReservationMutation.isLoading ? <CircularProgress size={20} /> : <Save />}
                  >
                    {createReservationMutation.isLoading ? 'Creando...' : 'Crear Reserva'}
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    onClick={handleNext}
                    disabled={!isStepValid(activeStep)}
                  >
                    Siguiente
                  </Button>
                )}
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </LocalizationProvider>
  );
};

export default CreateReservation;