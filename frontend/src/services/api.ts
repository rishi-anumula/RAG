import axios from 'axios';

const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL !== undefined && import.meta.env.VITE_API_URL !== '') {
    return import.meta.env.VITE_API_URL.replace(/\/$/, '');
  }
  return 'https://rag-backend-6ozj.onrender.com';
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Request interceptor to attach bearer token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('rag_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Simple response pass-through interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error);
  }
);

export default api;
