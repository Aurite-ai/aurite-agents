import { describe, it, expect, vi, afterEach, beforeEach, Mock } from 'vitest';
import * as apiClient from './apiClient';
import useAuthStore from '../store/authStore';

// Mock the auth store
vi.mock('../store/authStore', () => ({
  __esModule: true,
  default: {
    getState: vi.fn(() => ({
      apiKey: 'test-api-key',
      clearAuth: vi.fn(),
    })),
  },
}));

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('apiClient', () => {
  beforeEach(() => {
    // Set a default successful response for fetch
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
      text: async () => 'Success',
    } as Response);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Configuration Management Functions', () => {
    it('listConfigFiles should map "mcp_servers" to "clients" path', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ['client1.json', 'client2.json'],
      } as Response);

      await apiClient.listConfigFiles('mcp_servers');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/configs/clients'),
        expect.any(Object)
      );
    });

    it('getConfigFileContent should map "mcp_servers" to "clients" path', async () => {
      await apiClient.getConfigFileContent('mcp_servers', 'test.json');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/configs/clients/test.json'),
        expect.any(Object)
      );
    });

    it('saveConfigFileContent should map "mcp_servers" to "clients" path', async () => {
      await apiClient.saveConfigFileContent('mcp_servers', 'test.json', { data: 'new' });
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/configs/clients/test.json'),
        expect.objectContaining({ method: 'PUT' })
      );
    });

    it('getSpecificComponentConfig should map "mcp_servers" to "clients" path', async () => {
      await apiClient.getSpecificComponentConfig('mcp_servers', 'server-id-1');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/configs/clients/id/server-id-1'),
        expect.any(Object)
      );
    });

    it('saveNewConfigFile should map "mcp_servers" to "clients" path', async () => {
      await apiClient.saveNewConfigFile('mcp_servers', 'new-server.json', { name: 'new-server' });
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/configs/clients/new-server.json'),
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  describe('Host and Registration Functions', () => {
    it('listActiveHostMcpServers should call the correct endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ['active_server_1'],
      } as Response);

      const result = await apiClient.listActiveHostMcpServers();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/host/clients/active'),
        expect.any(Object)
      );
      expect(result).toEqual(['active_server_1']);
    });

    it('registerMcpServerAPI should call the correct endpoint', async () => {
      const newServerConfig = { name: 'new-mcp-server', transport_type: 'local' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'success', name: 'new-mcp-server' }),
      } as Response);

      const result = await apiClient.registerMcpServerAPI(newServerConfig);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/clients/register'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newServerConfig),
        })
      );
      expect(result).toEqual({ status: 'success', name: 'new-mcp-server' });
    });
  });

  describe('Error Handling', () => {
    it('should throw an ApiError on non-ok response', async () => {
      const errorDetail = { detail: 'Specific error from backend' };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => errorDetail,
        statusText: 'Not Found',
      } as Response);

      await expect(apiClient.listConfigFiles('agents')).rejects.toMatchObject({
        message: 'Specific error from backend',
        status: 404,
      });
    });

    it('should handle 401 Unauthorized by calling clearAuth', async () => {
      // Get a handle to the mock function from the store mock
      const clearAuthMock = vi.fn();
      (useAuthStore.getState as Mock).mockReturnValue({
        apiKey: 'test-api-key',
        clearAuth: clearAuthMock,
      });

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Unauthorized' }),
        statusText: 'Unauthorized',
      } as Response);

      await expect(apiClient.listConfigFiles('agents')).rejects.toThrow(
        'Unauthorized - API Key rejected or missing.'
      );

      expect(clearAuthMock).toHaveBeenCalled();
    });
  });

  describe('Component Execution and Registration', () => {
    it('listRegisteredAgents should call the correct endpoint', async () => {
      await apiClient.listRegisteredAgents();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/components/agents'),
        expect.any(Object)
      );
    });

    it('listRegisteredSimpleWorkflows should call the correct endpoint', async () => {
      await apiClient.listRegisteredSimpleWorkflows();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/components/workflows'),
        expect.any(Object)
      );
    });

    it('listRegisteredCustomWorkflows should call the correct endpoint', async () => {
      await apiClient.listRegisteredCustomWorkflows();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/components/custom_workflows'),
        expect.any(Object)
      );
    });

    it('registerAgentAPI should POST to the correct endpoint', async () => {
      const agentConfig = { name: 'test-agent', mcp_servers: [] };
      await apiClient.registerAgentAPI(agentConfig as any);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/agents/register'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(agentConfig),
        })
      );
    });

    it('executeAgentAPI should POST to the correct endpoint', async () => {
      const agentName = 'test-agent';
      const userMessage = 'Hello';
      await apiClient.executeAgentAPI(agentName, userMessage);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/agents/${agentName}/execute`),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ user_message: userMessage, system_prompt: undefined }),
        })
      );
    });

    it('registerSimpleWorkflowAPI should POST to the correct endpoint', async () => {
      const workflowConfig = { name: 'test-workflow', steps: [] };
      await apiClient.registerSimpleWorkflowAPI(workflowConfig as any);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/workflows/register'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(workflowConfig),
        })
      );
    });

    it('executeSimpleWorkflowAPI should POST to the correct endpoint', async () => {
      const workflowName = 'test-workflow';
      const initialMessage = 'Start';
      await apiClient.executeSimpleWorkflowAPI(workflowName, initialMessage);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/workflows/${workflowName}/execute`),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ initial_user_message: initialMessage }),
        })
      );
    });

    it('registerCustomWorkflowAPI should POST to the correct endpoint', async () => {
      const customWorkflowConfig = { name: 'custom-workflow', module_path: 'path/to/module.py' };
      await apiClient.registerCustomWorkflowAPI(customWorkflowConfig as any);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/custom_workflows/register'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(customWorkflowConfig),
        })
      );
    });

    it('executeCustomWorkflowAPI should POST to the correct endpoint', async () => {
      const workflowName = 'custom-workflow';
      const initialInput = { key: 'value' };
      await apiClient.executeCustomWorkflowAPI(workflowName, initialInput);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/custom_workflows/${workflowName}/execute`),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ initial_input: initialInput }),
        })
      );
    });
  });
});
