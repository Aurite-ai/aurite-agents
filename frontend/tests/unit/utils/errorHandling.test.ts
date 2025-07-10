/**
 * Tests for error handling utilities
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  createErrorNotification,
  getErrorColor,
  getErrorIcon,
  RetryHandler,
  ErrorBoundary,
  logError,
  type ErrorDisplayConfig,
} from '../../../src/utils/errorHandling';
import {
  ApiError,
  TimeoutError,
  CancellationError,
  ErrorCategory,
  ErrorSeverity,
} from '../../../src/types';

describe('Error Handling Utilities', () => {
  describe('createErrorNotification', () => {
    it('should create notification for API error', () => {
      const apiError = new ApiError(
        'Test error',
        400,
        'TEST_ERROR',
        { detail: 'Test error details' },
        { method: 'GET', url: '/test' }
      );

      const notification = createErrorNotification(apiError);

      expect(notification).toMatchObject({
        title: 'Validation Error',
        message: apiError.getDisplayMessage(),
        severity: ErrorSeverity.WARNING,
        category: ErrorCategory.VALIDATION,
        retryable: false,
        autoDismiss: true,
      });
      expect(notification.id).toMatch(/^error_\d+_[a-z0-9]+$/);
      expect(notification.originalError).toBe(apiError);
    });

    it('should create notification for timeout error', () => {
      const timeoutError = new TimeoutError(5000, { method: 'POST', url: '/test' });
      const notification = createErrorNotification(timeoutError);

      expect(notification).toMatchObject({
        title: 'Request Timeout',
        severity: ErrorSeverity.ERROR,
        category: ErrorCategory.TIMEOUT,
        retryable: true,
      });
    });

    it('should create notification for cancellation error', () => {
      const cancelError = new CancellationError({ method: 'GET', url: '/test' });
      const notification = createErrorNotification(cancelError);

      expect(notification).toMatchObject({
        title: 'Request Cancelled',
        severity: ErrorSeverity.ERROR,
        category: ErrorCategory.CANCELLED,
        retryable: false,
      });
    });

    it('should create notification for generic error', () => {
      const genericError = new Error('Generic error');
      const notification = createErrorNotification(genericError);

      expect(notification).toMatchObject({
        title: 'Unexpected Error',
        message: 'An unexpected error occurred. Please try again.',
        severity: ErrorSeverity.ERROR,
        category: ErrorCategory.UNKNOWN,
        retryable: false,
        autoDismiss: false,
      });
    });

    it('should respect custom configuration', () => {
      const config: ErrorDisplayConfig = {
        showTechnicalDetails: true,
        showRetryButton: false,
        customMessages: {
          [ErrorCategory.VALIDATION]: 'Custom validation message',
        },
        autoDismiss: {
          enabled: false,
          categories: [],
          delay: 0,
        },
      };

      const apiError = new ApiError('Test error', 400);
      const notification = createErrorNotification(apiError, config);

      expect(notification.message).toBe('Custom validation message');
      expect(notification.retryable).toBe(false);
      expect(notification.autoDismiss).toBe(false);
      expect(notification.technicalDetails).toBeDefined();
    });
  });

  describe('getErrorColor', () => {
    it('should return correct colors for severities', () => {
      expect(getErrorColor(ErrorSeverity.INFO)).toBe('blue');
      expect(getErrorColor(ErrorSeverity.WARNING)).toBe('yellow');
      expect(getErrorColor(ErrorSeverity.ERROR)).toBe('red');
      expect(getErrorColor(ErrorSeverity.CRITICAL)).toBe('red');
    });
  });

  describe('getErrorIcon', () => {
    it('should return correct icons for categories', () => {
      expect(getErrorIcon(ErrorCategory.NETWORK)).toBe('🌐');
      expect(getErrorIcon(ErrorCategory.AUTH)).toBe('🔒');
      expect(getErrorIcon(ErrorCategory.VALIDATION)).toBe('⚠️');
      expect(getErrorIcon(ErrorCategory.SERVER)).toBe('🔧');
      expect(getErrorIcon(ErrorCategory.TIMEOUT)).toBe('⏱️');
      expect(getErrorIcon(ErrorCategory.CANCELLED)).toBe('❌');
      expect(getErrorIcon(ErrorCategory.RATE_LIMIT)).toBe('🚦');
      expect(getErrorIcon(ErrorCategory.NOT_FOUND)).toBe('🔍');
      expect(getErrorIcon(ErrorCategory.UNKNOWN)).toBe('❗');
    });
  });

  describe('RetryHandler', () => {
    let retryHandler: RetryHandler;

    beforeEach(() => {
      retryHandler = new RetryHandler(2, 100); // 2 retries, 100ms base delay
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should succeed on first attempt', async () => {
      const mockFn = vi.fn().mockResolvedValue('success');

      const result = await retryHandler.execute(mockFn);

      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalledTimes(1);
      expect(retryHandler.getCurrentRetryCount()).toBe(0);
    });

    it('should retry on retryable errors', async () => {
      const retryableError = new ApiError('Server error', 500);
      const mockFn = vi
        .fn()
        .mockRejectedValueOnce(retryableError)
        .mockRejectedValueOnce(retryableError)
        .mockResolvedValue('success');

      const executePromise = retryHandler.execute(mockFn);

      // Fast-forward through delays
      await vi.runAllTimersAsync();

      const result = await executePromise;

      expect(result).toBe('success');
      expect(mockFn).toHaveBeenCalledTimes(3);
    });

    it('should not retry non-retryable errors', async () => {
      const nonRetryableError = new ApiError('Validation error', 400);
      const mockFn = vi.fn().mockRejectedValue(nonRetryableError);

      await expect(retryHandler.execute(mockFn)).rejects.toThrow(nonRetryableError);
      expect(mockFn).toHaveBeenCalledTimes(1);
    });

    it('should respect custom retry logic', async () => {
      const error = new Error('Custom error');
      const mockFn = vi.fn().mockRejectedValue(error);
      const shouldRetry = vi.fn().mockReturnValue(false);

      await expect(retryHandler.execute(mockFn, shouldRetry)).rejects.toThrow(error);
      expect(mockFn).toHaveBeenCalledTimes(1);
      expect(shouldRetry).toHaveBeenCalledWith(error);
    });

    it('should reset retry count after success', async () => {
      const error = new ApiError('Server error', 500);
      const mockFn = vi.fn().mockRejectedValueOnce(error).mockResolvedValue('success');

      const executePromise = retryHandler.execute(mockFn);
      await vi.runAllTimersAsync();
      await executePromise;

      expect(retryHandler.getCurrentRetryCount()).toBe(0);
    });

    it('should reset retry count manually', () => {
      retryHandler.reset();
      expect(retryHandler.getCurrentRetryCount()).toBe(0);
    });
  });

  describe('ErrorBoundary', () => {
    let errorBoundary: ErrorBoundary;
    let mockHandler: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      errorBoundary = new ErrorBoundary();
      mockHandler = vi.fn();
    });

    it('should add and call error handlers', () => {
      errorBoundary.addErrorHandler(mockHandler);

      const error = new Error('Test error');
      errorBoundary.handleError(error);

      expect(mockHandler).toHaveBeenCalledWith(error, undefined);
    });

    it('should remove error handlers', () => {
      errorBoundary.addErrorHandler(mockHandler);
      errorBoundary.removeErrorHandler(mockHandler);

      const error = new Error('Test error');
      errorBoundary.handleError(error);

      expect(mockHandler).not.toHaveBeenCalled();
    });

    it('should wrap synchronous functions', () => {
      errorBoundary.addErrorHandler(mockHandler);

      const error = new Error('Test error');
      const throwingFn = () => {
        throw error;
      };
      const wrappedFn = errorBoundary.wrap(throwingFn);

      expect(() => wrappedFn()).toThrow(error);
      expect(mockHandler).toHaveBeenCalledWith(error, undefined);
    });

    it('should wrap asynchronous functions', async () => {
      errorBoundary.addErrorHandler(mockHandler);

      const error = new Error('Test error');
      const throwingAsyncFn = async () => {
        throw error;
      };
      const wrappedFn = errorBoundary.wrap(throwingAsyncFn);

      await expect(wrappedFn()).rejects.toThrow(error);
      expect(mockHandler).toHaveBeenCalledWith(error, undefined);
    });

    it('should handle errors in error handlers gracefully', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const faultyHandler = vi.fn().mockImplementation(() => {
        throw new Error('Handler error');
      });

      errorBoundary.addErrorHandler(faultyHandler);
      errorBoundary.addErrorHandler(mockHandler);

      const error = new Error('Test error');
      errorBoundary.handleError(error);

      expect(faultyHandler).toHaveBeenCalled();
      expect(mockHandler).toHaveBeenCalled();
      expect(consoleSpy).toHaveBeenCalledWith('Error in error handler:', expect.any(Error));

      consoleSpy.mockRestore();
    });
  });

  describe('logError', () => {
    let consoleSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
      consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {}) as any;
    });

    afterEach(() => {
      consoleSpy.mockRestore();
    });

    it('should log API errors with full details', () => {
      const apiError = new ApiError(
        'Test error',
        400,
        'TEST_ERROR',
        { detail: 'Test details' },
        { method: 'GET', url: '/test' }
      );

      logError(apiError, 'test context');

      expect(consoleSpy).toHaveBeenCalledWith('API Error:', {
        timestamp: expect.any(String),
        context: 'test context',
        error: apiError.toJSON(),
      });
    });

    it('should log generic errors', () => {
      const error = new Error('Generic error');
      error.stack = 'Error stack trace';

      logError(error);

      expect(consoleSpy).toHaveBeenCalledWith('API Error:', {
        timestamp: expect.any(String),
        context: undefined,
        error: {
          name: 'Error',
          message: 'Generic error',
          stack: 'Error stack trace',
        },
      });
    });
  });

  describe('Error categorization', () => {
    it('should categorize network errors correctly', () => {
      const networkError = new ApiError('Network error', 0);
      expect(networkError.category).toBe(ErrorCategory.NETWORK);
      expect(networkError.severity).toBe(ErrorSeverity.ERROR);
      expect(networkError.retryable).toBe(true);
    });

    it('should categorize auth errors correctly', () => {
      const authError401 = new ApiError('Unauthorized', 401);
      expect(authError401.category).toBe(ErrorCategory.AUTH);
      expect(authError401.retryable).toBe(false);

      const authError403 = new ApiError('Forbidden', 403);
      expect(authError403.category).toBe(ErrorCategory.AUTH);
      expect(authError403.retryable).toBe(false);
    });

    it('should categorize validation errors correctly', () => {
      const validationError400 = new ApiError('Bad request', 400);
      expect(validationError400.category).toBe(ErrorCategory.VALIDATION);
      expect(validationError400.severity).toBe(ErrorSeverity.WARNING);
      expect(validationError400.retryable).toBe(false);

      const validationError422 = new ApiError('Unprocessable entity', 422);
      expect(validationError422.category).toBe(ErrorCategory.VALIDATION);
    });

    it('should categorize rate limit errors correctly', () => {
      const rateLimitError = new ApiError('Too many requests', 429, undefined, { retry_after: 30 });
      expect(rateLimitError.category).toBe(ErrorCategory.RATE_LIMIT);
      expect(rateLimitError.retryable).toBe(true);
      expect(rateLimitError.retryDelay).toBe(30000);
    });

    it('should categorize server errors correctly', () => {
      const serverError = new ApiError('Internal server error', 500);
      expect(serverError.category).toBe(ErrorCategory.SERVER);
      expect(serverError.severity).toBe(ErrorSeverity.ERROR);
      expect(serverError.retryable).toBe(true);
    });

    it('should categorize not found errors correctly', () => {
      const notFoundError = new ApiError('Not found', 404);
      expect(notFoundError.category).toBe(ErrorCategory.NOT_FOUND);
      expect(notFoundError.severity).toBe(ErrorSeverity.WARNING);
      expect(notFoundError.retryable).toBe(false);
    });
  });
});
