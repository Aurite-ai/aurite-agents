/**
 * Tests for BaseClient
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { BaseClient } from '../../../src/client/BaseClient';
import { ApiError, TimeoutError, CancellationError } from '../../../src/types';
import type { ApiConfig } from '../../../src/types';

// Test class that extends BaseClient to access protected methods
class TestableBaseClient extends BaseClient {
  public async testRequest<T>(method: string, path: string, body?: any, options?: any): Promise<T> {
    return this.request<T>(method, path, body, options);
  }
}

describe('BaseClient', () => {
  let client: TestableBaseClient;
  const mockFetch = vi.fn();
  const config: ApiConfig = {
    baseUrl: process.env.AURITE_API_BASE_URL || 'http://localhost:8000',
    apiKey: process.env.AURITE_API_KEY || 'test-api-key',
  };

  beforeEach(() => {
    client = new TestableBaseClient(config);
    mockFetch.mockClear();
    (globalThis as any).fetch = mockFetch;
  });

  describe('constructor', () => {
    it('should initialize with config', () => {
      expect(client).toBeInstanceOf(BaseClient);
    });
  });

  describe('request', () => {
    it('should make successful GET request', async () => {
      const mockResponse = { data: 'test' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await client.testRequest('GET', '/test');

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/test`,
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('should make successful POST request with body', async () => {
      const requestBody = { message: 'Hello' };
      const mockResponse = { success: true };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await client.testRequest('POST', '/test', requestBody);

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/test`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('should handle API errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not found' }),
      } as Response);

      await expect(client.testRequest('GET', '/test')).rejects.toThrow('Not found');
    });

    it('should handle network errors', async () => {
      // Mock fetch to throw a network error
      const networkError = new TypeError('Failed to fetch');
      mockFetch.mockRejectedValue(networkError);

      try {
        await client.testRequest('GET', '/test');
        expect.fail('Should have thrown an error');
      } catch (error: any) {
        expect(error).toBeInstanceOf(ApiError);
        expect(error.message).toBe('Network error: Unable to connect to server');
      }
    });

    it('should retry on 5xx errors', async () => {
      // First call fails with 500
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Internal server error' }),
      } as Response);

      // Second call succeeds
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      } as Response);

      const result = await client.testRequest('GET', '/test');

      expect(mockFetch).toHaveBeenCalledTimes(2);
      expect(result).toEqual({ success: true });
    });

    it('should not retry on 4xx errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Bad request' }),
      } as Response);

      await expect(client.testRequest('GET', '/test')).rejects.toThrow('Bad request');
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('should handle timeout errors', async () => {
      // Mock fetch to simulate an AbortError (which happens on timeout)
      mockFetch.mockImplementationOnce(() => {
        const error = new Error('The operation was aborted');
        error.name = 'AbortError';
        return Promise.reject(error);
      });

      await expect(
        client.testRequest('GET', '/test', undefined, { timeout: 100 })
      ).rejects.toThrow(TimeoutError);
    });
  });
});
