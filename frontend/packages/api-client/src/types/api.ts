/**
 * Core API configuration and client types
 */

/**
 * Configuration for the API client
 */
export interface ApiConfig {
  /** Base URL of the Aurite API (e.g., http://localhost:8000) */
  baseUrl: string;
  /** API key for authentication */
  apiKey: string;
}

/**
 * Request options for API calls
 */
export interface RequestOptions {
  /** Request timeout in milliseconds */
  timeout?: number;
  /** Number of retry attempts */
  retries?: number;
  /** Delay between retries in milliseconds */
  retryDelay?: number;
  /** AbortSignal for request cancellation */
  signal?: AbortSignal;
}

/**
 * Error categories for better error handling in UI applications
 */
export enum ErrorCategory {
  /** Network connectivity issues */

  NETWORK = 'network',
  /** Authentication/authorization failures */

  AUTH = 'auth',
  /** Client-side validation errors */

  VALIDATION = 'validation',
  /** Server-side errors */

  SERVER = 'server',
  /** Request timeout */

  TIMEOUT = 'timeout',
  /** Request was cancelled */

  CANCELLED = 'cancelled',
  /** Rate limiting */

  RATE_LIMIT = 'rate_limit',
  /** Resource not found */

  NOT_FOUND = 'not_found',
  /** Unknown error */

  UNKNOWN = 'unknown',
}

/**
 * Error severity levels for UI display
 */
export enum ErrorSeverity {
  /** Low severity - informational */

  INFO = 'info',
  /** Medium severity - warning */

  WARNING = 'warning',
  /** High severity - error */

  ERROR = 'error',
  /** Critical severity - fatal error */

  CRITICAL = 'critical',
}

/**
 * Enhanced API Error class with comprehensive error information for UI applications
 */
export class ApiError extends Error {
  /** Error category for programmatic handling */
  public readonly category: ErrorCategory;
  /** Error severity for UI display */
  public readonly severity: ErrorSeverity;
  /** User-friendly error message */
  public readonly userMessage: string;
  /** Technical error details */
  public readonly technicalDetails: any;
  /** Timestamp when error occurred */
  public readonly timestamp: Date;
  /** Whether this error is retryable */
  public readonly retryable: boolean;
  /** Suggested retry delay in milliseconds */
  public readonly retryDelay?: number;
  /** Request context information */
  public readonly context:
    | {
        method?: string;
        url?: string;
        requestId?: string;
      }
    | undefined;

  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
    details?: any,
    context?: {
      method?: string;
      url?: string;
      requestId?: string;
    }
  ) {
    super(message);
    this.name = 'ApiError';
    this.timestamp = new Date();
    this.context = context;
    this.technicalDetails = details;

    // Categorize error based on status code and details
    const { category, severity, userMessage, retryable, retryDelay } = this.categorizeError(
      status,
      code,
      details
    );
    this.category = category;
    this.severity = severity;
    this.userMessage = userMessage;
    this.retryable = retryable;
    this.retryDelay = retryDelay ?? 0;
  }

  /**
   * Categorizes error based on status code and error details
   */
  private categorizeError(status: number, _code?: string, details?: any) {
    // Check for non-retryable execution errors first
    if (details?.error?.error_type === 'MaxIterationsReachedError') {
      return {
        category: ErrorCategory.VALIDATION,
        severity: ErrorSeverity.WARNING,
        userMessage:
          'Agent reached maximum iteration limit. Consider increasing max_iterations or simplifying the task.',
        retryable: false,
      };
    }

    // Add other non-retryable execution errors
    const nonRetryableExecutionErrors = [
      'MaxIterationsReachedError',
      'ValidationError',
      'ConfigurationError',
    ];

    if (
      status >= 500 &&
      details?.error?.error_type &&
      nonRetryableExecutionErrors.includes(details.error.error_type)
    ) {
      return {
        category: ErrorCategory.VALIDATION,
        severity: ErrorSeverity.WARNING,
        userMessage:
          details?.error?.message || 'Execution failed due to configuration or validation issue.',
        retryable: false,
      };
    }

    // Network/connectivity errors
    if (status === 0 || status === -1) {
      return {
        category: ErrorCategory.NETWORK,
        severity: ErrorSeverity.ERROR,
        userMessage: 'Unable to connect to the server. Please check your internet connection.',
        retryable: true,
        retryDelay: 5000,
      };
    }

    // Authentication errors
    if (status === 401) {
      return {
        category: ErrorCategory.AUTH,
        severity: ErrorSeverity.ERROR,
        userMessage: 'Authentication failed. Please check your API key.',
        retryable: false,
      };
    }

    if (status === 403) {
      return {
        category: ErrorCategory.AUTH,
        severity: ErrorSeverity.ERROR,
        userMessage: "Access denied. You don't have permission to perform this action.",
        retryable: false,
      };
    }

    // Not found errors
    if (status === 404) {
      return {
        category: ErrorCategory.NOT_FOUND,
        severity: ErrorSeverity.WARNING,
        userMessage: 'The requested resource was not found.',
        retryable: false,
      };
    }

    // Validation errors
    if (status === 400 || status === 422) {
      return {
        category: ErrorCategory.VALIDATION,
        severity: ErrorSeverity.WARNING,
        userMessage: details?.detail || 'Invalid request. Please check your input.',
        retryable: false,
      };
    }

    // Rate limiting
    if (status === 429) {
      const retryAfter = details?.retry_after || 60;
      return {
        category: ErrorCategory.RATE_LIMIT,
        severity: ErrorSeverity.WARNING,
        userMessage: `Too many requests. Please wait ${retryAfter} seconds before trying again.`,
        retryable: true,
        retryDelay: retryAfter * 1000,
      };
    }

    // Server errors
    if (status >= 500) {
      return {
        category: ErrorCategory.SERVER,
        severity: ErrorSeverity.ERROR,
        userMessage: 'Server error occurred. Please try again later.',
        retryable: true,
        retryDelay: 3000,
      };
    }

    // Default case
    return {
      category: ErrorCategory.UNKNOWN,
      severity: ErrorSeverity.ERROR,
      userMessage: 'An unexpected error occurred. Please try again.',
      retryable: true,
      retryDelay: 2000,
    };
  }

  /**
   * Returns a JSON representation of the error for logging
   */
  toJSON() {
    return {
      name: this.name,
      message: this.message,
      userMessage: this.userMessage,
      status: this.status,
      code: this.code,
      category: this.category,
      severity: this.severity,
      retryable: this.retryable,
      retryDelay: this.retryDelay,
      timestamp: this.timestamp.toISOString(),
      context: this.context,
      technicalDetails: this.technicalDetails,
    };
  }

  /**
   * Returns a user-friendly error message for display in UI
   */
  getDisplayMessage(): string {
    return this.userMessage;
  }

  /**
   * Returns whether this error should be retried automatically
   */
  shouldRetry(): boolean {
    return this.retryable;
  }

  /**
   * Returns the suggested delay before retrying
   */
  getRetryDelay(): number {
    return this.retryDelay || 1000;
  }
}

/**
 * Timeout Error for request timeouts
 */
export class TimeoutError extends ApiError {
  constructor(timeout: number, context?: { method?: string; url?: string; requestId?: string }) {
    super(`Request timed out after ${timeout}ms`, 0, 'TIMEOUT', { timeout }, context);
    this.name = 'TimeoutError';

    // Override categorization for timeout errors
    const timeoutCategory = {
      category: ErrorCategory.TIMEOUT,
      severity: ErrorSeverity.ERROR,
      userMessage: `Request timed out after ${timeout / 1000} seconds. Please try again.`,
      retryable: true,
      retryDelay: 5000,
    };

    (this as any).category = timeoutCategory.category;
    (this as any).severity = timeoutCategory.severity;
    (this as any).userMessage = timeoutCategory.userMessage;
    (this as any).retryable = timeoutCategory.retryable;
    (this as any).retryDelay = timeoutCategory.retryDelay;
  }
}

/**
 * Cancellation Error for cancelled requests
 */
export class CancellationError extends ApiError {
  constructor(context?: { method?: string; url?: string; requestId?: string }) {
    super('Request was cancelled', 0, 'CANCELLED', {}, context);
    this.name = 'CancellationError';

    // Override categorization for cancellation errors
    const cancelCategory = {
      category: ErrorCategory.CANCELLED,
      severity: ErrorSeverity.ERROR,
      userMessage: 'Request was cancelled.',
      retryable: false,
      retryDelay: undefined,
    };

    (this as any).category = cancelCategory.category;
    (this as any).severity = cancelCategory.severity;
    (this as any).userMessage = cancelCategory.userMessage;
    (this as any).retryable = cancelCategory.retryable;
    (this as any).retryDelay = cancelCategory.retryDelay;
  }
}

/**
 * Union types for better type safety
 */
export type ConfigType = 'agent' | 'llm' | 'mcp_server' | 'linear_workflow' | 'custom_workflow';
export type ExecutionStatus = 'success' | 'error' | 'max_iterations_reached';
export type TransportType = 'stdio' | 'local' | 'http_stream';
export type LLMProvider = 'openai' | 'anthropic' | 'local' | 'azure';

/**
 * Execution error types that should not be retried
 */
export type ExecutionErrorType =
  | 'MaxIterationsReachedError'
  | 'TimeoutError'
  | 'ValidationError'
  | 'ConfigurationError';
