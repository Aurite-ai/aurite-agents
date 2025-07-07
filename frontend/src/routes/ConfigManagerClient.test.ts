/**
 * Tests for ConfigManagerClient
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ConfigManagerClient } from './ConfigManagerClient';
import type { ApiConfig } from '../types';

describe('ConfigManagerClient', () => {
  let client: ConfigManagerClient;
  const mockFetch = vi.fn();
  const config: ApiConfig = {
    baseUrl: 'http://localhost:8000',
    apiKey: 'test-api-key',
  };

  beforeEach(() => {
    client = new ConfigManagerClient(config);
    mockFetch.mockClear();
    (globalThis as any).fetch = mockFetch;
  });

  describe('listConfigs', () => {
    it('should list configurations by type', async () => {
      const mockAgents = ['Weather Agent', 'Code Assistant', 'Research Agent'];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAgents,
      } as Response);

      const agents = await client.listConfigs('agent');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/agent',
        {
          method: 'GET',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: undefined,
        }
      );

      expect(agents).toEqual(mockAgents);
    });

    it('should handle invalid config type', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Invalid config type' }),
      } as Response);

      await expect(
        client.listConfigs('invalid_type')
      ).rejects.toThrow('Invalid config type');
    });
  });

  describe('getConfig', () => {
    it('should get a specific configuration', async () => {
      const mockAgentConfig = {
        name: 'Weather Agent',
        description: 'An agent that provides weather information',
        system_prompt: 'You are a helpful weather assistant...',
        llm_config_id: 'anthropic_claude',
        mcp_servers: ['weather_server'],
        max_iterations: 5,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAgentConfig,
      } as Response);

      const config = await client.getConfig('agent', 'Weather Agent');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/agent/Weather%20Agent',
        {
          method: 'GET',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: undefined,
        }
      );

      expect(config).toEqual(mockAgentConfig);
    });

    it('should handle config not found', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Configuration not found' }),
      } as Response);

      await expect(
        client.getConfig('agent', 'NonExistent Agent')
      ).rejects.toThrow('Configuration not found');
    });
  });

  describe('createConfig', () => {
    it('should create a new configuration', async () => {
      const newAgent = {
        name: 'Translation Agent',
        description: 'Translates text between languages',
        system_prompt: 'You are a professional translator...',
        llm_config_id: 'anthropic_claude',
        mcp_servers: ['translation_server'],
        max_iterations: 3,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Configuration created successfully' }),
      } as Response);

      const result = await client.createConfig('agent', newAgent);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/agent',
        {
          method: 'POST',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(newAgent),
        }
      );

      expect(result).toEqual({ message: 'Configuration created successfully' });
    });

    it('should handle duplicate name error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({ detail: 'Configuration with this name already exists' }),
      } as Response);

      await expect(
        client.createConfig('agent', { name: 'Existing Agent' })
      ).rejects.toThrow('Configuration with this name already exists');
    });
  });

  describe('updateConfig', () => {
    it('should update an existing configuration', async () => {
      const updatedAgent = {
        name: 'Weather Agent',
        description: 'Updated weather agent',
        system_prompt: 'You are an expert meteorologist...',
        llm_config_id: 'anthropic_claude',
        mcp_servers: ['weather_server', 'news_server'],
        max_iterations: 10,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Configuration updated successfully' }),
      } as Response);

      const result = await client.updateConfig('agent', 'Weather Agent', updatedAgent);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/agent/Weather%20Agent',
        {
          method: 'PUT',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(updatedAgent),
        }
      );

      expect(result).toEqual({ message: 'Configuration updated successfully' });
    });
  });

  describe('deleteConfig', () => {
    it('should delete a configuration', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Configuration deleted successfully' }),
      } as Response);

      const result = await client.deleteConfig('agent', 'Old Agent');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/agent/Old%20Agent',
        {
          method: 'DELETE',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: undefined,
        }
      );

      expect(result).toEqual({ message: 'Configuration deleted successfully' });
    });

    it('should handle delete non-existent config', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Configuration not found' }),
      } as Response);

      await expect(
        client.deleteConfig('agent', 'NonExistent Agent')
      ).rejects.toThrow('Configuration not found');
    });
  });

  describe('reloadConfigs', () => {
    it('should reload all configurations', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Configurations reloaded successfully' }),
      } as Response);

      const result = await client.reloadConfigs();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/reload',
        {
          method: 'POST',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: undefined,
        }
      );

      expect(result).toEqual({ message: 'Configurations reloaded successfully' });
    });
  });
});
