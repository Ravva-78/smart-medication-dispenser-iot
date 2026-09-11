import { ENV } from '../config/env';
import { logger } from '../utils/logger';

/**
 * Centralized API Client
 * Wraps fetch to provide standard error handling and JSON parsing.
 */
class ApiClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const controller = new AbortController();
    const timeout = options.timeout || 12000;
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const response = await fetch(url, {
        ...options,
        signal: options.signal || controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorMsg = 'An error occurred';
        try {
          const errorData = await response.json();
          errorMsg = errorData.detail || errorData.error || errorData.message || errorMsg;
        } catch (e) {
          // Response wasn't JSON
          errorMsg = response.statusText;
        }
        throw new Error(errorMsg);
      }

      // Check for empty 204 No Content
      if (response.status === 204) return null;
      
      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      logger.error(`API Error on ${options.method || 'GET'} ${endpoint}:`, error);
      throw error;
    }
  }

  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  post(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  put(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  patch(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient(ENV.API_URL);
