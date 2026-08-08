import axios from 'axios';

const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL !== undefined && import.meta.env.VITE_API_URL !== '') {
    return import.meta.env.VITE_API_URL.replace(/\/$/, '');
  }
  // When running in local development environment, default to local backend port 8000
  if (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    return 'http://localhost:8000';
  }
  return 'https://rag-backend-fe1u.onrender.com';
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
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

// Response interceptor with enhanced network error diagnostics
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response && (error.code === 'ERR_NETWORK' || error.message === 'Network Error')) {
      console.error(
        `[Network Error] Unable to communicate with backend API server at ${error.config?.baseURL || API_BASE_URL}. ` +
        `Please ensure your backend FastAPI server is running on port 8000.`
      );
    }
    return Promise.reject(error);
  }
);

export default api;
