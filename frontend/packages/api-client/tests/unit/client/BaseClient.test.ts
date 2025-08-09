/**
 * Tests for BaseClient
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { BaseClient } from '../../../src/client/BaseClient';
import {
  ApiError,
  TimeoutError,
  CancellationError,
  type ApiConfig,
  RequestOptions,
} from '../../../src/types';

// Create a test class that extends BaseClient to expose the protected request method
class TestableBaseClient extends BaseClient {
  public async testRequest<T>(
    method: string,
    path: string,
    body?: any,
    options?: RequestOptions
  ): Promise<T> {
    return this.request<T>(method, path, body, options);
  }
}

describe('BaseClient', () => {
  let client: TestableBaseClient;
  const mockFetch = vi.fn();
  const config: ApiConfig = {
    baseUrl: 'http://localhost:8000',
    apiKey: 'test-api-key',
  };

  beforeEach(() => {
    client = new TestableBaseClient(config);
    mockFetch.mockClear();
    (globalThis as any).fetch = mockFetch;
    vi.useFakeTimers();
  });

  afterEach(async () => {
    // Clear all pending timers
    vi.clearAllTimers();
    // Run any pending timers to completion
    await vi.runAllTimersAsync();
    // Reset to real timers
    vi.useRealTimers();
    // Clear mock to prevent any lingering promises
    mockFetch.mockClear();
  });

  describe('constructor', () => {
    it('should initialize with provided config', () => {
      const customConfig: ApiConfig = {
        baseUrl: 'https://api.example.com',
        apiKey: 'custom-key',
      };
      const customClient = new TestableBaseClient(customConfig);
      expect(customClient).toBeDefined();
      // Config is protected, so we'll test its effects through requests
    });
  });

  describe('request method', () => {
    describe('successful requests', () => {
      it('should make a GET request with proper headers', async () => {
        const mockResponse = { data: 'test' };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockResponse,
        } as Response);

        const result = await client.testRequest('GET', '/test');

        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/test',
          expect.objectContaining({
            method: 'GET',
            headers: {
              'X-API-Key': 'test-api-key',
              'Content-Type': 'application/json',
            },
          })
        );
        expect(result).toEqual(mockResponse);
      });

      it('should make a POST request with body', async () => {
        const requestBody = { name: 'test', value: 123 };
        const mockResponse = { success: true };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockResponse,
        } as Response);

        const result = await client.testRequest('POST', '/test', requestBody);

        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/test',
          expect.objectContaining({
            method: 'POST',
            headers: {
              'X-API-Key': 'test-api-key',
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
          })
        );
        expect(result).toEqual(mockResponse);
      });

      it('should handle PUT requests', async () => {
        const requestBody = { id: 1, name: 'updated' };
        const mockResponse = { updated: true };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockResponse,
        } as Response);

        const result = await client.testRequest('PUT', '/test/1', requestBody);

        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/test/1',
          expect.objectContaining({
            method: 'PUT',
            body: JSON.stringify(requestBody),
          })
        );
        expect(result).toEqual(mockResponse);
      });

      it('should handle DELETE requests', async () => {
        const mockResponse = { deleted: true };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockResponse,
        } as Response);

        const result = await client.testRequest('DELETE', '/test/1');

        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/test/1',
          expect.objectContaining({
            method: 'DELETE',
          })
        );
        expect(result).toEqual(mockResponse);
      });
    });

    describe('error handling', () => {
      it('should throw ApiError for non-OK responses', async () => {
        const errorResponse = {
          detail: 'Resource not found',
          code: 'NOT_FOUND',
        };
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 404,
          json: async () => errorResponse,
        } as Response);

        // Use try/catch to test the error properties
        try {
          await client.testRequest('GET', '/test');
          // Should not reach here
          expect(true).toBe(false);
        } catch (error) {
          expect(error).toBeInstanceOf(ApiError);
          expect(error).toMatchObject({
            message: 'Resource not found',
            status: 404,
            code: 'NOT_FOUND',
            technicalDetails: errorResponse,
          });
        }
      });

      it('should handle non-JSON error responses', async () => {
        // Mock all retry attempts since 500 is retryable
        const mockResponse = {
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
          json: async () => {
            throw new Error('Invalid JSON');
          },
        } as unknown as Response;

        // Mock for initial attempt + 3 retries = 4 total
        mockFetch.mockResolvedValue(mockResponse);

        const requestPromise = client.testRequest('GET', '/test', undefined, { retries: 0 });

        // Since we set retries to 0, it should fail immediately
        await expect(requestPromise).rejects.toThrow(ApiError);
        await expect(requestPromise).rejects.toMatchObject({
          message: 'Internal Server Error',
          status: 500,
        });

        // Should only be called once with retries: 0
        expect(mockFetch).toHaveBeenCalledTimes(1);
      });
    });

    describe('timeout handling', () => {
      it('should timeout after default 30 seconds', async () => {
        // Create a promise that will be properly handled
        let rejectFn: ((error: Error) => void) | null = null;
        const fetchPromise = new Promise((_, reject) => {
          rejectFn = reject;
        });

        // Mock fetch to return our controlled promise
        mockFetch.mockImplementationOnce((url, options) => {
          // Listen for abort signal
          if (options?.signal) {
            options.signal.addEventListener('abort', () => {
              const error = new Error('The operation was aborted');
              error.name = 'AbortError';
              if (rejectFn) {
                rejectFn(error);
              }
            });
          }
          return fetchPromise;
        });

        const requestPromise = client.testRequest('GET', '/test');

        // Fast-forward time to trigger timeout
        await vi.advanceTimersByTimeAsync(30000);

        // Ensure the promise rejection is handled
        await expect(requestPromise).rejects.toThrow(TimeoutError);
        await expect(requestPromise).rejects.toMatchObject({
          status: 0,
          context: {
            method: 'GET',
            url: 'http://localhost:8000/test',
          },
        });

        // Ensure the fetch promise is also handled to prevent unhandled rejection
        fetchPromise.catch(() => {
          // Silently catch to prevent unhandled rejection
        });
      });

      it('should respect custom timeout option', async () => {
        // Create a promise that will be properly handled
        let rejectFn: ((error: Error) => void) | null = null;
        const fetchPromise = new Promise((_, reject) => {
          rejectFn = reject;
        });

        // Mock fetch to return our controlled promise
        mockFetch.mockImplementationOnce((url, options) => {
          // Listen for abort signal
          if (options?.signal) {
            options.signal.addEventListener('abort', () => {
              const error = new Error('The operation was aborted');
              error.name = 'AbortError';
              if (rejectFn) {
                rejectFn(error);
              }
            });
          }
          return fetchPromise;
        });

        const requestPromise = client.testRequest('GET', '/test', undefined, {
          timeout: 5000,
        });

        await vi.advanceTimersByTimeAsync(5000);

        // Ensure the promise rejection is handled
        await expect(requestPromise).rejects.toThrow(TimeoutError);
        await expect(requestPromise).rejects.toMatchObject({
          status: 0,
        });

        // Ensure the fetch promise is also handled to prevent unhandled rejection
        fetchPromise.catch(() => {
          // Silently catch to prevent unhandled rejection
        });
      });

      it('should clear timeout on successful response', async () => {
        const mockResponse = { data: 'test' };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockResponse,
        } as Response);

        const result = await client.testRequest('GET', '/test');

        expect(result).toEqual(mockResponse);
        // No timeout error should be thrown
      });
    });

    describe('cancellation handling', () => {
      it('should handle external cancellation via AbortSignal', async () => {
        const controller = new AbortController();
        mockFetch.mockImplementationOnce(() => {
          // Simulate abort during fetch
          controller.abort();
          const error = new Error('AbortError');
          error.name = 'AbortError';
          throw error;
        });

        await expect(
          client.testRequest('GET', '/test', undefined, {
            signal: controller.signal,
          })
        ).rejects.toThrow(CancellationError);
      });

      it('should distinguish between timeout and external cancellation', async () => {
        const controller = new AbortController();

        // Mock fetch that checks if signal is aborted
        let abortHandler: (() => void) | null = null;
        mockFetch.mockImplementationOnce(
          (url, options) =>
            new Promise((resolve, reject) => {
              abortHandler = () => {
                const error = new Error('AbortError');
                error.name = 'AbortError';
                reject(error);
              };
              options.signal.addEventListener('abort', abortHandler);
            })
        );

        const requestPromise = client.testRequest('GET', '/test', undefined, {
          signal: controller.signal,
          timeout: 10000,
        });

        // Manually abort before timeout
        controller.abort();

        await expect(requestPromise).rejects.toThrow(CancellationError);
      });
    });

    describe('retry logic', () => {
      it('should retry on 5xx errors', async () => {
        const successResponse = { data: 'success' };

        // First two attempts fail with 500, third succeeds
        mockFetch
          .mockResolvedValueOnce({
            ok: false,
            status: 500,
            json: async () => ({ detail: 'Server error' }),
          } as Response)
          .mockResolvedValueOnce({
            ok: false,
            status: 503,
            json: async () => ({ detail: 'Service unavailable' }),
          } as Response)
          .mockResolvedValueOnce({
            ok: true,
            json: async () => successResponse,
          } as Response);

        const requestPromise = client.testRequest('GET', '/test', undefined, {
          retryDelay: 100,
        });

        // Advance timer for first retry
        await vi.advanceTimersByTimeAsync(100);
        // Advance timer for second retry (exponential backoff: 100 * 2)
        await vi.advanceTimersByTimeAsync(200);

        const result = await requestPromise;
        expect(result).toEqual(successResponse);
        expect(mockFetch).toHaveBeenCalledTimes(3);
      });

      it('should retry on 429 (rate limit) errors', async () => {
        const successResponse = { data: 'success' };

        mockFetch
          .mockResolvedValueOnce({
            ok: false,
            status: 429,
            json: async () => ({ detail: 'Rate limit exceeded' }),
          } as Response)
          .mockResolvedValueOnce({
            ok: true,
            json: async () => successResponse,
          } as Response);

        const requestPromise = client.testRequest('GET', '/test', undefined, {
          retryDelay: 100,
        });

        // Advance timer for retry
        await vi.advanceTimersByTimeAsync(100);

        const result = await requestPromise;
        expect(result).toEqual(successResponse);
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });

      it('should not retry on 4xx errors (except 429)', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 400,
          json: async () => ({ detail: 'Bad request' }),
        } as Response);

        await expect(client.testRequest('GET', '/test')).rejects.toThrow(ApiError);
        expect(mockFetch).toHaveBeenCalledTimes(1);
      });

      it('should retry on network errors', async () => {
        const successResponse = { data: 'success' };

        mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValueOnce({
          ok: true,
          json: async () => successResponse,
        } as Response);

        const requestPromise = client.testRequest('GET', '/test', undefined, {
          retryDelay: 100,
        });

        // Advance timer for retry
        await vi.advanceTimersByTimeAsync(100);

        const result = await requestPromise;
        expect(result).toEqual(successResponse);
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });

      it('should respect custom retry count', async () => {
        // All attempts fail
        mockFetch
          .mockResolvedValueOnce({
            ok: false,
            status: 500,
            json: async () => ({ detail: 'Server error' }),
          } as Response)
          .mockResolvedValueOnce({
            ok: false,
            status: 500,
            json: async () => ({ detail: 'Server error' }),
          } as Response);

        const requestPromise = client.testRequest('GET', '/test', undefined, {
          retries: 1,
          retryDelay: 100,
        });

        // Advance timer for the single retry
        await vi.advanceTimersByTimeAsync(100);

        // Catch the promise to ensure it's handled
        await expect(requestPromise).rejects.toThrow(ApiError);

        // Initial attempt + 1 retry = 2 calls
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });

      it('should use exponential backoff for retries', async () => {
        const successResponse = { data: 'success' };

        mockFetch
          .mockResolvedValueOnce({
            ok: false,
            status: 500,
            json: async () => ({ detail: 'Server error' }),
          } as Response)
          .mockResolvedValueOnce({
            ok: false,
            status: 500,
            json: async () => ({ detail: 'Server error' }),
          } as Response)
          .mockResolvedValueOnce({
            ok: true,
            json: async () => successResponse,
          } as Response);

        const requestPromise = client.testRequest('GET', '/test', undefined, {
          retryDelay: 1000,
        });

        // First retry after 1000ms
        await vi.advanceTimersByTimeAsync(1000);

        // Second retry after 2000ms (exponential backoff)
        await vi.advanceTimersByTimeAsync(2000);

        const result = await requestPromise;
        expect(result).toEqual(successResponse);
        expect(mockFetch).toHaveBeenCalledTimes(3);
      });

      it('should throw last error after exhausting retries', async () => {
        const errorResponse = {
          detail: 'Persistent server error',
          code: 'SERVER_ERROR',
        };

        // All attempts fail
        mockFetch
          .mockResolvedValueOnce({
            ok: false,
            status: 500,
            json: async () => errorResponse,
          } as Response)
          .mockResolvedValueOnce({
            ok: false,
            status: 500,
            json: async () => errorResponse,
          } as Response)
          .mockResolvedValueOnce({
            ok: false,
            status: 500,
            json: async () => errorResponse,
          } as Response);

        const requestPromise = client.testRequest('GET', '/test', undefined, {
          retries: 2,
          retryDelay: 100,
        });

        // Advance timer for first retry
        await vi.advanceTimersByTimeAsync(100);
        // Advance timer for second retry (exponential backoff)
        await vi.advanceTimersByTimeAsync(200);

        // Catch the promise to ensure it's handled
        await expect(requestPromise).rejects.toThrow(ApiError);
        await expect(requestPromise).rejects.toMatchObject({
          message: 'Persistent server error',
          status: 500,
          code: 'SERVER_ERROR',
        });

        // Initial attempt + 2 retries = 3 calls
        expect(mockFetch).toHaveBeenCalledTimes(3);
      });
    });

    describe('edge cases', () => {
      it('should handle unexpected errors', async () => {
        const unexpectedError = new Error('Unexpected error occurred');
        mockFetch.mockRejectedValueOnce(unexpectedError);

        try {
          await client.testRequest('GET', '/test');
          // Should not reach here
          expect(true).toBe(false);
        } catch (error) {
          expect(error).toBeInstanceOf(ApiError);
          expect(error).toMatchObject({
            message: 'Unexpected error: Unexpected error occurred',
            status: 0,
            code: 'UNEXPECTED_ERROR',
          });
        }
      });

      it('should handle errors without message', async () => {
        mockFetch.mockRejectedValueOnce({});

        try {
          await client.testRequest('GET', '/test');
          // Should not reach here
          expect(true).toBe(false);
        } catch (error) {
          expect(error).toBeInstanceOf(ApiError);
          expect(error).toMatchObject({
            message: 'Unexpected error: Unknown error',
            status: 0,
            code: 'UNEXPECTED_ERROR',
          });
        }
      });

      it('should handle empty error responses', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 500,
          statusText: '',
          json: async () => ({}),
        } as Response);

        const requestPromise = client.testRequest('GET', '/test', undefined, { retries: 0 });

        await expect(requestPromise).rejects.toThrow(ApiError);
        await expect(requestPromise).rejects.toMatchObject({
          message: 'API request failed: 500',
          status: 500,
        });
      });

      it('should handle network errors with custom messages', async () => {
        const networkError = new TypeError('Failed to fetch');
        mockFetch.mockRejectedValueOnce(networkError);

        // Network errors are retryable by default, so disable retries
        const requestPromise = client.testRequest('GET', '/test', undefined, { retries: 0 });

        await expect(requestPromise).rejects.toThrow(ApiError);
        await expect(requestPromise).rejects.toMatchObject({
          message: 'Network error: Unable to connect to server',
          status: 0,
          code: 'NETWORK_ERROR',
        });
      });
    });

    describe('request options', () => {
      it('should use default options when none provided', async () => {
        const mockResponse = { data: 'test' };
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockResponse,
        } as Response);

        await client.testRequest('GET', '/test');

        // Verify default timeout behavior by checking that fetch was called
        // with an AbortSignal (created internally for timeout)
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/test',
          expect.objectContaining({
            signal: expect.any(AbortSignal),
          })
        );
      });

      it('should merge custom options with defaults', async () => {
        const mockResponse = { data: 'test' };
        const customSignal = new AbortController().signal;

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: async () => mockResponse,
        } as Response);

        await client.testRequest('GET', '/test', undefined, {
          timeout: 10000,
          retries: 5,
          signal: customSignal,
        });

        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/test',
          expect.objectContaining({
            signal: customSignal,
          })
        );
      });
    });
  });
});
