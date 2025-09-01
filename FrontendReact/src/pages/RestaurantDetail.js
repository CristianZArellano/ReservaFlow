import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  IconButton,
  Chip,
  Avatar,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Divider,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack,
  Edit,
  Delete,
  Restaurant as RestaurantIcon,
  Phone,
  Email,
  LocationOn,
  Schedule,
  AttachMoney,
  Kitchen,
  TableRestaurant,
  Add,
  Visibility,
  EventAvailable,
} from '@mui/icons-material';
import { restaurantAPI, tableAPI, reservationAPI } from '../services/api';
import { format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';

const RestaurantDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [editDialog, setEditDialog] = useState({ open: false, data: {} });
  const [deleteDialog, setDeleteDialog] = useState({ open: false });

  // Fetch restaurant data
  const { 
    data: restaurant, 
    isLoading: loadingRestaurant, 
    error: restaurantError 
  } = useQuery(
    ['restaurant', id],
    () => restaurantAPI.getById(id),
    {
      select: (data) => data.data,
    }
  );

  // Fetch restaurant tables
  const { 
    data: tables, 
    isLoading: loadingTables 
  } = useQuery(
    ['tables', id],
    () => tableAPI.getAll({ restaurant: id }),
    {
      enabled: !!id,
      select: (data) => data.data.results || [],
    }
  );

  // Fetch recent reservations for this restaurant
  const { 
    data: recentReservations, 
    isLoading: loadingReservations 
  } = useQuery(
    ['restaurant-reservations', id],
    () => reservationAPI.getAll({ restaurant: id, page_size: 5 }),
    {
      enabled: !!id,
      select: (data) => data.data.results || [],
    }
  );

  // Update mutation
  const updateMutation = useMutation(
    (updateData) => restaurantAPI.update(id, updateData),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['restaurant', id]);
        setEditDialog({ open: false, data: {} });
      },
    }
  );

  // Delete mutation
  const deleteMutation = useMutation(
    () => restaurantAPI.delete(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('restaurants');
        navigate('/restaurants');
      },
    }
  );

  const handleEditSave = () => {
    updateMutation.mutate(editDialog.data);
  };

  const handleDeleteConfirm = () => {
    deleteMutation.mutate();
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'warning',
      confirmed: 'success',
      completed: 'info',
      cancelled: 'error',
      no_show: 'error',
      expired: 'default',
    };
    return colors[status] || 'default';
  };

  const getStatusLabel = (status) => {
    const labels = {
      pending: 'Pendiente',
      confirmed: 'Confirmada',
      completed: 'Completada',
      cancelled: 'Cancelada',
      no_show: 'No Show',
      expired: 'Expirada',
    };
    return labels[status] || status;
  };

  if (loadingRestaurant) {
    return (
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <Skeleton variant="rectangular" width={40} height={40} sx={{ mr: 2 }} />
          <Skeleton width={300} height={40} />
        </Box>
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Skeleton variant="rectangular" height={300} />
          </Grid>
          <Grid item xs={12} md={4}>
            <Skeleton variant="rectangular" height={200} />
          </Grid>
        </Grid>
      </Box>
    );
  }

  if (restaurantError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Error al cargar el restaurante: {restaurantError.message}
        </Alert>
      </Box>
    );
  }

  if (!restaurant) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">
          Restaurante no encontrado
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/restaurants')}
            sx={{ mr: 2, color: '#5e6472' }}
          >
            Volver
          </Button>
          <Avatar sx={{ bgcolor: '#ffa69e', mr: 2, width: 48, height: 48 }}>
            <RestaurantIcon />
          </Avatar>
          <Box>
            <Typography variant="h4" component="h1" sx={{ color: '#5e6472' }}>
              {restaurant.name}
            </Typography>
            <Typography variant="subtitle1" color="textSecondary">
              {restaurant.cuisine_type} • {restaurant.price_range}
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            startIcon={<Add />}
            component={Link}
            to={`/reservations/new?restaurant=${restaurant.id}`}
            sx={{ bgcolor: '#b8f2e6', color: '#5e6472', '&:hover': { bgcolor: '#aed9e0' } }}
          >
            Nueva Reserva
          </Button>
          <IconButton
            color="primary"
            onClick={() => setEditDialog({ open: true, data: { ...restaurant } })}
          >
            <Edit />
          </IconButton>
          <IconButton
            color="error"
            onClick={() => setDeleteDialog({ open: true })}
          >
            <Delete />
          </IconButton>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Main Information */}
        <Grid item xs={12} md={8}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ color: '#5e6472' }}>
                Información General
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Typography variant="body1" paragraph>
                    {restaurant.description}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <LocationOn sx={{ mr: 1, color: '#ffa69e' }} />
                    <Typography variant="body2">
                      {restaurant.address}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Phone sx={{ mr: 1, color: '#ffa69e' }} />
                    <Typography variant="body2">
                      {restaurant.phone}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Email sx={{ mr: 1, color: '#ffa69e' }} />
                    <Typography variant="body2">
                      {restaurant.email}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Schedule sx={{ mr: 1, color: '#ffa69e' }} />
                    <Typography variant="body2">
                      {restaurant.opening_time} - {restaurant.closing_time}
                    </Typography>
                  </Box>
                </Grid>
              </Grid>

              <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip 
                  icon={<Kitchen />}
                  label={restaurant.cuisine_type} 
                  sx={{ bgcolor: '#b8f2e6', color: '#5e6472' }}
                />
                <Chip 
                  icon={<AttachMoney />}
                  label={restaurant.price_range} 
                  sx={{ bgcolor: '#aed9e0', color: '#5e6472' }}
                />
                <Chip 
                  label={`${restaurant.total_tables || 0} Mesas`} 
                  sx={{ bgcolor: '#faf3dd', color: '#5e6472' }}
                />
                {restaurant.accepts_reservations && (
                  <Chip 
                    icon={<EventAvailable />}
                    label="Acepta Reservas" 
                    color="success" 
                    size="small"
                  />
                )}
              </Box>
            </CardContent>
          </Card>

          {/* Tables */}
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ color: '#5e6472' }}>
                  Mesas ({tables?.length || 0})
                </Typography>
                <Button
                  startIcon={<Add />}
                  size="small"
                  component={Link}
                  to={`/restaurants/${id}/tables/new`}
                >
                  Agregar Mesa
                </Button>
              </Box>

              {loadingTables ? (
                <Grid container spacing={2}>
                  {Array.from(new Array(6)).map((_, index) => (
                    <Grid item xs={12} sm={6} md={4} key={index}>
                      <Skeleton variant="rectangular" height={100} />
                    </Grid>
                  ))}
                </Grid>
              ) : tables && tables.length > 0 ? (
                <Grid container spacing={2}>
                  {tables.map((table) => (
                    <Grid item xs={12} sm={6} md={4} key={table.id}>
                      <Paper 
                        sx={{ 
                          p: 2, 
                          bgcolor: '#faf3dd',
                          border: '1px solid #b8f2e6',
                          '&:hover': {
                            boxShadow: '0 4px 12px rgba(94, 100, 114, 0.15)',
                          },
                        }}
                      >
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="h6" sx={{ color: '#5e6472' }}>
                            Mesa {table.number}
                          </Typography>
                          <Box>
                            <IconButton 
                              size="small" 
                              component={Link} 
                              to={`/tables/${table.id}`}
                            >
                              <Visibility />
                            </IconButton>
                          </Box>
                        </Box>
                        <Typography variant="body2" color="textSecondary">
                          Capacidad: {table.capacity} personas
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          Ubicación: {table.location}
                        </Typography>
                        <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                          {table.has_view && (
                            <Chip label="Vista" size="small" sx={{ bgcolor: '#b8f2e6', color: '#5e6472' }} />
                          )}
                          {table.is_accessible && (
                            <Chip label="Accesible" size="small" sx={{ bgcolor: '#aed9e0', color: '#5e6472' }} />
                          )}
                        </Box>
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              ) : (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <TableRestaurant sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                  <Typography variant="body1" color="textSecondary">
                    No hay mesas registradas
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<Add />}
                    component={Link}
                    to={`/restaurants/${id}/tables/new`}
                    sx={{ mt: 2 }}
                  >
                    Agregar Primera Mesa
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          {/* Recent Reservations */}
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ color: '#5e6472' }}>
                  Reservas Recientes
                </Typography>
                <Button
                  size="small"
                  component={Link}
                  to={`/reservations?restaurant=${id}`}
                >
                  Ver Todas
                </Button>
              </Box>

              {loadingReservations ? (
                <List>
                  {Array.from(new Array(3)).map((_, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <Skeleton variant="circular" width={24} height={24} />
                      </ListItemIcon>
                      <ListItemText
                        primary={<Skeleton width="60%" />}
                        secondary={<Skeleton width="40%" />}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : recentReservations && recentReservations.length > 0 ? (
                <List>
                  {recentReservations.map((reservation, index) => (
                    <React.Fragment key={reservation.id}>
                      <ListItemButton
                        component={Link}
                        to={`/reservations/${reservation.id}`}
                      >
                        <ListItemIcon>
                          <Avatar sx={{ bgcolor: '#b8f2e6', width: 32, height: 32 }}>
                            <EventAvailable fontSize="small" sx={{ color: '#5e6472' }} />
                          </Avatar>
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant="subtitle2">
                                Mesa {reservation.table?.number}
                              </Typography>
                              <Chip 
                                label={getStatusLabel(reservation.status)}
                                color={getStatusColor(reservation.status)}
                                size="small"
                              />
                            </Box>
                          }
                          secondary={
                            <Typography variant="body2" color="textSecondary">
                              {format(parseISO(reservation.reservation_date), 'dd/MM/yyyy', { locale: es })} - {reservation.reservation_time}
                            </Typography>
                          }
                        />
                      </ListItemButton>
                      {index < recentReservations.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Box sx={{ textAlign: 'center', py: 3 }}>
                  <EventAvailable sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
                  <Typography variant="body2" color="textSecondary">
                    No hay reservas recientes
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Edit Dialog */}
      <Dialog
        open={editDialog.open}
        onClose={() => setEditDialog({ open: false, data: {} })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Editar Restaurante</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Nombre"
                value={editDialog.data.name || ''}
                onChange={(e) => setEditDialog(prev => ({
                  ...prev,
                  data: { ...prev.data, name: e.target.value }
                }))}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Descripción"
                multiline
                rows={3}
                value={editDialog.data.description || ''}
                onChange={(e) => setEditDialog(prev => ({
                  ...prev,
                  data: { ...prev.data, description: e.target.value }
                }))}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Teléfono"
                value={editDialog.data.phone || ''}
                onChange={(e) => setEditDialog(prev => ({
                  ...prev,
                  data: { ...prev.data, phone: e.target.value }
                }))}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Email"
                type="email"
                value={editDialog.data.email || ''}
                onChange={(e) => setEditDialog(prev => ({
                  ...prev,
                  data: { ...prev.data, email: e.target.value }
                }))}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Dirección"
                value={editDialog.data.address || ''}
                onChange={(e) => setEditDialog(prev => ({
                  ...prev,
                  data: { ...prev.data, address: e.target.value }
                }))}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Tipo de Cocina</InputLabel>
                <Select
                  value={editDialog.data.cuisine_type || ''}
                  label="Tipo de Cocina"
                  onChange={(e) => setEditDialog(prev => ({
                    ...prev,
                    data: { ...prev.data, cuisine_type: e.target.value }
                  }))}
                >
                  <MenuItem value="italiana">Italiana</MenuItem>
                  <MenuItem value="mexicana">Mexicana</MenuItem>
                  <MenuItem value="china">China</MenuItem>
                  <MenuItem value="japonesa">Japonesa</MenuItem>
                  <MenuItem value="francesa">Francesa</MenuItem>
                  <MenuItem value="española">Española</MenuItem>
                  <MenuItem value="argentina">Argentina</MenuItem>
                  <MenuItem value="internacional">Internacional</MenuItem>
                  <MenuItem value="vegetariana">Vegetariana</MenuItem>
                  <MenuItem value="otra">Otra</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Rango de Precios</InputLabel>
                <Select
                  value={editDialog.data.price_range || ''}
                  label="Rango de Precios"
                  onChange={(e) => setEditDialog(prev => ({
                    ...prev,
                    data: { ...prev.data, price_range: e.target.value }
                  }))}
                >
                  <MenuItem value="$">$ - Económico</MenuItem>
                  <MenuItem value="$$">$$ - Moderado</MenuItem>
                  <MenuItem value="$$$">$$$ - Caro</MenuItem>
                  <MenuItem value="$$$$">$$$$ - Muy Caro</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialog({ open: false, data: {} })}>
            Cancelar
          </Button>
          <Button
            onClick={handleEditSave}
            variant="contained"
            disabled={updateMutation.isLoading}
          >
            {updateMutation.isLoading ? 'Guardando...' : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Confirmar Eliminación</DialogTitle>
        <DialogContent>
          <Typography>
            ¿Está seguro que desea eliminar el restaurante{' '}
            <strong>"{restaurant.name}"</strong>?
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            Esta acción eliminará también todas las mesas y reservas asociadas.
            No se puede deshacer.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false })}>
            Cancelar
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="error"
            variant="contained"
            disabled={deleteMutation.isLoading}
          >
            {deleteMutation.isLoading ? 'Eliminando...' : 'Eliminar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RestaurantDetail;