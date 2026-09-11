/**
 * Global Notification Service
 * Allows triggering toast notifications from anywhere in the application.
 */

class NotificationService {
  constructor() {
    this.listeners = new Set();
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  notify(message, variant = 'success') {
    for (const listener of this.listeners) {
      listener({ message, variant });
    }
  }

  success(message) {
    this.notify(message, 'success');
  }

  error(message) {
    this.notify(message, 'error');
  }

  warning(message) {
    this.notify(message, 'warning');
  }

  info(message) {
    this.notify(message, 'info');
  }
}

export const notifier = new NotificationService();
