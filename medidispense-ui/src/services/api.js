/**
 * MEDI-DISPENSE — centralized API configuration
 *
 * All pages and components that communicate with the backend should
 * import API_BASE from this file rather than declaring their own constant.
 *
 * Backend mounts routes at the root level (no /api prefix):
 *   GET  /patients
 *   GET  /medications
 *   GET  /devices
 *   GET  /alerts
 *   etc.
 */
export const API_BASE = "http://localhost:8000";
