import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token here if needed
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Restaurants API
export const restaurantAPI = {
  getAll: (params = {}) => api.get('/api/restaurants/restaurants/', { params }),
  getById: (id) => api.get(`/api/restaurants/restaurants/${id}/`),
  create: (data) => api.post('/api/restaurants/restaurants/', data),
  update: (id, data) => api.put(`/api/restaurants/restaurants/${id}/`, data),
  partialUpdate: (id, data) => api.patch(`/api/restaurants/restaurants/${id}/`, data),
  delete: (id) => api.delete(`/api/restaurants/restaurants/${id}/`),
};

// Tables API
export const tableAPI = {
  getAll: (params = {}) => api.get('/api/restaurants/tables/', { params }),
  getById: (id) => api.get(`/api/restaurants/tables/${id}/`),
  create: (data) => api.post('/api/restaurants/tables/', data),
  update: (id, data) => api.put(`/api/restaurants/tables/${id}/`, data),
  partialUpdate: (id, data) => api.patch(`/api/restaurants/tables/${id}/`, data),
  delete: (id) => api.delete(`/api/restaurants/tables/${id}/`),
};

// Customers API
export const customerAPI = {
  getAll: (params = {}) => api.get('/api/customers/', { params }),
  getById: (id) => api.get(`/api/customers/${id}/`),
  create: (data) => api.post('/api/customers/', data),
  update: (id, data) => api.put(`/api/customers/${id}/`, data),
  partialUpdate: (id, data) => api.patch(`/api/customers/${id}/`, data),
  delete: (id) => api.delete(`/api/customers/${id}/`),
};

// Reservations API
export const reservationAPI = {
  getAll: (params = {}) => api.get('/api/reservations/', { params }),
  getById: (id) => api.get(`/api/reservations/${id}/`),
  create: (data) => api.post('/api/reservations/', data),
  update: (id, data) => api.put(`/api/reservations/${id}/`, data),
  partialUpdate: (id, data) => api.patch(`/api/reservations/${id}/`, data),
  delete: (id) => api.delete(`/api/reservations/${id}/`),
  cancel: (id) => api.patch(`/api/reservations/${id}/`, { status: 'cancelled' }),
  confirm: (id) => api.patch(`/api/reservations/${id}/`, { status: 'confirmed' }),
  complete: (id) => api.patch(`/api/reservations/${id}/`, { status: 'completed' }),
};

// Notifications API
export const notificationAPI = {
  getAll: (params = {}) => api.get('/api/notifications/notifications/', { params }),
  getById: (id) => api.get(`/api/notifications/notifications/${id}/`),
  create: (data) => api.post('/api/notifications/notifications/', data),
  update: (id, data) => api.put(`/api/notifications/notifications/${id}/`, data),
  partialUpdate: (id, data) => api.patch(`/api/notifications/notifications/${id}/`, data),
  delete: (id) => api.delete(`/api/notifications/notifications/${id}/`),
};

// Notification Templates API
export const notificationTemplateAPI = {
  getAll: (params = {}) => api.get('/api/notifications/templates/', { params }),
  getById: (id) => api.get(`/api/notifications/templates/${id}/`),
  create: (data) => api.post('/api/notifications/templates/', data),
  update: (id, data) => api.put(`/api/notifications/templates/${id}/`, data),
  partialUpdate: (id, data) => api.patch(`/api/notifications/templates/${id}/`, data),
  delete: (id) => api.delete(`/api/notifications/templates/${id}/`),
};

// Notification Preferences API
export const notificationPreferenceAPI = {
  getAll: (params = {}) => api.get('/api/notifications/preferences/', { params }),
  getById: (id) => api.get(`/api/notifications/preferences/${id}/`),
  create: (data) => api.post('/api/notifications/preferences/', data),
  update: (id, data) => api.put(`/api/notifications/preferences/${id}/`, data),
  partialUpdate: (id, data) => api.patch(`/api/notifications/preferences/${id}/`, data),
  delete: (id) => api.delete(`/api/notifications/preferences/${id}/`),
};

export default api;