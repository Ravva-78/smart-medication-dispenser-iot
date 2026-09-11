/**
 * Centralized Logging Utility (Frontend)
 */
import { ENV } from '../config/env';

const getTimestamp = () => new Date().toLocaleTimeString();

export const logger = {
  info: (message, meta = {}) => {
    console.log(`[INFO] [${getTimestamp()}] ${message}`, Object.keys(meta).length ? meta : '');
  },
  warn: (message, meta = {}) => {
    console.warn(`[WARN] [${getTimestamp()}] ${message}`, Object.keys(meta).length ? meta : '');
  },
  error: (message, error = null) => {
    console.error(`[ERROR] [${getTimestamp()}] ${message}`, error ? error : '');
  },
  debug: (message, meta = {}) => {
    if (ENV.NODE_ENV === 'development') {
      console.debug(`[DEBUG] [${getTimestamp()}] ${message}`, Object.keys(meta).length ? meta : '');
    }
  }
};
