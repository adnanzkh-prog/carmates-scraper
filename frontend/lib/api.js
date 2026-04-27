// frontend/lib/api.js
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// Debug: log the API URL (remove in production)
if (typeof window !== 'undefined') {
  console.log('API URL:', API_URL);
}

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url, config.params);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.data);
    return response;
  },
  (error) => {
    console.error('API Error:', error.message, error.response?.status, error.response?.data);
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('Request timed out. Please try again.'));
    }
    if (error.response?.status === 429) {
      return Promise.reject(new Error('Too many requests. Please wait.'));
    }
    if (error.response?.status >= 500) {
      return Promise.reject(new Error('Server error. Please try again later.'));
    }
    if (!error.response) {
      return Promise.reject(new Error('Cannot connect to server. Check your connection.'));
    }
    return Promise.reject(error);
  }
);

export const searchCars = async (query, filters = {}) => {
  const params = {
    q: query || '',
    ...filters,
  };
  
  // Remove empty values
  Object.keys(params).forEach(key => {
    if (params[key] === '' || params[key] === null || params[key] === undefined) {
      delete params[key];
    }
  });

  const { data } = await api.get('/search', { params });
  
  // Backend returns { results: [...], total: N }
  // Return the full response so page can access results and total
  return data;
};

export const healthCheck = async () => {
  const { data } = await api.get('/health');
  return data;
};

export default api;
