//* frontend/src/api/client.ts
import axios from 'axios';

// Dynamic API URL - uses the current host (works for both localhost and remote access)
const getBaseUrl = () => {
  if (import.meta.env.DEV) {
    return 'http://localhost:8000';
  }
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  const port = window.location.port || '8000';
  return `${protocol}//${hostname}:${port}`;
};

// Single apiClient instance with auth support
const apiClient = axios.create({
  baseURL: getBaseUrl(),
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Gate: ensures auto-key fetch completes before any request proceeds
let keyReady: Promise<void>;

keyReady = (async () => {
  try {
    const stored = localStorage.getItem('mai-rag-api-key');
    if (!stored) {
      // Fetch auto-generated key from backend
      const res = await axios.get(`${getBaseUrl()}/api/auth/auto-key`);
      if (res.data?.api_key) {
        localStorage.setItem('mai-rag-api-key', res.data.api_key);
        console.log('API key auto-retrieved and stored');
      }
    }
  } catch (err) {
    console.warn('Auto-key fetch failed:', err);
  }
})();

// Request interceptor: attach API key + debug logging
apiClient.interceptors.request.use(
  async (config) => {
    // Wait for auto-key fetch to complete before sending any request
    await keyReady;

    const apiKey = localStorage.getItem('mai-rag-api-key');
    if (apiKey) {
      config.headers['X-API-Key'] = apiKey;
    }
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401/403 + error logging
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);

    // Remove the prompt - just log the error
    // Users will see clear error messages instead of key prompts

    return Promise.reject(error);
  }
);

export default apiClient;
