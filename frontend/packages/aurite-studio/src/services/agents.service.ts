import apiClient from './apiClient';
import { 
  AgentConfig as LocalAgentConfig,
  AgentExecutionResult as LocalAgentExecutionResult,
  ExecuteAgentRequest,
  SuccessResponse,
} from '../types';
import {
  ApiError,
  TimeoutError,
  CancellationError,
  AgentRunRequest,
  AgentRunResult,
} from '@aurite/api-client';

class AgentsService {
  // List all registered agents (components)
  async listAgents(): Promise<string[]> {
    try {
      // This maps to listing registered components
      const response = await apiClient.config.listConfigs('agent');
      return response;
    } catch (error) {
      this.handleError(error, 'Failed to list agents');
      throw error;
    }
  }

  // List agent configuration files
  async listAgentConfigs(): Promise<string[]> {
    try {
      return await apiClient.config.listConfigs('agent');
    } catch (error) {
      this.handleError(error, 'Failed to list agent configurations');
      throw error;
    }
  }

  // Get agent configuration by ID/name
  async getAgentById(id: string): Promise<LocalAgentConfig> {
    try {
      const config = await apiClient.config.getConfig('agent', id);
      return this.mapToLocalAgentConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get agent configuration for ${id}`);
      throw error;
    }
  }

  // Get agent configuration by filename
  async getAgentConfig(filename: string): Promise<LocalAgentConfig> {
    try {
      const config = await apiClient.config.getConfig('agent', filename);
      return this.mapToLocalAgentConfig(config);
    } catch (error) {
      this.handleError(error, `Failed to get agent configuration ${filename}`);
      throw error;
    }
  }

  // Create new agent configuration file
  async createAgentConfig(filename: string, config: LocalAgentConfig): Promise<LocalAgentConfig> {
    try {
      const apiConfig = this.mapToApiAgentConfig(config);
      const result = await apiClient.config.createConfig('agent', apiConfig);
      return this.mapToLocalAgentConfig(result);
    } catch (error) {
      this.handleError(error, `Failed to create agent configuration ${filename}`);
      throw error;
    }
  }

  // Update existing agent configuration
  async updateAgentConfig(filename: string, config: LocalAgentConfig): Promise<LocalAgentConfig> {
    try {
      const apiConfig = this.mapToApiAgentConfig(config);
      const result = await apiClient.config.updateConfig('agent', filename, apiConfig);
      return this.mapToLocalAgentConfig(result);
    } catch (error) {
      this.handleError(error, `Failed to update agent configuration ${filename}`);
      throw error;
    }
  }

  // Delete agent configuration
  async deleteAgentConfig(filename: string): Promise<void> {
    try {
      await apiClient.config.deleteConfig('agent', filename);
    } catch (error) {
      this.handleError(error, `Failed to delete agent configuration ${filename}`);
      throw error;
    }
  }

  // Register an agent (reload configs)
  async registerAgent(config: LocalAgentConfig): Promise<SuccessResponse> {
    try {
      await apiClient.config.reloadConfigs();
      return {
        status: 'success',
        message: `Agent ${config.name} registered successfully`
      };
    } catch (error) {
      this.handleError(error, `Failed to register agent ${config.name}`);
      throw error;
    }
  }

  // Execute an agent
  async executeAgent(
    agentName: string, 
    request: ExecuteAgentRequest
  ): Promise<LocalAgentExecutionResult> {
    try {
      const apiRequest: AgentRunRequest = {
        user_message: request.user_message,
        system_prompt: request.system_prompt,
      };
      
      const result: AgentRunResult = await apiClient.execution.runAgent(agentName, apiRequest);
      
      return this.mapToLocalExecutionResult(result);
    } catch (error) {
      this.handleError(error, `Failed to execute agent ${agentName}`);
      throw error;
    }
  }

  // Helper to generate a unique filename for agent config
  generateConfigFilename(agentName: string): string {
    const sanitized = agentName.toLowerCase().replace(/[^a-z0-9]/g, '_');
    return `${sanitized}.json`;
  }

  // Create and register agent in one operation
  async createAndRegisterAgent(config: LocalAgentConfig): Promise<{
    configFile: string;
    registration: SuccessResponse;
  }> {
    const filename = this.generateConfigFilename(config.name);
    
    try {
      // First create the config file
      await this.createAgentConfig(filename, config);
      
      // Then register the agent
      const registration = await this.registerAgent(config);
      
      return {
        configFile: filename,
        registration
      };
    } catch (error) {
      this.handleError(error, `Failed to create and register agent ${config.name}`);
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

  // Map API client AgentConfig to local AgentConfig
  private mapToLocalAgentConfig(apiConfig: any): LocalAgentConfig {
    return {
      // Core Identity
      name: apiConfig.name,
      description: apiConfig.description,
      
      // LLM Configuration - CRITICAL: Include llm_config_id
      llm_config_id: apiConfig.llm_config_id,
      
      // LLM Override Parameters
      model: apiConfig.model,
      temperature: apiConfig.temperature,
      max_tokens: apiConfig.max_tokens,
      
      // Behavior Control
      system_prompt: apiConfig.system_prompt,
      max_iterations: apiConfig.max_iterations,
      include_history: apiConfig.include_history,
      auto: apiConfig.auto,
      
      // Capability Management
      mcp_servers: apiConfig.mcp_servers,
      exclude_components: apiConfig.exclude_components,
      
      // Framework Metadata (preserve if present)
      _source_file: apiConfig._source_file,
      _context_path: apiConfig._context_path,
      _context_level: apiConfig._context_level,
      _project_name: apiConfig._project_name,
      _workspace_name: apiConfig._workspace_name,
    };
  }

  // Map local AgentConfig to API client AgentConfig
  private mapToApiAgentConfig(localConfig: LocalAgentConfig): any {
    return {
      // Core Identity
      type: 'agent',
      name: localConfig.name,
      description: localConfig.description,
      
      // LLM Configuration - CRITICAL: Include llm_config_id
      llm_config_id: localConfig.llm_config_id,
      
      // LLM Override Parameters
      model: localConfig.model,
      temperature: localConfig.temperature,
      max_tokens: localConfig.max_tokens,
      
      // Behavior Control
      system_prompt: localConfig.system_prompt,
      max_iterations: localConfig.max_iterations,
      include_history: localConfig.include_history,
      auto: localConfig.auto,
      
      // Capability Management
      mcp_servers: localConfig.mcp_servers,
      exclude_components: localConfig.exclude_components,
    };
  }

  // Map API client AgentRunResult to local AgentExecutionResult
  private mapToLocalExecutionResult(apiResult: AgentRunResult): LocalAgentExecutionResult {
    return {
      final_response: apiResult.final_response ? {
        role: apiResult.final_response.role,
        content: [{ type: 'text', text: apiResult.final_response.content }],
      } : undefined,
      error: apiResult.error_message || null,
      history: apiResult.conversation_history || [],
    };
  }
}

export default new AgentsService();
