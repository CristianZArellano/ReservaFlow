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
  Person as PersonIcon,
  Phone,
  Email,
  CalendarToday,
  EventAvailable,
  Restaurant,
  Schedule,
  Add,
  Visibility,
} from '@mui/icons-material';
import { customerAPI, reservationAPI } from '../services/api';
import { format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';

const CustomerDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [editDialog, setEditDialog] = useState({ open: false, data: {} });
  const [deleteDialog, setDeleteDialog] = useState({ open: false });

  // Fetch customer data
  const { 
    data: customer, 
    isLoading: loadingCustomer, 
    error: customerError 
  } = useQuery(
    ['customer', id],
    () => customerAPI.getById(id),
    {
      select: (data) => data.data,
    }
  );

  // Fetch customer reservations
  const { 
    data: reservations, 
    isLoading: loadingReservations 
  } = useQuery(
    ['customer-reservations', id],
    () => reservationAPI.getAll({ customer: id }),
    {
      enabled: !!id,
      select: (data) => data.data.results || [],
    }
  );

  // Update mutation
  const updateMutation = useMutation(
    (updateData) => customerAPI.update(id, updateData),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['customer', id]);
        setEditDialog({ open: false, data: {} });
      },
    }
  );

  // Delete mutation
  const deleteMutation = useMutation(
    () => customerAPI.delete(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('customers');
        navigate('/customers');
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

  if (loadingCustomer) {
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

  if (customerError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Error al cargar el cliente: {customerError.message}
        </Alert>
      </Box>
    );
  }

  if (!customer) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">
          Cliente no encontrado
        </Alert>
      </Box>
    );
  }

  const totalReservations = reservations?.length || 0;
  const confirmedReservations = reservations?.filter(r => r.status === 'confirmed').length || 0;
  const completedReservations = reservations?.filter(r => r.status === 'completed').length || 0;
  const cancelledReservations = reservations?.filter(r => r.status === 'cancelled').length || 0;

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/customers')}
            sx={{ mr: 2, color: '#5e6472' }}
          >
            Volver
          </Button>
          <Avatar sx={{ bgcolor: '#ffa69e', mr: 2, width: 48, height: 48 }}>
            <PersonIcon />
          </Avatar>
          <Box>
            <Typography variant="h4" component="h1" sx={{ color: '#5e6472' }}>
              {customer.first_name} {customer.last_name}
            </Typography>
            <Typography variant="subtitle1" color="textSecondary">
              Cliente desde {format(parseISO(customer.created_at), 'MMMM yyyy', { locale: es })}
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            startIcon={<Add />}
            component={Link}
            to={`/reservations/new?customer=${customer.id}`}
            sx={{ bgcolor: '#b8f2e6', color: '#5e6472', '&:hover': { bgcolor: '#aed9e0' } }}
          >
            Nueva Reserva
          </Button>
          <IconButton
            color="primary"
            onClick={() => setEditDialog({ open: true, data: { ...customer } })}
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
                Información Personal
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <PersonIcon sx={{ mr: 2, color: '#ffa69e' }} />
                    <Box>
                      <Typography variant="subtitle2" color="textSecondary">
                        Nombre Completo
                      </Typography>
                      <Typography variant="body1">
                        {customer.first_name} {customer.last_name}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Email sx={{ mr: 2, color: '#ffa69e' }} />
                    <Box>
                      <Typography variant="subtitle2" color="textSecondary">
                        Correo Electrónico
                      </Typography>
                      <Typography variant="body1">
                        {customer.email}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Phone sx={{ mr: 2, color: '#ffa69e' }} />
                    <Box>
                      <Typography variant="subtitle2" color="textSecondary">
                        Teléfono
                      </Typography>
                      <Typography variant="body1">
                        {customer.phone || 'No registrado'}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <CalendarToday sx={{ mr: 2, color: '#ffa69e' }} />
                    <Box>
                      <Typography variant="subtitle2" color="textSecondary">
                        Fecha de Nacimiento
                      </Typography>
                      <Typography variant="body1">
                        {customer.date_of_birth ? format(parseISO(customer.date_of_birth), 'dd/MM/yyyy', { locale: es }) : 'No registrada'}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                {customer.dietary_preferences && (
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Restaurant sx={{ mr: 2, color: '#ffa69e' }} />
                      <Box>
                        <Typography variant="subtitle2" color="textSecondary">
                          Preferencias Dietéticas
                        </Typography>
                        <Typography variant="body1">
                          {customer.dietary_preferences}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>
                )}
                {customer.special_requests && (
                  <Grid item xs={12}>
                    <Box>
                      <Typography variant="subtitle2" color="textSecondary" sx={{ mb: 1 }}>
                        Solicitudes Especiales
                      </Typography>
                      <Paper sx={{ p: 2, bgcolor: '#faf3dd' }}>
                        <Typography variant="body1">
                          {customer.special_requests}
                        </Typography>
                      </Paper>
                    </Box>
                  </Grid>
                )}
              </Grid>
            </CardContent>
          </Card>

          {/* Reservations History */}
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ color: '#5e6472' }}>
                  Historial de Reservas ({totalReservations})
                </Typography>
              </Box>

              {loadingReservations ? (
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Restaurante</TableCell>
                      <TableCell>Mesa</TableCell>
                      <TableCell align="center">Fecha</TableCell>
                      <TableCell align="center">Estado</TableCell>
                      <TableCell align="center">Acciones</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Array.from(new Array(3)).map((_, index) => (
                      <TableRow key={index}>
                        <TableCell><Skeleton width={120} /></TableCell>
                        <TableCell><Skeleton width={80} /></TableCell>
                        <TableCell align="center"><Skeleton width={100} /></TableCell>
                        <TableCell align="center"><Skeleton width={80} /></TableCell>
                        <TableCell align="center"><Skeleton width={60} /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : reservations && reservations.length > 0 ? (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Restaurante</TableCell>
                        <TableCell>Mesa</TableCell>
                        <TableCell align="center">Fecha</TableCell>
                        <TableCell align="center">Hora</TableCell>
                        <TableCell align="center">Personas</TableCell>
                        <TableCell align="center">Estado</TableCell>
                        <TableCell align="center">Acciones</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {reservations.map((reservation) => (
                        <TableRow key={reservation.id} hover>
                          <TableCell>
                            <Typography variant="subtitle2">
                              {reservation.restaurant?.name || 'N/A'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              Mesa {reservation.table?.number || 'N/A'}
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Typography variant="body2">
                              {format(parseISO(reservation.reservation_date), 'dd/MM/yyyy', { locale: es })}
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Typography variant="body2">
                              {reservation.reservation_time}
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Typography variant="body2">
                              {reservation.party_size}
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Chip
                              label={getStatusLabel(reservation.status)}
                              color={getStatusColor(reservation.status)}
                              size="small"
                            />
                          </TableCell>
                          <TableCell align="center">
                            <Tooltip title="Ver detalles">
                              <IconButton
                                size="small"
                                color="primary"
                                component={Link}
                                to={`/reservations/${reservation.id}`}
                              >
                                <Visibility />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <EventAvailable sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                  <Typography variant="body1" color="textSecondary">
                    No hay reservas registradas
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<Add />}
                    component={Link}
                    to={`/reservations/new?customer=${customer.id}`}
                    sx={{ mt: 2 }}
                  >
                    Crear Primera Reserva
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          {/* Statistics */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ color: '#5e6472' }}>
                Estadísticas
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#faf3dd', borderRadius: 1 }}>
                    <Typography variant="h4" sx={{ color: '#ffa69e', fontWeight: 'bold' }}>
                      {totalReservations}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Total Reservas
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#b8f2e6', borderRadius: 1 }}>
                    <Typography variant="h4" sx={{ color: '#5e6472', fontWeight: 'bold' }}>
                      {completedReservations}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Completadas
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#aed9e0', borderRadius: 1 }}>
                    <Typography variant="h4" sx={{ color: '#5e6472', fontWeight: 'bold' }}>
                      {confirmedReservations}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Confirmadas
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#ffa69e', borderRadius: 1 }}>
                    <Typography variant="h4" sx={{ color: 'white', fontWeight: 'bold' }}>
                      {cancelledReservations}
                    </Typography>
                    <Typography variant="body2" sx={{ color: 'white' }}>
                      Canceladas
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Customer Info */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ color: '#5e6472' }}>
                Información Adicional
              </Typography>
              <List>
                <ListItem disablePadding>
                  <ListItemText
                    primary="Cliente desde"
                    secondary={format(parseISO(customer.created_at), 'dd/MM/yyyy', { locale: es })}
                  />
                </ListItem>
                <Divider />
                <ListItem disablePadding>
                  <ListItemText
                    primary="Última actualización"
                    secondary={format(parseISO(customer.updated_at), 'dd/MM/yyyy HH:mm', { locale: es })}
                  />
                </ListItem>
                {customer.loyalty_points && (
                  <>
                    <Divider />
                    <ListItem disablePadding>
                      <ListItemText
                        primary="Puntos de Lealtad"
                        secondary={customer.loyalty_points}
                      />
                    </ListItem>
                  </>
                )}
              </List>
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
        <DialogTitle>Editar Cliente</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Nombre"
                value={editDialog.data.first_name || ''}
                onChange={(e) => setEditDialog(prev => ({
                  ...prev,
                  data: { ...prev.data, first_name: e.target.value }
                }))}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Apellido"
                value={editDialog.data.last_name || ''}
                onChange={(e) => setEditDialog(prev => ({
                  ...prev,
                  data: { ...prev.data, last_name: e.target.value }
                }))}
              />
            </Grid>
            <Grid item xs={12}>
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
                label="Fecha de Nacimiento"
                type="date"
                value={editDialog.data.date_of_birth || ''}
                onChange={(e) => setEditDialog(prev => ({
                  ...prev,
                  data: { ...prev.data, date_of_birth: e.target.value }
                }))}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Preferencias Dietéticas"
                value={editDialog.data.dietary_preferences || ''}
                onChange={(e) => setEditDialog(prev => ({
                  ...prev,
                  data: { ...prev.data, dietary_preferences: e.target.value }
                }))}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Solicitudes Especiales"
                multiline
                rows={3}
                value={editDialog.data.special_requests || ''}
                onChange={(e) => setEditDialog(prev => ({
                  ...prev,
                  data: { ...prev.data, special_requests: e.target.value }
                }))}
              />
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
            ¿Está seguro que desea eliminar el cliente{' '}
            <strong>"{customer.first_name} {customer.last_name}"</strong>?
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            Esta acción eliminará también todas las reservas asociadas.
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

export default CustomerDetail;