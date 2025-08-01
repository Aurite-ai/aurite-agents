import { useEffect } from 'react';

/**
 * Custom hook to handle ResizeObserver loop errors
 * This prevents the "ResizeObserver loop completed with undelivered notifications" error
 * that commonly occurs during drag operations in React Flow
 */
export const useResizeObserverErrorHandler = () => {
  useEffect(() => {
    // Store the original error handler
    const originalError = console.error;
    const originalWarn = console.warn;

    // Override console.error to suppress ResizeObserver errors
    console.error = (...args) => {
      const message = args[0];
      if (
        typeof message === 'string' &&
        (message.includes('ResizeObserver loop completed with undelivered notifications') ||
         message.includes('ResizeObserver loop limit exceeded'))
      ) {
        // Suppress ResizeObserver loop errors
        return;
      }
      originalError.apply(console, args);
    };

    // Override console.warn to suppress ResizeObserver warnings
    console.warn = (...args) => {
      const message = args[0];
      if (
        typeof message === 'string' &&
        message.includes('ResizeObserver')
      ) {
        // Suppress ResizeObserver warnings
        return;
      }
      originalWarn.apply(console, args);
    };

    // Restore original handlers on cleanup
    return () => {
      console.error = originalError;
      console.warn = originalWarn;
    };
  }, []);
}; 