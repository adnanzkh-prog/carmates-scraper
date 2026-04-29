import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://renewed-adventure-production-fef0.up.railway.app';

const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,  // Reduce from 30000 to 15000 (15 seconds max)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request timeout handling
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('Search timed out. Try a simpler query.'));
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
  return data;
};

export const healthCheck = async () => {
  const { data } = await api.get('/health', { timeout: 5000 });  // Quick health check
  return data;
};

export default api;
