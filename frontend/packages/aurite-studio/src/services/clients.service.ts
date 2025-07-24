import apiClient from './apiClient';
import { 
  ClientConfig as LocalClientConfig,
  MCPServerConfig,
  SuccessResponse
} from '../types';
import {
  ApiError,
  TimeoutError,
  CancellationError,
  ServerConfig,
  ToolDetails,
} from '@aurite/api-client';
import { 
  validateMCPServerConfig, 
  migrateClientConfig 
} from '../utils/mcpValidation';

class ClientsService {
  // List all registered MCP clients/servers
  async listClients(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('mcp_server');
    } catch (error) {
      this.handleError(error, 'Failed to list clients');
      throw error;
    }
  }

  // List active MCP servers in the host
  async listActiveClients(): Promise<string[]> {
    try {
      const servers = await apiClient.host.listRegisteredServers();
      
      if (!servers) {
        console.warn('listRegisteredServers() returned undefined/null');
        return [];
      }
      
      if (!Array.isArray(servers)) {
        console.warn('listRegisteredServers() returned non-array:', typeof servers, servers);
        return [];
      }
      
      return servers.map(server => server.name);
    } catch (error) {
      this.handleError(error, 'Failed to list active clients');
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

  // List client configuration files
  async listClientConfigs(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('mcp_server');
    } catch (error) {
      this.handleError(error, 'Failed to list client configurations');
      throw error;
    }
  }

  // Get client configuration by ID
  async getClientById(id: string): Promise<LocalClientConfig> {
    try {
      const config = await apiClient.config.getConfig('mcp_server', id);
      return this.mapToLocalClientConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get client configuration for ${id}`);
      throw error;
    }
  }

  // Get client configuration by filename
  async getClientConfig(filename: string): Promise<LocalClientConfig> {
    try {
      const config = await apiClient.config.getConfig('mcp_server', filename);
      return this.mapToLocalClientConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get client configuration ${filename}`);
      throw error;
    }
  }

  // Create new client configuration
  async createClientConfig(filename: string, config: LocalClientConfig): Promise<LocalClientConfig> {
    try {
      const apiConfig = this.mapToApiClientConfig(config);
      const result = await apiClient.config.createConfig('mcp_server', apiConfig);
      return this.mapToLocalClientConfig(result);
    } catch (error) {
      this.handleError(error, `Failed to create client configuration ${filename}`);
      throw error;
    }
  }

  // Update client configuration
  async updateClientConfig(filename: string, config: LocalClientConfig): Promise<LocalClientConfig> {
    try {
      const apiConfig = this.mapToApiClientConfig(config);
      const result = await apiClient.config.updateConfig('mcp_server', filename, apiConfig);
      return this.mapToLocalClientConfig(result);
    } catch (error) {
      this.handleError(error, `Failed to update client configuration ${filename}`);
      throw error;
    }
  }

  // Delete client configuration
  async deleteClientConfig(filename: string): Promise<void> {
    try {
      await apiClient.config.deleteConfig('mcp_server', filename);
    } catch (error) {
      this.handleError(error, `Failed to delete client configuration ${filename}`);
      throw error;
    }
  }

  // Register an MCP client/server
  async registerClient(config: LocalClientConfig): Promise<SuccessResponse> {
    try {
      await apiClient.host.registerServerByName(config.name);
      return {
        status: 'success',
        message: `Client ${config.name} registered successfully`
      };
    } catch (error) {
      this.handleError(error, `Failed to register client ${config.name}`);
      throw error;
    }
  }

  // Unregister an MCP server
  async unregisterClient(clientName: string): Promise<SuccessResponse> {
    try {
      await apiClient.host.unregisterServer(clientName);
      return {
        status: 'success',
        message: `Client ${clientName} unregistered successfully`
      };
    } catch (error) {
      this.handleError(error, `Failed to unregister client ${clientName}`);
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

  // Helper to generate a unique filename for client config
  generateConfigFilename(clientName: string): string {
    const sanitized = clientName.toLowerCase().replace(/[^a-z0-9]/g, '_');
    return `${sanitized}.json`;
  }

  // Create and register client in one operation
  async createAndRegisterClient(config: LocalClientConfig): Promise<{
    configFile: string;
    registration: SuccessResponse;
  }> {
    const filename = this.generateConfigFilename(config.name);
    
    try {
      // First create the config file
      await this.createClientConfig(filename, config);
      
      // Then register the client
      const registration = await this.registerClient(config);
      
      return {
        configFile: filename,
        registration
      };
    } catch (error) {
      this.handleError(error, `Failed to create and register client ${config.name}`);
      throw error;
    }
  }

  // Check if a client is active
  async isClientActive(clientName: string): Promise<boolean> {
    try {
      const activeClients = await this.listActiveClients();
      return activeClients.includes(clientName);
    } catch (error) {
      this.handleError(error, `Failed to check if client ${clientName} is active`);
      return false;
    }
  }

  // Get client status (combines registered and active status)
  async getClientStatus(clientName: string): Promise<{
    registered: boolean;
    active: boolean;
    config?: LocalClientConfig;
  }> {
    try {
      const [registeredClients, activeClients] = await Promise.all([
        this.listClients(),
        this.listActiveClients()
      ]);

      const registered = registeredClients.includes(clientName);
      const active = activeClients.includes(clientName);

      let config: LocalClientConfig | undefined;
      if (registered) {
        try {
          config = await this.getClientById(clientName);
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
      this.handleError(error, `Failed to get client status for ${clientName}`);
      return {
        registered: false,
        active: false
      };
    }
  }

  // NEW MCP SERVER METHODS (API-compliant)

  // List all MCP server configurations
  async listMCPServers(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('mcp_server');
    } catch (error) {
      this.handleError(error, 'Failed to list MCP servers');
      throw error;
    }
  }

  // Get MCP server configuration by ID using proper API client
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
      // Store config in flat format that FastAPI expects (not nested)
      return await apiClient.config.createConfig('mcp_server', config);
    } catch (error) {
      this.handleError(error, `Failed to create MCP server ${name}`);
      throw error;
    }
  }

  // Update MCP server configuration
  async updateMCPServer(id: string, config: MCPServerConfig): Promise<{message: string}> {
    try {
      // Store config in flat format that FastAPI expects (not nested)
      return await apiClient.config.updateConfig('mcp_server', id, config);
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

  // Helper method to handle errors with user-friendly messages
  private handleError(error: unknown, context: string): void {
    if (error instanceof ApiError) {
      console.error('%s: %s', context, String(error.getDisplayMessage()), error.toJSON());
    } else if (error instanceof TimeoutError) {
      console.error('%s: Request timed out', context, error);
    } else if (error instanceof CancellationError) {
      console.error('%s: Request was cancelled', context, error);
    } else {
      console.error('%s: Unknown error', context, error);
    }
  }

  // Map API client ServerConfig to local ClientConfig
  private mapToLocalClientConfig(apiConfig: any): LocalClientConfig {
    return {
      name: apiConfig.name,
      server_path: apiConfig.server_path,
      roots: apiConfig.roots,
      capabilities: apiConfig.capabilities,
      timeout: apiConfig.timeout,
      routing_weight: apiConfig.routing_weight,
      exclude: apiConfig.exclude,
      gcp_secrets: apiConfig.gcp_secrets,
    };
  }

  // Map local ClientConfig to API client ServerConfig
  private mapToApiClientConfig(localConfig: LocalClientConfig): any {
    return {
      name: localConfig.name,
      server_path: localConfig.server_path,
      roots: localConfig.roots,
      capabilities: localConfig.capabilities,
      timeout: localConfig.timeout,
      routing_weight: localConfig.routing_weight,
      exclude: localConfig.exclude,
      gcp_secrets: localConfig.gcp_secrets,
    };
  }

  // Map API response to MCPServerConfig
  private mapToMCPServerConfig(apiConfig: any): MCPServerConfig {
    // Handle both flat and nested config structures during transition
    // Prioritize flat format (new) over nested format (old)
    let config;
    
    if (apiConfig.config && typeof apiConfig.config === 'object') {
      // Legacy nested format: { config: { ... }, name: ..., ... }
      config = apiConfig.config;
      console.log('📋 Using nested config format (legacy)');
    } else {
      // New flat format: { name: ..., type: ..., transport_type: ..., ... }
      config = apiConfig;
      console.log('📋 Using flat config format (current)');
    }
    
    return {
      name: config.name || apiConfig.name,
      type: "mcp_server",
      capabilities: config.capabilities || [],
      description: config.description,
      transport_type: config.transport_type,
      server_path: config.server_path,
      http_endpoint: config.http_endpoint,
      headers: config.headers,
      command: config.command,
      args: config.args,
      timeout: config.timeout,
      registration_timeout: config.registration_timeout,
      routing_weight: config.routing_weight,
      exclude: config.exclude,
      roots: config.roots,
    };
  }
}

export default new ClientsService();
