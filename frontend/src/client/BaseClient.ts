/**
 * Base HTTP client for making API requests to the Aurite Framework
 *
 * This class handles:
 * - Authentication via API key headers
 * - Request/response formatting
 * - Enhanced error handling with custom ApiError
 * - Request timeout and retry logic
 * - Base URL configuration
 */

import type { ApiConfig, RequestOptions } from '../types';
import { ApiError, TimeoutError, CancellationError } from '../types';

export class BaseClient {
  protected config: ApiConfig;

  constructor(config: ApiConfig) {
    this.config = config;
  }

  /**
   * Makes an HTTP request to the API with enhanced error handling and retry logic
   *
   * @param method - HTTP method (GET, POST, PUT, DELETE, etc.)
   * @param path - API endpoint path (will be appended to base URL)
   * @param body - Optional request body
   * @param options - Optional request configuration
   * @returns Promise resolving to the parsed JSON response
   * @throws ApiError, TimeoutError, or CancellationError based on failure type
   */
  protected async request<T>(
    method: string,
    path: string,
    body?: any,
    options: RequestOptions = {}
  ): Promise<T> {
    const { timeout = 30000, retries = 3, retryDelay = 1000 } = options;
    const url = `${this.config.baseUrl}${path}`;
    const requestContext = { method, url };

    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= retries; attempt++) {
      let controller: AbortController | undefined;
      let timeoutId: NodeJS.Timeout | undefined;

      try {
        // Create abort controller for this attempt
        controller = new AbortController();

        // Set up timeout
        timeoutId = setTimeout(() => {
          controller?.abort();
        }, timeout);

        // Prepare request
        const headers: HeadersInit = {
          'X-API-Key': this.config.apiKey,
          'Content-Type': 'application/json',
        };

        const fetchOptions: RequestInit = {
          method,
          headers,
          signal: options.signal || controller.signal,
        };

        if (body) {
          fetchOptions.body = JSON.stringify(body);
        }

        // Make the request
        const response = await fetch(url, fetchOptions);

        // Clear timeout on successful response
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = undefined;
        }

        // Handle non-OK responses
        if (!response.ok) {
          // Parse error response
          let errorData;
          try {
            errorData = await response.json();
          } catch {
            errorData = { detail: response.statusText };
          }

          // Create enhanced error with context
          const apiError = new ApiError(
            errorData.detail || `API request failed: ${response.status}`,
            response.status,
            errorData.code,
            errorData,
            requestContext
          );

          // Check if this is a retryable error
          const isRetryable = response.status >= 500 || response.status === 429;

          if (isRetryable && attempt < retries) {
            lastError = apiError;
            // Calculate exponential backoff delay
            const delay = retryDelay * Math.pow(2, attempt);
            await new Promise(resolve => setTimeout(resolve, delay));
            continue;
          }

          throw apiError;
        }

        // Parse and return successful response
        try {
          return await response.json();
        } catch (parseError) {
          throw new ApiError(
            'Failed to parse response JSON',
            response.status,
            'PARSE_ERROR',
            { parseError: parseError instanceof Error ? parseError.message : parseError },
            requestContext
          );
        }
      } catch (error: any) {
        // Clean up timeout
        if (timeoutId) {
          clearTimeout(timeoutId);
        }

        // Handle different error types
        if (error instanceof ApiError) {
          // If this is the last attempt or error is not retryable, throw it
          if (attempt === retries || !error.shouldRetry()) {
            throw error;
          }

          lastError = error;
          // Wait before retrying
          await new Promise(resolve => setTimeout(resolve, error.getRetryDelay()));
          continue;
        }

        // Handle abort errors (timeout or cancellation)
        if (error.name === 'AbortError') {
          // Check if this was a timeout or external cancellation
          if (options.signal?.aborted) {
            throw new CancellationError(requestContext);
          } else {
            throw new TimeoutError(timeout, requestContext);
          }
        }

        // Handle network errors
        if (error instanceof TypeError && (error.message.includes('fetch') || error.message.includes('Failed to fetch'))) {
          const networkError = new ApiError(
            'Network error: Unable to connect to server',
            0,
            'NETWORK_ERROR',
            { originalError: error.message },
            requestContext
          );

          // Retry network errors if not the last attempt
          if (attempt < retries) {
            lastError = networkError;
            const delay = retryDelay * Math.pow(2, attempt);
            await new Promise(resolve => setTimeout(resolve, delay));
            continue;
          }

          throw networkError;
        }

        // Handle other unexpected errors
        const unexpectedError = new ApiError(
          `Unexpected error: ${error.message || 'Unknown error'}`,
          0,
          'UNEXPECTED_ERROR',
          { originalError: error.message || error },
          requestContext
        );

        // Don't retry unexpected errors
        throw unexpectedError;
      }
    }

    // If we've exhausted all retries, throw the last error
    throw lastError || new ApiError('Maximum retries exceeded', 0, 'MAX_RETRIES', {}, requestContext);
  }
}
