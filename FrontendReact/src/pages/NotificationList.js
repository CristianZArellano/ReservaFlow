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
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { es } from 'date-fns/locale';
import {
  Search,
  Add,
  Edit,
  Delete,
  Notifications,
  Email,
  Sms,
  CheckCircle,
  Cancel,
  Schedule,
  Send,
  Visibility,
  MarkEmailRead,
  MarkEmailUnread,
  Warning,
  Info,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { notificationAPI } from '../services/api';
import { format, parseISO } from 'date-fns';


const NotificationList = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFilter, setDateFilter] = useState(null);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, notification: null });

  // Fetch notifications with pagination and filters
  const {
    data: notificationsResponse,
    isLoading,
    error
  } = useQuery(
    ['notifications', page, rowsPerPage, searchQuery, typeFilter, statusFilter, dateFilter],
    () => {
      const params = {
        page: page + 1,
        page_size: rowsPerPage,
      };

      if (searchQuery) params.search = searchQuery;
      if (typeFilter) params.notification_type = typeFilter;
      if (statusFilter) params.status = statusFilter;
      if (dateFilter) params.created_at = format(dateFilter, 'yyyy-MM-dd');

      return notificationAPI.getAll(params);
    },
    {
      keepPreviousData: true,
      select: (data) => data.data,
    }
  );

  // Delete mutation
  const deleteMutation = useMutation(
    (notificationId) => notificationAPI.delete(notificationId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('notifications');
        setDeleteDialog({ open: false, notification: null });
      },
    }
  );

  // Mark as read mutation
  const markAsReadMutation = useMutation(
    (notificationId) => notificationAPI.partialUpdate(notificationId, { read_at: new Date().toISOString() }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('notifications');
      },
    }
  );

  const handleSearchChange = (event) => {
    setSearchQuery(event.target.value);
    setPage(0);
  };

  const handleTypeFilterChange = (event) => {
    setTypeFilter(event.target.value);
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

  const handleDeleteClick = (notification) => {
    setDeleteDialog({ open: true, notification });
  };

  const handleDeleteConfirm = () => {
    if (deleteDialog.notification) {
      deleteMutation.mutate(deleteDialog.notification.id);
    }
  };

  const handleMarkAsRead = (notificationId) => {
    markAsReadMutation.mutate(notificationId);
  };

  const getTypeColor = (type) => {
    const colors = {
      reservation_confirmation: 'success',
      reservation_reminder: 'warning',
      reservation_cancellation: 'error',
      promotional: 'info',
      system: 'default',
    };
    return colors[type] || 'default';
  };

  const getTypeIcon = (type) => {
    const icons = {
      reservation_confirmation: <CheckCircle />,
      reservation_reminder: <Schedule />,
      reservation_cancellation: <Cancel />,
      promotional: <Info />,
      system: <Warning />,
    };
    return icons[type] || <Notifications />;
  };

  const getTypeLabel = (type) => {
    const labels = {
      reservation_confirmation: 'Confirmación',
      reservation_reminder: 'Recordatorio',
      reservation_cancellation: 'Cancelación',
      promotional: 'Promocional',
      system: 'Sistema',
    };
    return labels[type] || type;
  };

  const getStatusColor = (notification) => {
    if (notification.delivered_at && !notification.read_at) return 'warning';
    if (notification.read_at) return 'success';
    return 'default';
  };

  const getStatusLabel = (notification) => {
    if (notification.read_at) return 'Leído';
    if (notification.delivered_at) return 'Entregado';
    return 'Pendiente';
  };

  const getChannelIcon = (channel) => {
    const icons = {
      email: <Email />,
      sms: <Sms />,
      push: <Notifications />,
    };
    return icons[channel] || <Send />;
  };

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Error al cargar las notificaciones: {error.message}
        </Alert>
      </Box>
    );
  }

  const notifications = notificationsResponse?.results || [];
  const totalNotifications = notificationsResponse?.count || 0;

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={es}>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1">
            Gestión de Notificaciones
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            component={Link}
            to="/notifications/new"
            sx={{ bgcolor: 'primary.main' }}
          >
            Nueva Notificación
          </Button>
        </Box>

        {/* Search and Filters */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  placeholder="Buscar notificaciones..."
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
              <Grid item xs={12} md={2}>
                <FormControl fullWidth>
                  <InputLabel>Tipo</InputLabel>
                  <Select
                    value={typeFilter}
                    onChange={handleTypeFilterChange}
                    label="Tipo"
                  >
                    <MenuItem value="">Todos</MenuItem>
                    <MenuItem value="reservation_confirmation">Confirmación</MenuItem>
                    <MenuItem value="reservation_reminder">Recordatorio</MenuItem>
                    <MenuItem value="reservation_cancellation">Cancelación</MenuItem>
                    <MenuItem value="promotional">Promocional</MenuItem>
                    <MenuItem value="system">Sistema</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={2}>
                <FormControl fullWidth>
                  <InputLabel>Estado</InputLabel>
                  <Select
                    value={statusFilter}
                    onChange={handleStatusFilterChange}
                    label="Estado"
                  >
                    <MenuItem value="">Todos</MenuItem>
                    <MenuItem value="pending">Pendiente</MenuItem>
                    <MenuItem value="delivered">Entregado</MenuItem>
                    <MenuItem value="read">Leído</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={3}>
                <DatePicker
                  label="Fecha de creación"
                  value={dateFilter}
                  onChange={handleDateFilterChange}
                  renderInput={(params) => <TextField fullWidth {...params} />}
                />
              </Grid>
              <Grid item xs={12} md={2}>
                <Box sx={{ display: 'flex', alignItems: 'center', height: '100%' }}>
                  <Typography variant="body2" color="textSecondary">
                    Total: {totalNotifications}
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Notifications Table */}
        <Paper sx={{ width: '100%', overflow: 'hidden' }}>
          <TableContainer>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>Notificación</TableCell>
                  <TableCell>Destinatario</TableCell>
                  <TableCell>Canal</TableCell>
                  <TableCell>Tipo</TableCell>
                  <TableCell align="center">Estado</TableCell>
                  <TableCell align="center">Fecha</TableCell>
                  <TableCell align="center">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {isLoading ? (
                  // Loading skeletons
                  Array.from(new Array(rowsPerPage)).map((_, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <Box>
                          <Skeleton width={200} />
                          <Skeleton width={150} />
                        </Box>
                      </TableCell>
                      <TableCell><Skeleton width={120} /></TableCell>
                      <TableCell><Skeleton width={80} /></TableCell>
                      <TableCell><Skeleton width={100} /></TableCell>
                      <TableCell align="center"><Skeleton width={80} /></TableCell>
                      <TableCell align="center"><Skeleton width={100} /></TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                          <Skeleton variant="circular" width={32} height={32} />
                          <Skeleton variant="circular" width={32} height={32} />
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                ) : notifications.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                      <Typography variant="body1" color="textSecondary">
                        {searchQuery || typeFilter || statusFilter || dateFilter
                          ? 'No se encontraron notificaciones que coincidan con los filtros'
                          : 'No hay notificaciones registradas'
                        }
                      </Typography>
                      {!searchQuery && !typeFilter && !statusFilter && !dateFilter && (
                        <Button
                          variant="contained"
                          startIcon={<Add />}
                          component={Link}
                          to="/notifications/new"
                          sx={{ mt: 2 }}
                        >
                          Crear Primera Notificación
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ) : (
                  notifications.map((notification) => (
                    <TableRow key={notification.id} hover>
                      <TableCell>
                        <Box>
                          <Typography variant="subtitle2" fontWeight="bold">
                            {notification.subject}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="textSecondary"
                            sx={{
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                            }}
                          >
                            {notification.message}
                          </Typography>
                        </Box>
                      </TableCell>

                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Avatar sx={{ bgcolor: 'primary.light', width: 32, height: 32 }}>
                            <Notifications fontSize="small" />
                          </Avatar>
                          <Box>
                            <Typography variant="subtitle2">
                              {notification.recipient_name || 'N/A'}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              {notification.recipient}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>

                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getChannelIcon(notification.channel)}
                          <Typography variant="body2" textTransform="capitalize">
                            {notification.channel}
                          </Typography>
                        </Box>
                      </TableCell>

                      <TableCell>
                        <Chip
                          icon={getTypeIcon(notification.notification_type)}
                          label={getTypeLabel(notification.notification_type)}
                          color={getTypeColor(notification.notification_type)}
                          size="small"
                        />
                      </TableCell>

                      <TableCell align="center">
                        <Chip
                          label={getStatusLabel(notification)}
                          color={getStatusColor(notification)}
                          size="small"
                        />
                      </TableCell>

                      <TableCell align="center">
                        <Box>
                          <Typography variant="body2" fontWeight="bold">
                            {format(parseISO(notification.created_at), 'dd/MM/yyyy')}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {format(parseISO(notification.created_at), 'HH:mm')}
                          </Typography>
                        </Box>
                      </TableCell>

                      <TableCell align="center">
                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                          <Tooltip title="Ver detalles">
                            <IconButton
                              size="small"
                              color="primary"
                              component={Link}
                              to={`/notifications/${notification.id}`}
                            >
                              <Visibility />
                            </IconButton>
                          </Tooltip>

                          {!notification.read_at && (
                            <Tooltip title="Marcar como leído">
                              <IconButton
                                size="small"
                                color="success"
                                onClick={() => handleMarkAsRead(notification.id)}
                                disabled={markAsReadMutation.isLoading}
                              >
                                <MarkEmailRead />
                              </IconButton>
                            </Tooltip>
                          )}

                          <Tooltip title="Eliminar">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeleteClick(notification)}
                            >
                              <Delete />
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
            count={totalNotifications}
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
          aria-label="add notification"
          sx={{
            position: 'fixed',
            bottom: 16,
            right: 16,
            display: { xs: 'flex', sm: 'none' },
          }}
          component={Link}
          to="/notifications/new"
        >
          <Add />
        </Fab>

        {/* Delete Confirmation Dialog */}
        <Dialog
          open={deleteDialog.open}
          onClose={() => setDeleteDialog({ open: false, notification: null })}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Confirmar Eliminación</DialogTitle>
          <DialogContent>
            <Typography>
              ¿Está seguro que desea eliminar la notificación{' '}
              <strong>"{deleteDialog.notification?.subject}"</strong>?
            </Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
              Esta acción no se puede deshacer.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialog({ open: false, notification: null })}>
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
    </LocalizationProvider>
  );
};

export default NotificationList;
