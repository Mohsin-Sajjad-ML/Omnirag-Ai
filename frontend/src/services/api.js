import axios from 'axios';

// API Base URL configuration:
// - In production / same-origin single-port mode (FastAPI serving frontend on port 8000 or ngrok tunnel),
//   API_BASE_URL defaults to '' (relative paths, e.g. /auth/login, /documents, /chat/sessions).
//   Because frontend and backend share the exact same origin and port, no CORS configuration or
//   environment-variable URL is needed.
// - In local development (standalone Vite dev server on port 5173/5174), it falls back to
//   http://localhost:8000 (or uses the .env-based VITE_API_BASE_URL override).
const getApiBaseUrl = () => {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '').trim();

  // In development mode (Vite dev server, e.g. port 5173/5174)
  if (import.meta.env.DEV) {
    if (envUrl) return envUrl;
    if (typeof window !== 'undefined' && window.location.port !== '8000') {
      return `${window.location.protocol}//${window.location.hostname}:8000`;
    }
    return 'http://localhost:8000';
  }

  // In production mode (built static files served by FastAPI or deployed):
  // When served from the same origin, API calls use relative paths ('').
  // Keep envUrl as an override only if explicitly pointing to an external remote host (not localhost).
  if (envUrl && !envUrl.includes('localhost:8000') && !envUrl.includes('127.0.0.1:8000')) {
    return envUrl;
  }

  return '';
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

let clerkTokenGetter = null;

export const setClerkTokenGetter = (getToken) => {
  clerkTokenGetter = getToken;
};

api.interceptors.request.use(async (config) => {
  if (clerkTokenGetter) {
    const token = await clerkTokenGetter();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export default api;
