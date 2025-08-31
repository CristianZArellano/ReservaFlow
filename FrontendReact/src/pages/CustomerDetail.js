import React from 'react';
import { useParams } from 'react-router-dom';
import { Typography, Box } from '@mui/material';

const CustomerDetail = () => {
  const { id } = useParams();
  
  return (
    <Box>
      <Typography variant="h4">Detalles del Cliente {id}</Typography>
      <Typography>En desarrollo...</Typography>
    </Box>
  );
};

export default CustomerDetail;