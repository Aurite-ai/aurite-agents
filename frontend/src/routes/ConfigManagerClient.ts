/**
 * Client for the Configuration Manager API endpoints
 *
 * The Configuration Manager handles all configuration for the Aurite Framework:
 * - Agents: AI assistants with specific capabilities and prompts
 * - LLMs: Language model configurations (OpenAI, Anthropic, etc.)
 * - MCP Servers: Tool providers for agents
 * - Workflows: Both simple (sequential) and custom (Python-based)
 *
 * Configurations are stored as JSON files and can be managed programmatically.
 */

import { BaseClient } from '../BaseClient';

export class ConfigManagerClient extends BaseClient {
  /**
   * List all configurations of a specific type
   *
   * Configuration types:
   * - 'agent': AI assistants
   * - 'llm': Language model configurations
   * - 'mcp_server': MCP server configurations
   * - 'simple_workflow': Sequential agent workflows
   * - 'custom_workflow': Python-based workflows
   *
   * @param configType - Type of configuration to list
   * @returns Array of configuration names
   * @throws Error if the config type is invalid
   *
   * @example
   * ```typescript
   * // List all configured agents
   * const agents = await client.config.listConfigs('agent');
   * console.log('Available agents:', agents);
   * // ['Weather Agent', 'Code Assistant', 'Research Agent']
   *
   * // List all LLM configurations
   * const llms = await client.config.listConfigs('llm');
   * // ['openai_gpt4', 'anthropic_claude', 'local_llama']
   * ```
   */
  async listConfigs(configType: string): Promise<string[]> {
    return this.request('GET', `/config/components/${configType}`);
  }

  /**
   * Get a specific configuration by type and name
   *
   * Returns the complete configuration object. The structure depends
   * on the configuration type:
   * - Agents include: name, system_prompt, llm_config_id, mcp_servers, etc.
   * - LLMs include: provider, model, temperature, max_tokens, etc.
   * - MCP servers include: transport_type, server_path, capabilities, etc.
   *
   * @param configType - Type of configuration
   * @param name - Name of the specific configuration
   * @returns Configuration object (structure varies by type)
   * @throws Error if the configuration is not found
   *
   * @example
   * ```typescript
   * // Get an agent configuration
   * const weatherAgent = await client.config.getConfig('agent', 'Weather Agent');
   * console.log(weatherAgent);
   * // {
   * //   name: 'Weather Agent',
   * //   description: 'An agent that provides weather information',
   * //   system_prompt: 'You are a helpful weather assistant...',
   * //   llm_config_id: 'anthropic_claude',
   * //   mcp_servers: ['weather_server'],
   * //   max_iterations: 5
   * // }
   *
   * // Get an LLM configuration
   * const llmConfig = await client.config.getConfig('llm', 'openai_gpt4');
   * // {
   * //   name: 'openai_gpt4',
   * //   provider: 'openai',
   * //   model: 'gpt-4-turbo-preview',
   * //   temperature: 0.7,
   * //   max_tokens: 2000
   * // }
   * ```
   */
  async getConfig(configType: string, name: string): Promise<any> {
    return this.request('GET', `/config/components/${configType}/${encodeURIComponent(name)}`);
  }

  /**
   * Create a new configuration
   *
   * The configuration object must include all required fields for the type.
   * The 'name' field is always required and must be unique within the type.
   *
   * @param configType - Type of configuration to create
   * @param config - Configuration object with all required fields
   * @returns Success message
   * @throws Error if validation fails or name already exists
   *
   * @example
   * ```typescript
   * // Create a new agent
   * await client.config.createConfig('agent', {
   *   name: 'Translation Agent',
   *   description: 'Translates text between languages',
   *   system_prompt: 'You are a professional translator...',
   *   llm_config_id: 'anthropic_claude',
   *   mcp_servers: ['translation_server'],
   *   max_iterations: 3,
   *   include_history: true
   * });
   *
   * // Create a new LLM configuration
   * await client.config.createConfig('llm', {
   *   name: 'fast_gpt',
   *   provider: 'openai',
   *   model: 'gpt-3.5-turbo',
   *   temperature: 0.3,
   *   max_tokens: 1000,
   *   api_key_env_var: 'OPENAI_API_KEY'
   * });
   * ```
   */
  async createConfig(configType: string, config: any): Promise<{ message: string }> {
    // Extract name from config and prepare the request body
    const { name, ...configData } = config;
    return this.request('POST', `/config/components/${configType}`, {
      name,
      config: configData
    });
  }

  /**
   * Update an existing configuration
   *
   * The entire configuration object must be provided, not just the fields
   * to update. The 'name' field must match the existing configuration.
   *
   * @param configType - Type of configuration to update
   * @param name - Current name of the configuration
   * @param config - Complete updated configuration object
   * @returns Success message
   * @throws Error if the configuration doesn't exist or validation fails
   *
   * @example
   * ```typescript
   * // Update an agent's system prompt
   * const agent = await client.config.getConfig('agent', 'Weather Agent');
   * agent.system_prompt = 'You are an expert meteorologist...';
   * agent.max_iterations = 10;
   *
   * await client.config.updateConfig('agent', 'Weather Agent', agent);
   *
   * // Update LLM temperature
   * const llm = await client.config.getConfig('llm', 'creative_gpt');
   * llm.temperature = 0.9;
   * await client.config.updateConfig('llm', 'creative_gpt', llm);
   * ```
   */
  async updateConfig(configType: string, name: string, config: any): Promise<{ message: string }> {
    // Remove name from config since it's in the URL
    const { name: _, ...configData } = config;
    return this.request('PUT', `/config/components/${configType}/${encodeURIComponent(name)}`, {
      config: configData
    });
  }

  /**
   * Delete a configuration
   *
   * Warning: This permanently removes the configuration. Agents or workflows
   * using this configuration will fail if not updated.
   *
   * @param configType - Type of configuration to delete
   * @param name - Name of the configuration to delete
   * @returns Success message
   * @throws Error if the configuration doesn't exist
   *
   * @example
   * ```typescript
   * // Delete an agent
   * await client.config.deleteConfig('agent', 'Old Agent');
   *
   * // Delete an LLM configuration
   * await client.config.deleteConfig('llm', 'deprecated_model');
   * ```
   */
  async deleteConfig(configType: string, name: string): Promise<{ message: string }> {
    return this.request('DELETE', `/config/components/${configType}/${encodeURIComponent(name)}`);
  }

  /**
   * Reload all configurations from disk
   *
   * This forces the server to re-read all configuration files.
   * Useful when configurations have been modified directly on disk
   * or through external tools.
   *
   * Note: This may briefly interrupt ongoing operations.
   *
   * @returns Success message
   * @example
   * ```typescript
   * // After manually editing config files
   * await client.config.reloadConfigs();
   * console.log('Configurations reloaded from disk');
   * ```
   */
  async reloadConfigs(): Promise<{ message: string }> {
    return this.request('POST', '/config/refresh');
  }

  /**
   * Validate a component's configuration
   *
   * Checks that the component has all required fields and that
   * the values meet the expected criteria for the component type.
   *
   * @param configType - Type of configuration to validate
   * @param name - Name of the configuration to validate
   * @returns Success message if valid
   * @throws Error with validation details if invalid
   *
   * @example
   * ```typescript
   * // Validate an agent configuration
   * try {
   *   await client.config.validateConfig('agent', 'Weather Agent');
   *   console.log('Configuration is valid');
   * } catch (error) {
   *   console.error('Validation failed:', error.message);
   * }
   * ```
   */
  async validateConfig(configType: string, name: string): Promise<{ message: string }> {
    return this.request('POST', `/config/components/${configType}/${encodeURIComponent(name)}/validate`);
  }
}
