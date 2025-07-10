/**
 * Tests for ConfigManagerClient
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ConfigManagerClient } from '../../../src/routes/ConfigManagerClient';
import type { ApiConfig } from '../../../src/types';

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
        'http://localhost:8000/config/components/agent',
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
        })
      );

      expect(agents).toEqual(mockAgents);
    });

    it('should handle invalid config type', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Invalid config type' }),
      } as Response);

      await expect(client.listConfigs('invalid_type')).rejects.toThrow('Invalid config type');
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
        'http://localhost:8000/config/components/agent/Weather%20Agent',
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
        })
      );

      expect(config).toEqual(mockAgentConfig);
    });

    it('should handle config not found', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Configuration not found' }),
      } as Response);

      await expect(client.getConfig('agent', 'NonExistent Agent')).rejects.toThrow(
        'Configuration not found'
      );
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
        'http://localhost:8000/config/components/agent',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: 'Translation Agent',
            config: {
              description: 'Translates text between languages',
              system_prompt: 'You are a professional translator...',
              llm_config_id: 'anthropic_claude',
              mcp_servers: ['translation_server'],
              max_iterations: 3,
            },
          }),
        })
      );

      expect(result).toEqual({ message: 'Configuration created successfully' });
    });

    it('should handle duplicate name error', async () => {
      // Need to mock the fetch call that happens during retry attempts
      const errorResponse = {
        ok: false,
        status: 409,
        json: async () => ({ detail: 'Configuration with this name already exists' }),
      } as Response;

      // Mock all retry attempts
      mockFetch.mockResolvedValue(errorResponse);

      await expect(client.createConfig('agent', { name: 'Existing Agent' })).rejects.toThrow(
        'Configuration with this name already exists'
      );
    });

    it('should create a new component with options', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Component created successfully' }),
      } as Response);

      const result = await client.createConfig(
        'agent',
        { name: 'My New Agent', description: 'A test agent' },
        { project: 'project_bravo', filePath: 'new_agents.json' }
      );

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/components/agent',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: 'My New Agent',
            config: {
              description: 'A test agent',
              project: 'project_bravo',
              workspace: undefined,
              file_path: 'new_agents.json',
            },
          }),
        })
      );

      expect(result).toEqual({ message: 'Component created successfully' });
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
        'http://localhost:8000/config/components/agent/Weather%20Agent',
        expect.objectContaining({
          method: 'PUT',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            config: {
              description: 'Updated weather agent',
              system_prompt: 'You are an expert meteorologist...',
              llm_config_id: 'anthropic_claude',
              mcp_servers: ['weather_server', 'news_server'],
              max_iterations: 10,
            },
          }),
        })
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
        'http://localhost:8000/config/components/agent/Old%20Agent',
        expect.objectContaining({
          method: 'DELETE',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual({ message: 'Configuration deleted successfully' });
    });

    it('should handle delete non-existent config', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Configuration not found' }),
      } as Response);

      await expect(client.deleteConfig('agent', 'NonExistent Agent')).rejects.toThrow(
        'Configuration not found'
      );
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
        'http://localhost:8000/config/refresh',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual({ message: 'Configurations reloaded successfully' });
    });
  });

  describe('validateConfig', () => {
    it('should validate a configuration', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: "Component 'Weather Agent' is valid." }),
      } as Response);

      const result = await client.validateConfig('agent', 'Weather Agent');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/components/agent/Weather%20Agent/validate',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual({ message: "Component 'Weather Agent' is valid." });
    });

    it('should handle validation errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ detail: 'Validation failed: Missing required field: system_prompt' }),
      } as Response);

      await expect(client.validateConfig('agent', 'Invalid Agent')).rejects.toThrow(
        'Validation failed: Missing required field: system_prompt'
      );
    });
  });

  describe('listConfigSources', () => {
    it('should list all configuration sources', async () => {
      const mockSources = [
        {
          path: '/home/wilcoxr/workspace/aurite/framework/project_bravo',
          context: 'project',
          project_name: 'project_bravo',
        },
        {
          path: '/home/wilcoxr/workspace/aurite/framework',
          context: 'workspace',
          workspace_name: 'aurite_framework',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSources,
      } as Response);

      const sources = await client.listConfigSources();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/sources',
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
        })
      );

      expect(sources).toEqual(mockSources);
    });
  });

  describe('listConfigFiles', () => {
    it('should list configuration files for a specific source', async () => {
      const mockFiles = [
        'config/agents/example_agents.json',
        'config/custom_workflows/example_custom_workflows.json',
        'config/example_multi_component.json',
        'config/linear_workflows/example_linear_workflow.json',
        'config/llms/example_llms.json',
        'config/mcp_servers/example_mcp_servers.json',
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockFiles,
      } as Response);

      const files = await client.listConfigFiles('project_bravo');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/files/project_bravo',
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
        })
      );

      expect(files).toEqual(mockFiles);
    });

    it('should handle source not found', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Source not found' }),
      } as Response);

      await expect(client.listConfigFiles('non_existent_source')).rejects.toThrow(
        'Source not found'
      );
    });
  });

  describe('getFileContent', () => {
    it('should get the content of a specific file', async () => {
      const mockContent = '{"key": "value"}';
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockContent,
      } as Response);

      const content = await client.getFileContent('workspace', 'agents.json');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/files/workspace/agents.json',
        expect.objectContaining({
          method: 'GET',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
        })
      );

      expect(content).toEqual(mockContent);
    });

    it('should handle file not found', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'File not found' }),
      } as Response);

      await expect(client.getFileContent('workspace', 'non_existent_file.json')).rejects.toThrow(
        'File not found'
      );
    });
  });

  describe('createConfigFile', () => {
    it('should create a new config file', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'File created successfully' }),
      } as Response);

      const result = await client.createConfigFile(
        'project_bravo',
        'new_llms.json',
        '[{"name": "new_llm", "type": "llm"}]'
      );

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/files',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            source_name: 'project_bravo',
            relative_path: 'new_llms.json',
            content: '[{"name": "new_llm", "type": "llm"}]',
          }),
        })
      );

      expect(result).toEqual({ message: 'File created successfully' });
    });

    it('should handle file creation failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Failed to create file' }),
      } as Response);

      await expect(client.createConfigFile('workspace', 'existing.json', '{}')).rejects.toThrow(
        'Failed to create file'
      );
    });
  });

  describe('updateConfigFile', () => {
    it('should update a config file', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'File updated successfully' }),
      } as Response);

      const result = await client.updateConfigFile(
        'project_bravo',
        'llms.json',
        '[{"name": "updated_llm", "type": "llm"}]'
      );

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/files/project_bravo/llms.json',
        expect.objectContaining({
          method: 'PUT',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            content: '[{"name": "updated_llm", "type": "llm"}]',
          }),
        })
      );

      expect(result).toEqual({ message: 'File updated successfully' });
    });
  });

  describe('deleteConfigFile', () => {
    it('should delete a config file', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'File deleted successfully' }),
      } as Response);

      const result = await client.deleteConfigFile('project_bravo', 'old_agents.json');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/files/project_bravo/old_agents.json',
        expect.objectContaining({
          method: 'DELETE',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual({ message: 'File deleted successfully' });
    });
  });

  describe('validateAllConfigs', () => {
    it('should validate all configurations successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      } as Response);

      const result = await client.validateAllConfigs();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/config/validate',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'X-API-Key': 'test-api-key',
            'Content-Type': 'application/json',
          },
        })
      );

      expect(result).toEqual([]);
    });

    it('should return validation errors', async () => {
      const mockErrors = [
        {
          component_type: 'agent',
          component_name: 'Invalid Agent',
          error: 'Missing required field: system_prompt',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockErrors,
      } as Response);

      const result = await client.validateAllConfigs();
      expect(result).toEqual(mockErrors);
    });
  });
});
