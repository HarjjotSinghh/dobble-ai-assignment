/**
 * API Service - Centralized HTTP client for backend communication.
 */

import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth APIs
export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
};

// Chat APIs
export const chatAPI = {
  sendMessage: (message, sessionId) =>
    api.post('/chat/', { message, session_id: sessionId }),
  getSessions: () => api.get('/chat/sessions'),
};

// Appointment APIs
export const appointmentAPI = {
  getDoctors: () => api.get('/appointments/doctors'),
  getMyAppointments: (status) =>
    api.get('/appointments/my-appointments', { params: { status } }),
  getDoctorStats: (dateFrom, dateTo) =>
    api.get('/appointments/doctor-stats', { params: { date_from: dateFrom, date_to: dateTo } }),
};

// Notification APIs
export const notificationAPI = {
  getNotifications: (unreadOnly) =>
    api.get('/notifications/', { params: { unread_only: unreadOnly } }),
  markAsRead: (id) => api.put(`/notifications/${id}/read`),
  markAllRead: () => api.put('/notifications/read-all'),
};

export default api;
