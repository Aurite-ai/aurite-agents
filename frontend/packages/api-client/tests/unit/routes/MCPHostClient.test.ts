/**
 * Tests for MCPHostClient
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MCPHostClient } from '../../../src/routes/MCPHostClient';
import { getApiClientConfig } from '../../../src/config/environment';
import type { ApiConfig, ServerConfig } from '../../../src/types';

describe('MCPHostClient', () => {
  let client: MCPHostClient;
  const mockFetch = vi.fn();
  let config: ApiConfig;

  beforeEach(() => {
    // Get config from environment with test overrides
    config = getApiClientConfig({
      baseUrl: 'http://localhost:8000',
      apiKey: 'test-api-key',
    });

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
        `${config.baseUrl}/tools/status`,
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
        `${config.baseUrl}/tools/`,
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
        `${config.baseUrl}/tools/weather_lookup`,
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
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
        `${config.baseUrl}/tools/weather_lookup/call`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ args: { location: 'SF' } }),
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

      await expect(client.callTool('non_existent_tool', {})).rejects.toThrow('Tool not found');
    });
  });

  describe('listRegisteredServers', () => {
    it('should list registered servers', async () => {
      const mockServers = [
        {
          name: 'weather_server',
          status: 'active',
          transport_type: 'stdio',
          tool_count: 3,
        },
      ];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockServers,
      } as Response);

      const result = await client.listRegisteredServers();
      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/tools/servers`,
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );
      expect(result).toEqual(mockServers);
    });
  });

  describe('getServerStatus', () => {
    it('should get status for a specific server', async () => {
      const mockStatus = {
        name: 'weather_server',
        registered: true,
        status: 'active',
        tools: ['weather_lookup', 'forecast'],
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus,
      } as Response);

      const result = await client.getServerStatus('weather_server');
      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/tools/servers/weather_server`,
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );
      expect(result).toEqual(mockStatus);
    });

    it('should handle server not found error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Server not found' }),
      } as Response);

      await expect(client.getServerStatus('non_existent_server')).rejects.toThrow(
        'Server not found'
      );
    });
  });

  describe('getServerTools', () => {
    it('should get tools for a specific server', async () => {
      const mockTools = [
        {
          name: 'weather_lookup',
          description: 'Look up weather information',
          server_name: 'weather_server',
        },
      ];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTools,
      } as Response);

      const result = await client.getServerTools('weather_server');
      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/tools/servers/weather_server/tools`,
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );
      expect(result).toEqual(mockTools);
    });
  });

  describe('testServer', () => {
    it('should test a server configuration', async () => {
      const mockResult = {
        status: 'success',
        server_name: 'weather_server',
        tools_discovered: 3,
        message: 'Server test successful',
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResult,
      } as Response);

      const result = await client.testServer('weather_server');
      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/tools/servers/weather_server/test`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );
      expect(result).toEqual(mockResult);
    });

    it('should handle test failure', async () => {
      const errorResponse = {
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Server test failed: Connection timeout' }),
      } as Response;

      // Mock all retry attempts
      mockFetch.mockResolvedValue(errorResponse);

      await expect(client.testServer('failing_server')).rejects.toThrow(
        'Server test failed: Connection timeout'
      );
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
        `${config.baseUrl}/tools/register/weather_server`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual({ status: 'success', name: 'weather_server' });
    });

    it('should handle registration failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
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
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'success', name: 'custom_server' }),
      } as Response);

      const result = await client.registerServerByConfig(serverConfig);

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/tools/register/config`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(serverConfig),
        })
      );

      expect(result).toEqual({ status: 'success', name: 'custom_server' });
    });

    it('should handle invalid config error', async () => {
      const invalidConfig: ServerConfig = {
        name: '',
        server_path: '',
        transport_type: 'stdio',
      };

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ detail: 'Invalid server configuration: name cannot be empty' }),
      } as Response);

      await expect(client.registerServerByConfig(invalidConfig)).rejects.toThrow(
        'Invalid server configuration: name cannot be empty'
      );
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
        `${config.baseUrl}/tools/servers/weather_server`,
        expect.objectContaining({
          method: 'DELETE',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual({ status: 'success', name: 'weather_server' });
    });

    it('should handle unregister non-existent server', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Server not registered' }),
      } as Response);

      await expect(client.unregisterServer('non_existent_server')).rejects.toThrow(
        'Server not registered'
      );
    });
  });

  describe('restartServer', () => {
    it('should restart a server', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'success', name: 'weather_server' }),
      } as Response);

      const result = await client.restartServer('weather_server');

      expect(mockFetch).toHaveBeenCalledWith(
        `${config.baseUrl}/tools/servers/weather_server/restart`,
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': config.apiKey,
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual({ status: 'success', name: 'weather_server' });
    });

    it('should handle restart failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Server not found' }),
      } as Response);

      await expect(client.restartServer('non_existent_server')).rejects.toThrow('Server not found');
    });
  });
});
