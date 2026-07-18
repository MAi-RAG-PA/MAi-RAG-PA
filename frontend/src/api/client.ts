//* frontend/src/api/client.ts
import axios, { AxiosInstance } from 'axios';

// Reliable dynamic API URL
const getBaseUrl = () => {
  if (import.meta.env.DEV) {
    return 'http://localhost:8000';
  }
  // window.location.origin is much more reliable than manual parsing
  return window.location.origin;
};

const apiClient: AxiosInstance = axios.create({
  baseURL: getBaseUrl(),
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

const API_KEY_STORAGE_NAME = 'mai-rag-api-key';

// Key fetching logic
let keyReady: Promise<void>;
let fetchingKey = false;

async function fetchApiKey(): Promise<void> {
  const baseUrl = getBaseUrl();

  if (fetchingKey) {
    // If another fetch is already in progress, just wait for it
    return new Promise<void>((resolve, reject) => {
      const check = () => {
        const stored = localStorage.getItem(API_KEY_STORAGE_NAME);
        if (stored) {
          resolve();
        } else {
          // If the first fetch eventually fails, this will also fail
          setTimeout(check, 200);
        }
      };
      check();
    });
  }

  fetchingKey = true;

  try {
    const res = await axios.get(`${baseUrl}/api/auth/auto-key`);
    if (!res.data?.api_key) {
      throw new Error('Backend responded, but no api_key found in response');
    }
    localStorage.setItem(API_KEY_STORAGE_NAME, res.data.api_key);
  } finally {
    fetchingKey = false;
  }
}

// Initialize keyReady
keyReady = (async () => {
  const stored = localStorage.getItem(API_KEY_STORAGE_NAME);
  if (stored) {
    return;
  }

  // Try to fetch with a small retry loop
  const maxAttempts = 5;
  const delayMs = 1000;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      await fetchApiKey();
      const again = localStorage.getItem(API_KEY_STORAGE_NAME);
      if (again) {
        return;
      }
    } catch (err: any) {
      console.warn(`[apikey] Auto-key fetch attempt ${attempt} failed:`, err.message);
      if (attempt < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    }
  }

  // If we still don't have a key, we still "resolve" but log clearly
  console.error('[apikey] CRITICAL: Could not retrieve API key after multiple attempts.');
})();

// Request interceptor
apiClient.interceptors.request.use(
  async (config) => {
    // Ensure key is ready before sending the request
    await keyReady;

    const apiKey = localStorage.getItem(API_KEY_STORAGE_NAME);
    if (apiKey) {
      config.headers['X-API-Key'] = apiKey;
    } else {
      console.warn('[apikey] Sending request WITHOUT API key because it is still null!');
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: Auto-retry once if we get a 401 (key might have just been generated)
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (!originalRequest) {
      return Promise.reject(error);
    }

    // If we get a 401 and haven't retried yet, try fetching the key and retrying
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      console.log('[apikey] Got 401, attempting to fetch API key and retry...');

      try {
        await fetchApiKey();
        const newKey = localStorage.getItem(API_KEY_STORAGE_NAME);
        if (newKey) {
          originalRequest.headers['X-API-Key'] = newKey;
          return apiClient(originalRequest); // Retry the original request
        }
      } catch (retryErr: any) {
        console.error('[apikey] Retry fetch failed:', retryErr.message);
      }
    }

    console.error('[api] API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default apiClient;
