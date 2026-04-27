import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// Debug log
if (typeof window !== 'undefined') {
  console.log('API URL:', API_URL);
}

if (!API_URL) {
  console.error('NEXT_PUBLIC_API_URL is not set! Using fallback.');
}

const api = axios.create({
  baseURL: API_URL || 'https://renewed-adventure-production-fef0.up.railway.app',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

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
    console.error('API Error:', error.message);
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('Request timed out. Please try again.'));
    }
    if (!error.response) {
      return Promise.reject(new Error('Network error. Cannot connect to server.'));
    }
    return Promise.reject(error);
  }
);

export const searchCars = async (query, filters = {}) => {
  const params = {
    q: query || '',
    ...filters,
  };
  
  Object.keys(params).forEach(key => {
    if (params[key] === '' || params[key] === null || params[key] === undefined) {
      delete params[key];
    }
  });

  const { data } = await api.get('/search', { params });
  return data;
};

export const healthCheck = async () => {
  const { data } = await api.get('/health');
  return data;
};

export default api;
