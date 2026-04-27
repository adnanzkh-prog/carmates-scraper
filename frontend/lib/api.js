import axios from 'axios';

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

  // Hard coded API call
  const response = await axios.get('https://renewed-adventure-production-fef0.up.railway.app/search', {
    params
  });
  return response.data;
};

export const healthCheck = async () => {
  const response = await axios.get('https://renewed-adventure-production-fef0.up.railway.app/health');
  return response.data;
};
