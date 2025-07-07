/**
 * Base HTTP client for making API requests to the Aurite Framework
 *
 * This class handles:
 * - Authentication via API key headers
 * - Request/response formatting
 * - Error handling
 * - Base URL configuration
 */

import type { ApiConfig } from './types';

export class BaseClient {
  protected config: ApiConfig;

  constructor(config: ApiConfig) {
    this.config = config;
  }

  /**
   * Makes an HTTP request to the API
   *
   * @param method - HTTP method (GET, POST, PUT, DELETE, etc.)
   * @param path - API endpoint path (will be appended to base URL)
   * @param body - Optional request body
   * @returns Promise resolving to the parsed JSON response
   * @throws Error if the request fails or returns a non-OK status
   */
  protected async request<T>(
    method: string,
    path: string,
    body?: any
  ): Promise<T> {
    const url = `${this.config.baseUrl}${path}`;
    const headers: HeadersInit = {
      'X-API-Key': this.config.apiKey,
      'Content-Type': 'application/json',
    };

    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `API request failed: ${response.status}`);
    }

    return response.json();
  }
}
