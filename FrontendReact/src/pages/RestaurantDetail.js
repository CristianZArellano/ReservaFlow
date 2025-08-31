import React from 'react';
import { useParams } from 'react-router-dom';
import { Typography, Box } from '@mui/material';

const RestaurantDetail = () => {
  const { id } = useParams();
  
  return (
    <Box>
      <Typography variant="h4">Detalles del Restaurante {id}</Typography>
      <Typography>En desarrollo...</Typography>
    </Box>
  );
};

export default RestaurantDetail;