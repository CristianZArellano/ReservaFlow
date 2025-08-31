import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Button,
  IconButton,
  Chip,
  TextField,
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Tooltip,
  Avatar,
  Card,
  CardContent,
  Grid,
  Skeleton,
  Fab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';

import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { es } from 'date-fns/locale';

import {
  Search,
  Add,
  Edit,
  Delete,
  Person,
  Restaurant,
  Event,
  Schedule,
  Cancel,
  CheckCircle,
  Warning,
  Pending,
  Group,
  Visibility,
  EventAvailable,
  EventBusy,
} from '@mui/icons-material';

import { reservationAPI } from '../services/api';
import { format, parseISO } from 'date-fns';

const ReservationList = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFilter, setDateFilter] = useState(null);
  const [cancelDialog, setCancelDialog] = useState({ open: false, reservation: null });

  // Fetch reservations with pagination and filters
  const {
    data: reservationsResponse,
    isLoading,
    error
  } = useQuery(
    ['reservations', page, rowsPerPage, searchQuery, statusFilter, dateFilter],
    () => {
      const params = {
        page: page + 1,
        page_size: rowsPerPage,
      };

      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (dateFilter) params.reservation_date = format(dateFilter, 'yyyy-MM-dd');

      return reservationAPI.getAll(params);
    },
    {
      keepPreviousData: true,
      select: (data) => data.data,
    }
  );

  // Cancel mutation
  const cancelMutation = useMutation(
    (reservationId) => reservationAPI.cancel(reservationId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('reservations');
        setCancelDialog({ open: false, reservation: null });
      },
    }
  );

  // Confirm mutation
  const confirmMutation = useMutation(
    (reservationId) => reservationAPI.confirm(reservationId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('reservations');
      },
    }
  );

  const handleSearchChange = (event) => {
    setSearchQuery(event.target.value);
    setPage(0);
  };

  const handleStatusFilterChange = (event) => {
    setStatusFilter(event.target.value);
    setPage(0);
  };

  const handleDateFilterChange = (date) => {
    setDateFilter(date);
    setPage(0);
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleCancelClick = (reservation) => {
    setCancelDialog({ open: true, reservation });
  };

  const handleCancelConfirm = () => {
    if (cancelDialog.reservation) {
      cancelMutation.mutate(cancelDialog.reservation.id);
    }
  };

  const handleConfirmReservation = (reservationId) => {
    confirmMutation.mutate(reservationId);
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

  const getStatusIcon = (status) => {
    const icons = {
      pending: <Pending />,
      confirmed: <CheckCircle />,
      completed: <EventAvailable />,
      cancelled: <Cancel />,
      no_show: <EventBusy />,
      expired: <Warning />,
    };
    return icons[status] || <Event />;
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

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Error al cargar las reservas: {error.message}
        </Alert>
      </Box>
    );
  }

  const reservations = reservationsResponse?.results || [];
  const totalReservations = reservationsResponse?.count || 0;

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={es}>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1">
            Gestión de Reservas
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            component={Link}
            to="/create-reservation"
            sx={{ bgcolor: 'primary.main' }}
          >
            Nueva Reserva
          </Button>
        </Box>

        {/* Search and Filters */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  placeholder="Buscar por cliente, restaurante o ID..."
                  value={searchQuery}
                  onChange={handleSearchChange}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Search />
                      </InputAdornment>
                    ),
                  }}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Estado</InputLabel>
                  <Select
                    value={statusFilter}
                    onChange={handleStatusFilterChange}
                    label="Estado"
                  >
                    <MenuItem value="">Todos</MenuItem>
                    <MenuItem value="pending">Pendiente</MenuItem>
                    <MenuItem value="confirmed">Confirmada</MenuItem>
                    <MenuItem value="completed">Completada</MenuItem>
                    <MenuItem value="cancelled">Cancelada</MenuItem>
                    <MenuItem value="no_show">No Show</MenuItem>
                    <MenuItem value="expired">Expirada</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={3}>
                <DatePicker
                  label="Fecha de reserva"
                  value={dateFilter}
                  onChange={handleDateFilterChange}
                  renderInput={(params) => <TextField fullWidth {...params} />}
                />
              </Grid>
              <Grid item xs={12} md={2}>
                <Box sx={{ display: 'flex', alignItems: 'center', height: '100%' }}>
                  <Typography variant="body2" color="textSecondary">
                    Total: {totalReservations}
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Reservations Table */}
        <Paper sx={{ width: '100%', overflow: 'hidden' }}>
          <TableContainer>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>Reserva</TableCell>
                  <TableCell>Cliente</TableCell>
                  <TableCell>Restaurante</TableCell>
                  <TableCell align="center">Fecha & Hora</TableCell>
                  <TableCell align="center">Personas</TableCell>
                  <TableCell align="center">Estado</TableCell>
                  <TableCell align="center">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {isLoading ? (
                  // Loading skeletons
                  Array.from(new Array(rowsPerPage)).map((_, index) => (
                    <TableRow key={index}>
                      <TableCell><Skeleton width={120} /></TableCell>
                      <TableCell><Skeleton width={150} /></TableCell>
                      <TableCell><Skeleton width={130} /></TableCell>
                      <TableCell align="center"><Skeleton width={100} /></TableCell>
                      <TableCell align="center"><Skeleton width={60} /></TableCell>
                      <TableCell align="center"><Skeleton width={80} /></TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                          <Skeleton variant="circular" width={32} height={32} />
                          <Skeleton variant="circular" width={32} height={32} />
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                ) : reservations.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                      <Typography variant="body1" color="textSecondary">
                        {searchQuery || statusFilter || dateFilter
                          ? 'No se encontraron reservas que coincidan con los filtros'
                          : 'No hay reservas registradas'
                        }
                      </Typography>
                      {!searchQuery && !statusFilter && !dateFilter && (
                        <Button
                          variant="contained"
                          startIcon={<Add />}
                          component={Link}
                          to="/create-reservation"
                          sx={{ mt: 2 }}
                        >
                          Crear Primera Reserva
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ) : (
                  reservations.map((reservation) => (
                    <TableRow key={reservation.id} hover>
                      <TableCell>
                        <Box>
                          <Typography variant="subtitle2" fontWeight="bold">
                            #{reservation.id.toString().slice(-8)}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {format(parseISO(reservation.created_at), 'dd/MM/yyyy HH:mm')}
                          </Typography>
                        </Box>
                      </TableCell>

                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Avatar sx={{ bgcolor: 'primary.light', width: 32, height: 32 }}>
                            <Person fontSize="small" />
                          </Avatar>
                          <Box>
                            <Typography variant="subtitle2">
                              {reservation.customer?.full_name || 'Cliente no disponible'}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              {reservation.customer?.email}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>

                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Avatar sx={{ bgcolor: 'secondary.light', width: 32, height: 32 }}>
                            <Restaurant fontSize="small" />
                          </Avatar>
                          <Box>
                            <Typography variant="subtitle2">
                              {reservation.restaurant?.name || 'Restaurante no disponible'}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              Mesa {reservation.table?.number || 'N/A'}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>

                      <TableCell align="center">
                        <Box>
                          <Typography variant="body2" fontWeight="bold">
                            {format(parseISO(reservation.reservation_date + 'T00:00:00'), 'dd/MM/yyyy')}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {reservation.reservation_time}
                          </Typography>
                        </Box>
                      </TableCell>

                      <TableCell align="center">
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                          <Group fontSize="small" color="action" />
                          <Typography variant="body2" fontWeight="bold">
                            {reservation.party_size}
                          </Typography>
                        </Box>
                      </TableCell>

                      <TableCell align="center">
                        <Chip
                          icon={getStatusIcon(reservation.status)}
                          label={getStatusLabel(reservation.status)}
                          color={getStatusColor(reservation.status)}
                          size="small"
                        />
                      </TableCell>

                      <TableCell align="center">
                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
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

                          {reservation.status === 'pending' && (
                            <Tooltip title="Confirmar">
                              <IconButton
                                size="small"
                                color="success"
                                onClick={() => handleConfirmReservation(reservation.id)}
                                disabled={confirmMutation.isLoading}
                              >
                                <CheckCircle />
                              </IconButton>
                            </Tooltip>
                          )}

                          {['pending', 'confirmed'].includes(reservation.status) && (
                            <Tooltip title="Cancelar">
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => handleCancelClick(reservation)}
                              >
                                <Cancel />
                              </IconButton>
                            </Tooltip>
                          )}

                          <Tooltip title="Editar">
                            <IconButton
                              size="small"
                              color="secondary"
                              component={Link}
                              to={`/reservations/${reservation.id}/edit`}
                              disabled={['cancelled', 'completed', 'no_show'].includes(reservation.status)}
                            >
                              <Edit />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            rowsPerPageOptions={[5, 10, 25, 50]}
            component="div"
            count={totalReservations}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            labelRowsPerPage="Filas por página:"
            labelDisplayedRows={({ from, to, count }) =>
              `${from}-${to} de ${count !== -1 ? count : `más de ${to}`}`
            }
          />
        </Paper>

        {/* Floating Action Button for mobile */}
        <Fab
          color="primary"
          aria-label="add reservation"
          sx={{
            position: 'fixed',
            bottom: 16,
            right: 16,
            display: { xs: 'flex', sm: 'none' },
          }}
          component={Link}
          to="/create-reservation"
        >
          <Add />
        </Fab>

        {/* Cancel Confirmation Dialog */}
        <Dialog
          open={cancelDialog.open}
          onClose={() => setCancelDialog({ open: false, reservation: null })}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Confirmar Cancelación</DialogTitle>
          <DialogContent>
            <Typography>
              ¿Está seguro que desea cancelar la reserva{' '}
              <strong>#{cancelDialog.reservation?.id.toString().slice(-8)}</strong>?
            </Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
              Esta acción enviará una notificación al cliente y liberará la mesa.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCancelDialog({ open: false, reservation: null })}>
              No Cancelar
            </Button>
            <Button
              onClick={handleCancelConfirm}
              color="error"
              variant="contained"
              disabled={cancelMutation.isLoading}
            >
              {cancelMutation.isLoading ? 'Cancelando...' : 'Confirmar Cancelación'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
};

export default ReservationList;
