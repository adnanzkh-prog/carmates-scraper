// lib/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('Search timed out. Please try again.'));
    }
    if (error.response?.status === 429) {
      return Promise.reject(new Error('Too many requests. Please wait a moment.'));
    }
    return Promise.reject(error);
  }
);

export const searchCars = async (filters) => {
  const { data } = await api.get('/search', { params: filters });
  return data;
};

export default api;
