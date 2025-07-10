/**
 * Tests for MCPHostClient
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MCPHostClient } from '../../../src/routes/MCPHostClient';
import type { ApiConfig, ServerConfig } from '../../../src/types';

describe('MCPHostClient', () => {
  let client: MCPHostClient;
  const mockFetch = vi.fn();
  const config: ApiConfig = {
    baseUrl: process.env.AURITE_API_BASE_URL || 'http://localhost:8000',
    apiKey: process.env.AURITE_API_KEY || 'test-api-key',
  };

  beforeEach(() => {
    client = new MCPHostClient(config);
    mockFetch.mockClear();
    (globalThis as any).fetch = mockFetch;
  });

  describe('getStatus', () => {
    it('should get host status with tool count', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'active', tool_count: 5 }),
      } as Response);

      const result = await client.getStatus();

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/host/status`,
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual({ status: 'active', tool_count: 5 });
    });
  });

  describe('listTools', () => {
    it('should list available tools', async () => {
      const mockTools = [
        {
          name: 'weather_lookup',
          description: 'Look up weather information',
          inputSchema: {
            type: 'object',
            properties: {
              location: { type: 'string' },
            },
          },
        },
        {
          name: 'calculate',
          description: 'Perform calculations',
          inputSchema: {
            type: 'object',
            properties: {
              expression: { type: 'string' },
            },
          },
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTools,
      } as Response);

      const tools = await client.listTools();

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/host/tools`,
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );

      expect(tools).toEqual(mockTools);
    });
  });

  describe('registerServerByName', () => {
    it('should register a server by name', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'registered', name: 'weather_server' }),
      } as Response);

      const result = await client.registerServerByName('weather_server');

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/host/register/weather_server`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual({ status: 'registered', name: 'weather_server' });
    });

    it('should handle server not found error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Server configuration not found' }),
      } as Response);

      await expect(client.registerServerByName('unknown_server')).rejects.toThrow(
        'Server configuration not found'
      );
    });
  });

  describe('registerServerByConfig', () => {
    it('should register a server with custom config', async () => {
      const serverConfig: ServerConfig = {
        name: 'custom_server',
        server_path: '/path/to/server.py',
        transport_type: 'stdio',
        capabilities: ['tools'],
        timeout: 30,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'registered', name: 'custom_server' }),
      } as Response);

      const result = await client.registerServerByConfig(serverConfig);

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/host/register/config`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(serverConfig),
        })
      );

      expect(result).toEqual({ status: 'registered', name: 'custom_server' });
    });
  });

  describe('unregisterServer', () => {
    it('should unregister a server', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'unregistered', name: 'weather_server' }),
      } as Response);

      const result = await client.unregisterServer('weather_server');

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/host/servers/weather_server`,
        expect.objectContaining({
          method: 'DELETE',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual({ status: 'unregistered', name: 'weather_server' });
    });
  });

  describe('callTool', () => {
    it('should call a tool directly', async () => {
      const mockResult = {
        content: [
          {
            type: 'text',
            text: 'Weather for San Francisco: Sunny, 72°F',
          },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResult,
      } as Response);

      const result = await client.callTool('weather_lookup', {
        location: 'San Francisco',
      });

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/host/tools/weather_lookup/call`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            args: { location: 'San Francisco' },
          }),
        })
      );

      expect(result).toEqual(mockResult);
    });

    it('should handle tool not found error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Tool not found' }),
      } as Response);

      await expect(client.callTool('unknown_tool', { arg: 'value' })).rejects.toThrow(
        'Tool not found'
      );
    });
  });
});
