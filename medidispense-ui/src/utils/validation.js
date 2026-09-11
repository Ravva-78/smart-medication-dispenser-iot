/**
 * Centralized Validation Utilities (Frontend)
 */

export const isRequired = (value) => {
  if (value === undefined || value === null) return false;
  if (typeof value === 'string' && value.trim() === '') return false;
  return true;
};

export const isValidTimeFormat = (value) => {
  if (!value || value === "—") return true; // Optional or empty
  return /^\d{1,2}:\d{2}$/.test(value.trim());
};

export const validateForm = (data, requiredFields) => {
  const errors = {};
  for (const field of requiredFields) {
    if (!isRequired(data[field])) {
      errors[field] = true;
    }
  }
  return errors;
};
