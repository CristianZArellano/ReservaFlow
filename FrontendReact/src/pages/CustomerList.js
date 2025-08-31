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
} from '@mui/material';
import {
  Search,
  Add,
  Edit,
  Delete,
  Person,
  Email,
  Phone,
  Star,
  Event,
  Cancel,
  CheckCircle,
  Warning,
} from '@mui/icons-material';
import { customerAPI } from '../services/api';

const CustomerList = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteDialog, setDeleteDialog] = useState({ open: false, customer: null });

  // Fetch customers with pagination and search
  const { 
    data: customersResponse, 
    isLoading, 
    error 
  } = useQuery(
    ['customers', page, rowsPerPage, searchQuery],
    () => customerAPI.getAll({
      page: page + 1,
      page_size: rowsPerPage,
      search: searchQuery,
    }),
    {
      keepPreviousData: true,
      select: (data) => data.data,
    }
  );

  // Delete mutation
  const deleteMutation = useMutation(
    (customerId) => customerAPI.delete(customerId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('customers');
        setDeleteDialog({ open: false, customer: null });
      },
    }
  );

  const handleSearchChange = (event) => {
    setSearchQuery(event.target.value);
    setPage(0); // Reset to first page on search
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleDeleteClick = (customer) => {
    setDeleteDialog({ open: true, customer });
  };

  const handleDeleteConfirm = () => {
    if (deleteDialog.customer) {
      deleteMutation.mutate(deleteDialog.customer.id);
    }
  };

  const getReliabilityColor = (score) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  const getReliabilityIcon = (score) => {
    if (score >= 80) return <CheckCircle />;
    if (score >= 60) return <Warning />;
    return <Cancel />;
  };

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Error al cargar los clientes: {error.message}
        </Alert>
      </Box>
    );
  }

  const customers = customersResponse?.results || [];
  const totalCustomers = customersResponse?.count || 0;

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Gestión de Clientes
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          component={Link}
          to="/customers/new"
          sx={{ bgcolor: 'primary.main' }}
        >
          Nuevo Cliente
        </Button>
      </Box>

      {/* Search and Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                placeholder="Buscar clientes por nombre, email o teléfono..."
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
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <Typography variant="body2" color="textSecondary">
                  Total: {totalCustomers} clientes
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Customers Table */}
      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <TableContainer>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Cliente</TableCell>
                <TableCell>Contacto</TableCell>
                <TableCell align="center">Reservas</TableCell>
                <TableCell align="center">Confiabilidad</TableCell>
                <TableCell align="center">Estado</TableCell>
                <TableCell align="center">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                // Loading skeletons
                Array.from(new Array(rowsPerPage)).map((_, index) => (
                  <TableRow key={index}>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Skeleton variant="circular" width={40} height={40} />
                        <Box>
                          <Skeleton width={120} />
                          <Skeleton width={160} />
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Skeleton width={100} />
                    </TableCell>
                    <TableCell align="center">
                      <Skeleton width={60} />
                    </TableCell>
                    <TableCell align="center">
                      <Skeleton width={80} />
                    </TableCell>
                    <TableCell align="center">
                      <Skeleton width={70} />
                    </TableCell>
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                        <Skeleton variant="circular" width={32} height={32} />
                        <Skeleton variant="circular" width={32} height={32} />
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              ) : customers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography variant="body1" color="textSecondary">
                      {searchQuery ? 'No se encontraron clientes que coincidan con la búsqueda' : 'No hay clientes registrados'}
                    </Typography>
                    {!searchQuery && (
                      <Button
                        variant="contained"
                        startIcon={<Add />}
                        component={Link}
                        to="/customers/new"
                        sx={{ mt: 2 }}
                      >
                        Agregar Primer Cliente
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ) : (
                customers.map((customer) => (
                  <TableRow key={customer.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Avatar sx={{ bgcolor: 'primary.light' }}>
                          <Person />
                        </Avatar>
                        <Box>
                          <Typography variant="subtitle2" fontWeight="bold">
                            {customer.full_name}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            ID: {customer.id}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    
                    <TableCell>
                      <Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                          <Email fontSize="small" color="action" />
                          <Typography variant="body2">{customer.email}</Typography>
                        </Box>
                        {customer.phone && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Phone fontSize="small" color="action" />
                            <Typography variant="body2">{customer.phone}</Typography>
                          </Box>
                        )}
                      </Box>
                    </TableCell>
                    
                    <TableCell align="center">
                      <Box>
                        <Typography variant="body2" fontWeight="bold">
                          {customer.total_reservations}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          Canceladas: {customer.cancelled_reservations}
                        </Typography>
                        {customer.no_show_count > 0 && (
                          <Typography variant="caption" color="error.main" display="block">
                            No Show: {customer.no_show_count}
                          </Typography>
                        )}
                      </Box>
                    </TableCell>
                    
                    <TableCell align="center">
                      <Tooltip title={`Puntuación: ${customer.reliability_score}/100`}>
                        <Chip
                          icon={getReliabilityIcon(customer.reliability_score)}
                          label={customer.reliability_score}
                          color={getReliabilityColor(customer.reliability_score)}
                          size="small"
                        />
                      </Tooltip>
                    </TableCell>
                    
                    <TableCell align="center">
                      <Chip
                        label={customer.is_active ? 'Activo' : 'Inactivo'}
                        color={customer.is_active ? 'success' : 'default'}
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
                            to={`/customers/${customer.id}`}
                          >
                            <Person />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Editar">
                          <IconButton
                            size="small"
                            color="secondary"
                            component={Link}
                            to={`/customers/${customer.id}/edit`}
                          >
                            <Edit />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Eliminar">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteClick(customer)}
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
          count={totalCustomers}
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
        aria-label="add customer"
        sx={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          display: { xs: 'flex', sm: 'none' },
        }}
        component={Link}
        to="/customers/new"
      >
        <Add />
      </Fab>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, customer: null })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Confirmar Eliminación</DialogTitle>
        <DialogContent>
          <Typography>
            ¿Está seguro que desea eliminar al cliente{' '}
            <strong>{deleteDialog.customer?.full_name}</strong>?
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            Esta acción no se puede deshacer y también eliminará todas las reservas asociadas.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, customer: null })}>
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

export default CustomerList;