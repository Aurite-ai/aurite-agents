import apiClient from './apiClient';
import { 
  MCPServerConfig,
  SuccessResponse
} from '../types';
import {
  ApiError,
  TimeoutError,
  CancellationError,
  ToolDetails,
} from '@aurite-ai/api-client';
import { 
  validateMCPServerConfig,
  formToMCPServerConfig,
  mcpServerConfigToForm,
  getDefaultMCPServerForm,
  validateMCPServerForm
} from '../utils/mcpValidation';

class MCPServersService {
  // List all MCP server configurations
  async listMCPServers(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('mcp_server');
    } catch (error) {
      this.handleError(error, 'Failed to list MCP servers');
      throw error;
    }
  }

  // Get MCP server configuration by ID
  async getMCPServer(id: string): Promise<MCPServerConfig> {
    try {
      const config = await apiClient.config.getConfig('mcp_server', id);
      return this.mapToMCPServerConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get MCP server configuration for ${id}`);
      throw error;
    }
  }

  // Create new MCP server configuration
  async createMCPServer(name: string, config: MCPServerConfig): Promise<{message: string}> {
    try {
      return await apiClient.config.createConfig('mcp_server', { name, config });
    } catch (error) {
      this.handleError(error, `Failed to create MCP server ${name}`);
      throw error;
    }
  }

  // Update MCP server configuration
  async updateMCPServer(id: string, config: MCPServerConfig): Promise<{message: string}> {
    try {
      return await apiClient.config.updateConfig('mcp_server', id, { config });
    } catch (error) {
      this.handleError(error, `Failed to update MCP server ${id}`);
      throw error;
    }
  }

  // Delete MCP server configuration
  async deleteMCPServer(id: string): Promise<{message: string}> {
    try {
      return await apiClient.config.deleteConfig('mcp_server', id);
    } catch (error) {
      this.handleError(error, `Failed to delete MCP server ${id}`);
      throw error;
    }
  }

  // Validate MCP server configuration
  async validateMCPServer(id: string): Promise<any> {
    try {
      return await apiClient.config.validateConfig('mcp_server', id);
    } catch (error) {
      this.handleError(error, `Failed to validate MCP server ${id}`);
      throw error;
    }
  }

  // Create with validation
  async createMCPServerWithValidation(name: string, config: MCPServerConfig): Promise<{message: string}> {
    const errors = validateMCPServerConfig(config);
    if (errors.length > 0) {
      throw new Error(`Validation failed: ${errors.join(', ')}`);
    }
    return await this.createMCPServer(name, config);
  }

  // Update with validation
  async updateMCPServerWithValidation(id: string, config: MCPServerConfig): Promise<{message: string}> {
    const errors = validateMCPServerConfig(config);
    if (errors.length > 0) {
      throw new Error(`Validation failed: ${errors.join(', ')}`);
    }
    return await this.updateMCPServer(id, config);
  }

  // Register MCP server by name
  async registerMCPServer(serverName: string): Promise<SuccessResponse> {
    try {
      await apiClient.host.registerServerByName(serverName);
      return {
        status: 'success',
        message: `MCP server ${serverName} registered successfully`
      };
    } catch (error) {
      this.handleError(error, `Failed to register MCP server ${serverName}`);
      throw error;
    }
  }

  // Unregister MCP server
  async unregisterMCPServer(serverName: string): Promise<SuccessResponse> {
    try {
      await apiClient.host.unregisterServer(serverName);
      return {
        status: 'success',
        message: `MCP server ${serverName} unregistered successfully`
      };
    } catch (error) {
      this.handleError(error, `Failed to unregister MCP server ${serverName}`);
      throw error;
    }
  }

  // Test MCP server connection
  async testMCPServer(serverName: string): Promise<any> {
    try {
      return await apiClient.host.testServer(serverName);
    } catch (error) {
      this.handleError(error, `Failed to test MCP server ${serverName}`);
      throw error;
    }
  }

  // List active MCP servers in the host
  async listActiveMCPServers(): Promise<string[]> {
    try {
      const servers = await apiClient.host.listRegisteredServers();
      return servers.map(server => server.name);
    } catch (error) {
      this.handleError(error, 'Failed to list active MCP servers');
      throw error;
    }
  }

  // List available tools from all registered servers
  async listTools(): Promise<ToolDetails[]> {
    try {
      return await apiClient.host.listTools();
    } catch (error) {
      this.handleError(error, 'Failed to list tools');
      throw error;
    }
  }

  // Call a tool directly
  async callTool(toolName: string, args: Record<string, any>): Promise<any> {
    try {
      return await apiClient.host.callTool(toolName, args);
    } catch (error) {
      this.handleError(error, `Failed to call tool ${toolName}`);
      throw error;
    }
  }

  // Get MCP server status (combines registered and active status)
  async getMCPServerStatus(serverName: string): Promise<{
    registered: boolean;
    active: boolean;
    config?: MCPServerConfig;
  }> {
    try {
      const [registeredServers, activeServers] = await Promise.all([
        this.listMCPServers(),
        this.listActiveMCPServers()
      ]);

      const registered = registeredServers.includes(serverName);
      const active = activeServers.includes(serverName);

      let config: MCPServerConfig | undefined;
      if (registered) {
        try {
          config = await this.getMCPServer(serverName);
        } catch (error) {
          // Config might not exist even if registered
        }
      }

      return {
        registered,
        active,
        config
      };
    } catch (error) {
      this.handleError(error, `Failed to get MCP server status for ${serverName}`);
      return {
        registered: false,
        active: false
      };
    }
  }

  // Check if an MCP server is active
  async isMCPServerActive(serverName: string): Promise<boolean> {
    try {
      const activeServers = await this.listActiveMCPServers();
      return activeServers.includes(serverName);
    } catch (error) {
      this.handleError(error, `Failed to check if MCP server ${serverName} is active`);
      return false;
    }
  }

  // Create and register MCP server in one operation
  async createAndRegisterMCPServer(config: MCPServerConfig): Promise<{
    creation: {message: string};
    registration: SuccessResponse;
  }> {
    try {
      // First create the config
      const creation = await this.createMCPServerWithValidation(config.name, config);
      
      // Then register the server
      const registration = await this.registerMCPServer(config.name);
      
      return {
        creation,
        registration
      };
    } catch (error) {
      this.handleError(error, `Failed to create and register MCP server ${config.name}`);
      throw error;
    }
  }

  // Helper method to handle errors with user-friendly messages
  private handleError(error: unknown, context: string): void {
    if (error instanceof ApiError) {
      console.error(`${context}: ${error.getDisplayMessage()}`, error.toJSON());
    } else if (error instanceof TimeoutError) {
      console.error(`${context}: Request timed out`, error);
    } else if (error instanceof CancellationError) {
      console.error(`${context}: Request was cancelled`, error);
    } else {
      console.error(`${context}: Unknown error`, error);
    }
  }

  // Map API response to MCPServerConfig
  private mapToMCPServerConfig(apiConfig: any): MCPServerConfig {
    return {
      name: apiConfig.name,
      type: "mcp_server",
      capabilities: apiConfig.capabilities || [],
      description: apiConfig.description,
      transport_type: apiConfig.transport_type,
      server_path: apiConfig.server_path,
      http_endpoint: apiConfig.http_endpoint,
      headers: apiConfig.headers,
      command: apiConfig.command,
      args: apiConfig.args,
      timeout: apiConfig.timeout,
      registration_timeout: apiConfig.registration_timeout,
      routing_weight: apiConfig.routing_weight,
      exclude: apiConfig.exclude,
      roots: apiConfig.roots,
    };
  }

  // Utility methods for form handling
  getDefaultForm = getDefaultMCPServerForm;
  validateForm = validateMCPServerForm;
  formToConfig = formToMCPServerConfig;
  configToForm = mcpServerConfigToForm;
}

const mcpServersService = new MCPServersService();
export default mcpServersService;
