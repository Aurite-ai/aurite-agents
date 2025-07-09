/**
 * Tests for MCPHostClient
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MCPHostClient } from './MCPHostClient';
import type { ApiConfig, ServerConfig } from '../types';

describe('MCPHostClient', () => {
  let client: MCPHostClient;
  const mockFetch = vi.fn();
  const config: ApiConfig = {
    baseUrl: 'http://localhost:8000',
    apiKey: 'test-api-key',
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
        'http://localhost:8000/tools/status',
        {
          method: 'GET',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: undefined,
        }
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
          server_name: 'weather_server',
          inputSchema: {
            type: 'object',
            properties: {
              location: { type: 'string' },
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
        'http://localhost:8000/tools/',
        {
          method: 'GET',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: undefined,
        }
      );

      expect(tools).toEqual(mockTools);
    });
  });

  describe('getToolDetails', () => {
    it('should get details for a specific tool', async () => {
      const mockToolDetails = {
        name: 'weather_lookup',
        description: 'Look up weather information',
        server_name: 'weather_server',
        inputSchema: { type: 'object' },
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockToolDetails,
      } as Response);

      const result = await client.getToolDetails('weather_lookup');
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/tools/weather_lookup',
        expect.any(Object)
      );
      expect(result).toEqual(mockToolDetails);
    });
  });

  describe('callTool', () => {
    it('should call a tool directly', async () => {
      const mockResult = {
        content: [{ type: 'text', text: 'Sunny' }],
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResult,
      } as Response);

      const result = await client.callTool('weather_lookup', { location: 'SF' });
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/tools/weather_lookup/call',
        {
          method: 'POST',
          headers: expect.any(Object),
          body: JSON.stringify({ args: { location: 'SF' } }),
        }
      );
      expect(result).toEqual(mockResult);
    });
  });

  describe('listRegisteredServers', () => {
    it('should list registered servers', async () => {
      const mockServers = [{ name: 'server1', status: 'active' }];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockServers,
      } as Response);

      const result = await client.listRegisteredServers();
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/tools/servers',
        expect.any(Object)
      );
      expect(result).toEqual(mockServers);
    });
  });

  describe('getServerStatus', () => {
    it('should get status for a specific server', async () => {
      const mockStatus = { name: 'server1', registered: true };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus,
      } as Response);

      const result = await client.getServerStatus('server1');
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/tools/servers/server1',
        expect.any(Object)
      );
      expect(result).toEqual(mockStatus);
    });
  });

  describe('getServerTools', () => {
    it('should get tools for a specific server', async () => {
      const mockTools = [{ name: 'tool1' }];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTools,
      } as Response);

      const result = await client.getServerTools('server1');
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/tools/servers/server1/tools',
        expect.any(Object)
      );
      expect(result).toEqual(mockTools);
    });
  });

  describe('testServer', () => {
    it('should test a server configuration', async () => {
      const mockResult = { status: 'success', server_name: 'server1' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResult,
      } as Response);

      const result = await client.testServer('server1');
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/tools/servers/server1/test',
        {
          method: 'POST',
          headers: expect.any(Object),
          body: undefined,
        }
      );
      expect(result).toEqual(mockResult);
    });
  });

  describe('registerServerByName', () => {
    it('should register a server by name', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'success', name: 'weather_server' }),
      } as Response);

      const result = await client.registerServerByName('weather_server');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/tools/register/weather_server',
        {
          method: 'POST',
          headers: expect.any(Object),
          body: undefined,
        }
      );

      expect(result).toEqual({ status: 'success', name: 'weather_server' });
    });
  });

  describe('registerServerByConfig', () => {
    it('should register a server with custom config', async () => {
      const serverConfig: ServerConfig = {
        name: 'custom_server',
        server_path: '/path/to/server.py',
        transport_type: 'stdio',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'success', name: 'custom_server' }),
      } as Response);

      const result = await client.registerServerByConfig(serverConfig);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/tools/register/config',
        {
          method: 'POST',
          headers: expect.any(Object),
          body: JSON.stringify(serverConfig),
        }
      );

      expect(result).toEqual({ status: 'success', name: 'custom_server' });
    });
  });

  describe('unregisterServer', () => {
    it('should unregister a server', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'success', name: 'weather_server' }),
      } as Response);

      const result = await client.unregisterServer('weather_server');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/tools/servers/weather_server',
        {
          method: 'DELETE',
          headers: expect.any(Object),
          body: undefined,
        }
      );

      expect(result).toEqual({ status: 'success', name: 'weather_server' });
    });
  });
});
