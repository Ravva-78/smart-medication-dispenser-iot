/**
 * Centralized Application Configuration (Frontend)
 */
export const ENV = {
  API_URL: (typeof process !== 'undefined' && process.env.REACT_APP_API_URL) || (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL) || "http://localhost:8000",
  NODE_ENV: (typeof process !== 'undefined' && process.env.NODE_ENV) || (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.MODE) || 'development',

  // Feature Flags
  FEATURES: {
    ENABLE_CV: false,
    ENABLE_IOT: false,
    ENABLE_AI_SCHEDULER: false,
  },

  // Dashboard Settings
  DASHBOARD: {
    REFRESH_INTERVAL_MS: 30000,
  }
};
