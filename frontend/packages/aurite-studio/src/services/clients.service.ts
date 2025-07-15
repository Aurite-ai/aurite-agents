import apiClient from './apiClient';
import { 
  ClientConfig as LocalClientConfig,
  SuccessResponse
} from '../types';
import {
  ApiError,
  TimeoutError,
  CancellationError,
  ServerConfig,
  ToolDetails,
} from '@aurite/api-client';

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
}

export default new ClientsService();
