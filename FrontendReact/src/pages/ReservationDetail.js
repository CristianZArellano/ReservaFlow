import React from 'react';
import { useParams } from 'react-router-dom';
import { Typography, Box } from '@mui/material';

const ReservationDetail = () => {
  const { id } = useParams();
  
  return (
    <Box>
      <Typography variant="h4">Detalles de la Reserva {id}</Typography>
      <Typography>En desarrollo...</Typography>
    </Box>
  );
};

export default ReservationDetail;