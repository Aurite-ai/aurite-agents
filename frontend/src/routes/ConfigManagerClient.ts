/* eslint-disable no-unused-vars */
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

import { BaseClient } from '../client/BaseClient';

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
   * @returns Array of configuration objects (or strings for backward compatibility)
   * @throws Error if the config type is invalid
   *
   * @example
   * ```typescript
   * // List all configured agents
   * const agents = await client.config.listConfigs('agent');
   * console.log('Available agents:', agents);
   * // [{ name: 'Weather Agent', ... }, { name: 'Code Assistant', ... }]
   *
   * // Extract just the names
   * const agentNames = agents.map(a => typeof a === 'string' ? a : a.name);
   * // ['Weather Agent', 'Code Assistant', 'Research Agent']
   * ```
   */
  async listConfigs(configType: string): Promise<Array<any>> {
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
   * // Create a new agent in a specific project and file
   * await client.config.createConfig('agent', {
   *   name: 'My New Agent',
   *   description: 'This is a test agent.',
   *   system_prompt: 'You are a test agent.',
   *   llm_config_id: 'my_openai_gpt4_turbo'
   * }, { project: 'project_bravo', filePath: 'new_agents.json' });
   * ```
   */
  async createConfig(
    configType: string,
    config: any,
    options: { project?: string; workspace?: boolean; filePath?: string } = {}
  ): Promise<{ message: string }> {
    const { name, ...configData } = config;
    const body = {
      name,
      config: {
        ...configData,
        project: options.project,
        workspace: options.workspace,
        file_path: options.filePath,
      },
    };
    return this.request('POST', `/config/components/${configType}`, body);
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
      config: configData,
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
    return this.request(
      'POST',
      `/config/components/${configType}/${encodeURIComponent(name)}/validate`
    );
  }

  /**
   * List all configuration source directories
   *
   * Returns a list of all directories being monitored for configuration files,
   * in priority order. Each source includes context information (project/workspace/user)
   * and associated names.
   *
   * @returns Array of configuration sources with metadata
   *
   * @example
   * ```typescript
   * const sources = await client.config.listConfigSources();
   * sources.forEach(source => {
   *   console.log(`${source.context} source: ${source.path}`);
   *   if (source.project_name) {
   *     console.log(`  Project: ${source.project_name}`);
   *   }
   * });
   * ```
   */
  async listConfigSources(): Promise<
    Array<{
      path: string;
      context: 'project' | 'workspace' | 'user';
      project_name?: string;
      workspace_name?: string;
    }>
  > {
    return this.request('GET', '/config/sources');
  }

  /**
   * List all configuration files for a given source
   *
   * Returns a comprehensive list of all configuration files found in the
   * specified configuration source.
   * This is useful for understanding what configurations are available and where
   * they are located.
   *
   * @param sourceName - The name of the source to list files for
   * @returns Array of configuration file paths
   *
   * @example
   * ```typescript
   * const files = await client.config.listConfigFiles('my_project');
   *
   * // Show workspace files
   * console.log('Workspace configuration files:');
   * byContext.workspace?.forEach(file => {
   *   if (!acc[file.context]) acc[file.context] = [];
   *   acc[file.context].push(file);
   *   return acc;
   * }, {} as Record<string, typeof files>);
   *
   * // Show workspace files
   * console.log('Workspace configuration files:');
   * byContext.workspace?.forEach(file => {
   *   console.log(`  ${file.path}`);
   * });
   * ```
   */
  async listConfigFiles(sourceName: string): Promise<string[]> {
    return this.request('GET', `/config/files/${sourceName}`);
  }

  /**
   * Get the content of a specific configuration file.
   *
   * @param sourceName - The name of the source the file belongs to.
   * @param filePath - The relative path of the file within the source.
   * @returns The file content as a string.
   * @throws Error if the file is not found.
   */
  async getFileContent(sourceName: string, filePath: string): Promise<string> {
    return this.request('GET', `/config/files/${sourceName}/${filePath}`);
  }

  /**
   * Create a new configuration file.
   *
   * @param sourceName - The name of the source to create the file in.
   * @param relativePath - The relative path for the new file.
   * @param content - The content to write to the file.
   * @returns A success message.
   * @throws Error if the file creation fails.
   */
  async createConfigFile(
    sourceName: string,
    relativePath: string,
    content: string
  ): Promise<{ message: string }> {
    return this.request('POST', '/config/files', {
      source_name: sourceName,
      relative_path: relativePath,
      content,
    });
  }

  /**
   * Update an existing configuration file.
   *
   * @param sourceName - The name of the source where the file exists.
   * @param relativePath - The relative path of the file to update.
   * @param content - The new content to write to the file.
   * @returns A success message.
   * @throws Error if the file update fails.
   */
  async updateConfigFile(
    sourceName: string,
    relativePath: string,
    content: string
  ): Promise<{ message: string }> {
    return this.request('PUT', `/config/files/${sourceName}/${relativePath}`, { content });
  }

  /**
   * Delete an existing configuration file.
   *
   * @param sourceName - The name of the source where the file exists.
   * @param relativePath - The relative path of the file to delete.
   * @returns A success message.
   * @throws Error if the file deletion fails.
   */
  async deleteConfigFile(sourceName: string, relativePath: string): Promise<{ message: string }> {
    return this.request('DELETE', `/config/files/${sourceName}/${relativePath}`);
  }

  /**
   * Validate all components in the system.
   *
   * @returns A list of validation errors, or an empty list if all are valid.
   * @throws Error if the validation fails.
   */
  async validateAllConfigs(): Promise<any[]> {
    return this.request('POST', '/config/validate');
  }
}
