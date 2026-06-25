// frontend/src/api/client.ts
import axios from 'axios';

// Dynamic API URL - uses the current host (works for both localhost and remote access)
const getBaseUrl = () => {
  // If running in development, use localhost
  if (import.meta.env.DEV) {
    return 'http://localhost:8000';
  }
  
  // In production, use the current window location
  // This makes it work whether accessed from localhost or remote IP
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  const port = window.location.port || '8000';
  
  return `${protocol}//${hostname}:${port}`;
};

const apiClient = axios.create({
  baseURL: getBaseUrl(),
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`📡 API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('❌ API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default apiClient;
