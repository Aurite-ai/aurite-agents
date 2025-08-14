/**
 * Error handling utilities for UI applications
 *
 * This module provides utilities for handling API errors in user interfaces,
 * including error categorization, user-friendly messaging, and retry logic.
 */

import { ApiError, ErrorCategory, ErrorSeverity, TimeoutError, CancellationError } from '../types';

/**
 * Error display configuration for UI components
 */
export interface ErrorDisplayConfig {
  /** Whether to show technical details to users */
  showTechnicalDetails?: boolean;
  /** Whether to show retry buttons for retryable errors */
  showRetryButton?: boolean;
  /** Custom error messages by category */
  customMessages?: Partial<Record<ErrorCategory, string>>;
  /** Whether to auto-dismiss certain error types */
  autoDismiss?: {
    enabled: boolean;
    categories: ErrorCategory[];
    delay: number;
  };
}

/**
 * Error notification data for UI display
 */
export interface ErrorNotification {
  /** Unique identifier for the error */
  id: string;
  /** User-friendly title */
  title: string;
  /** User-friendly message */
  message: string;
  /** Error severity level */
  severity: ErrorSeverity;
  /** Error category */
  category: ErrorCategory;
  /** Whether this error can be retried */
  retryable: boolean;
  /** Suggested retry delay in milliseconds */
  retryDelay?: number | undefined;
  /** Whether this notification should auto-dismiss */
  autoDismiss: boolean;
  /** Auto-dismiss delay in milliseconds */
  autoDismissDelay?: number | undefined;
  /** Technical details (only shown if configured) */
  technicalDetails?: any;
  /** Original error object */
  originalError: ApiError | TimeoutError | CancellationError;
}

/**
 * Default error display configuration
 */
const DEFAULT_ERROR_CONFIG: ErrorDisplayConfig = {
  showTechnicalDetails: false,
  showRetryButton: true,
  autoDismiss: {
    enabled: true,
    categories: [ErrorCategory.VALIDATION, ErrorCategory.NOT_FOUND],
    delay: 5000,
  },
};

/**
 * Converts an API error to a user-friendly notification
 */
export function createErrorNotification(
  error: ApiError | TimeoutError | CancellationError | Error,
  config: ErrorDisplayConfig = DEFAULT_ERROR_CONFIG
): ErrorNotification {
  // Generate unique ID
  const id = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  // Handle non-API errors
  if (
    !(error instanceof ApiError) &&
    !(error instanceof TimeoutError) &&
    !(error instanceof CancellationError)
  ) {
    return {
      id,
      title: 'Unexpected Error',
      message: 'An unexpected error occurred. Please try again.',
      severity: ErrorSeverity.ERROR,
      category: ErrorCategory.UNKNOWN,
      retryable: false,
      autoDismiss: false,
      technicalDetails: config.showTechnicalDetails ? { message: error.message } : undefined,
      originalError: new ApiError(error.message || 'Unknown error', 0),
    };
  }

  const apiError = error as ApiError;

  // Get custom message if configured
  const customMessage = config.customMessages?.[apiError.category];
  const message = customMessage || apiError.getDisplayMessage();

  // Determine if should auto-dismiss
  const shouldAutoDismiss =
    config.autoDismiss?.enabled && config.autoDismiss.categories.includes(apiError.category);

  return {
    id,
    title: getErrorTitle(apiError.category),
    message,
    severity: apiError.severity,
    category: apiError.category,
    retryable: apiError.retryable && Boolean(config.showRetryButton ?? true),
    retryDelay: apiError.retryDelay,
    autoDismiss: shouldAutoDismiss ?? false,
    autoDismissDelay: shouldAutoDismiss ? config.autoDismiss?.delay : undefined,
    technicalDetails: config.showTechnicalDetails ? apiError.toJSON() : undefined,
    originalError: apiError,
  };
}

/**
 * Gets appropriate title for error category
 */
function getErrorTitle(category: ErrorCategory): string {
  switch (category) {
    case ErrorCategory.NETWORK:
      return 'Connection Error';
    case ErrorCategory.AUTH:
      return 'Authentication Error';
    case ErrorCategory.VALIDATION:
      return 'Validation Error';
    case ErrorCategory.SERVER:
      return 'Server Error';
    case ErrorCategory.TIMEOUT:
      return 'Request Timeout';
    case ErrorCategory.CANCELLED:
      return 'Request Cancelled';
    case ErrorCategory.RATE_LIMIT:
      return 'Rate Limit Exceeded';
    case ErrorCategory.NOT_FOUND:
      return 'Not Found';
    default:
      return 'Error';
  }
}

/**
 * Determines the appropriate UI color/theme for an error severity
 */
export function getErrorColor(severity: ErrorSeverity): string {
  switch (severity) {
    case ErrorSeverity.INFO:
      return 'blue';
    case ErrorSeverity.WARNING:
      return 'yellow';
    case ErrorSeverity.ERROR:
      return 'red';
    case ErrorSeverity.CRITICAL:
      return 'red';
    default:
      return 'gray';
  }
}

/**
 * Determines the appropriate icon for an error category
 */
export function getErrorIcon(category: ErrorCategory): string {
  switch (category) {
    case ErrorCategory.NETWORK:
      return '🌐';
    case ErrorCategory.AUTH:
      return '🔒';
    case ErrorCategory.VALIDATION:
      return '⚠️';
    case ErrorCategory.SERVER:
      return '🔧';
    case ErrorCategory.TIMEOUT:
      return '⏱️';
    case ErrorCategory.CANCELLED:
      return '❌';
    case ErrorCategory.RATE_LIMIT:
      return '🚦';
    case ErrorCategory.NOT_FOUND:
      return '🔍';
    default:
      return '❗';
  }
}

/**
 * Retry handler with exponential backoff
 */
export class RetryHandler {
  private retryCount = 0;
  private maxRetries: number;
  private baseDelay: number;

  constructor(maxRetries = 3, baseDelay = 1000) {
    this.maxRetries = maxRetries;
    this.baseDelay = baseDelay;
  }

  /**
   * Executes a function with retry logic
   */
  async execute<T>(fn: () => Promise<T>, shouldRetry?: (error: any) => boolean): Promise<T> {
    while (this.retryCount <= this.maxRetries) {
      try {
        const result = await fn();
        this.retryCount = 0; // Reset on success
        return result;
      } catch (error) {
        this.retryCount++;

        // Check if we should retry
        const canRetry = this.retryCount <= this.maxRetries;
        const errorAllowsRetry = error instanceof ApiError ? error.shouldRetry() : false;
        const customRetryLogic = shouldRetry ? shouldRetry(error) : true;

        if (!canRetry || !errorAllowsRetry || !customRetryLogic) {
          this.retryCount = 0; // Reset for next use
          throw error;
        }

        // Calculate delay with exponential backoff
        const delay =
          error instanceof ApiError
            ? error.getRetryDelay()
            : this.baseDelay * Math.pow(2, this.retryCount - 1);

        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    throw new Error('Maximum retries exceeded');
  }

  /**
   * Resets the retry counter
   */
  reset(): void {
    this.retryCount = 0;
  }

  /**
   * Gets current retry count
   */
  getCurrentRetryCount(): number {
    return this.retryCount;
  }
}

/**
 * Error boundary helper for React-like error handling
 */
export class ErrorBoundary {
  private errorHandlers: Array<(_error: Error, _errorInfo?: any) => void> = [];

  /**
   * Adds an error handler
   */
  addErrorHandler(handler: (_error: Error, _errorInfo?: any) => void): void {
    this.errorHandlers.push(handler);
  }

  /**
   * Removes an error handler
   */
  removeErrorHandler(handler: (_error: Error, _errorInfo?: any) => void): void {
    const index = this.errorHandlers.indexOf(handler);
    if (index > -1) {
      this.errorHandlers.splice(index, 1);
    }
  }

  /**
   * Handles an error by calling all registered handlers
   */
  handleError(error: Error, errorInfo?: any): void {
    this.errorHandlers.forEach(handler => {
      try {
        handler(error, errorInfo);
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error('Error in error handler:', e);
      }
    });
  }

  /**
   * Wraps a function to catch and handle errors
   */
  wrap<T extends (...args: any[]) => any>(fn: T): T {
    return ((...args: any[]) => {
      try {
        const result = fn(...args);

        // Handle async functions
        if (result instanceof Promise) {
          return result.catch(e => {
            this.handleError(e);
            throw e;
          });
        }

        return result;
      } catch (e) {
        this.handleError(e as Error);
        throw e;
      }
    }) as T;
  }
}

/**
 * Logs errors with structured information for debugging
 */
export function logError(error: Error | ApiError, context?: string): void {
  const timestamp = new Date().toISOString();

  if (error instanceof ApiError) {
    // eslint-disable-next-line no-console
    console.error('API Error:', {
      timestamp,
      context,
      error: error.toJSON(),
    });
  } else {
    // eslint-disable-next-line no-console
    console.error('API Error:', {
      timestamp,
      context,
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
    });
  }
}

/**
 * Global error boundary instance
 */
export const globalErrorBoundary = new ErrorBoundary();
