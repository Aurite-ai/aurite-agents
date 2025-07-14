/**
 * Main Aurite API Client
 *
 * This is the primary entry point for interacting with the Aurite Framework API.
 * It provides a unified interface to all API endpoints through specialized sub-clients.
 *
 * The client is organized into three main areas:
 * - execution: Run agents and workflows
 * - host: Manage MCP servers and tools
 * - config: Manage configurations
 */

import type { ApiConfig } from '../types';
import { ExecutionFacadeClient } from '../routes/ExecutionFacadeClient';
import { MCPHostClient } from '../routes/MCPHostClient';
import { ConfigManagerClient } from '../routes/ConfigManagerClient';
import { SystemClient } from '../routes/SystemClient';

export class AuriteApiClient {
  /**
   * Client for agent and workflow execution
   *
   * Use this to:
   * - Run agents with user messages
   * - Stream agent responses in real-time
   * - Execute simple and custom workflows
   */
  public readonly execution: ExecutionFacadeClient;

  /**
   * Client for MCP server and tool management
   *
   * Use this to:
   * - Register/unregister MCP servers
   * - List available tools
   * - Call tools directly
   */
  public readonly host: MCPHostClient;

  /**
   * Client for configuration management
   *
   * Use this to:
   * - Create, read, update, delete configurations
   * - Manage agents, LLMs, servers, and workflows
   * - Reload configurations from disk
   */
  public readonly config: ConfigManagerClient;

  /**
   * Client for system management
   *
   * Use this to:
   * - Get system information
   * - Get framework version
   * - Get system capabilities
   */
  public readonly system: SystemClient;

  constructor(config: ApiConfig) {
    this.execution = new ExecutionFacadeClient(config);
    this.host = new MCPHostClient(config);
    this.config = new ConfigManagerClient(config);
    this.system = new SystemClient(config);
  }
}

/**
 * Create a new Aurite API client instance
 *
 * This is the recommended way to create a client. It ensures proper
 * initialization and provides a clean API surface.
 *
 * @param baseUrl - Base URL of the Aurite API (e.g., http://localhost:8000)
 * @param apiKey - API key for authentication
 * @returns Configured AuriteApiClient instance
 *
 * @example
 * ```typescript
 * import { createAuriteClient } from '@aurite/api-client';
 *
 * const client = createAuriteClient('http://localhost:8000', 'your-api-key');
 *
 * // Now you can use the client
 * const agents = await client.config.listConfigs('agent');
 * const result = await client.execution.runAgent('Weather Agent', {
 *   user_message: 'What is the weather?'
 * });
 * ```
 */
export function createAuriteClient(baseUrl: string, apiKey: string): AuriteApiClient {
  return new AuriteApiClient({ baseUrl, apiKey });
}

/**
 * Create a new Aurite API client instance using environment configuration
 *
 * This convenience function automatically loads configuration from environment
 * variables and .env files. It's the easiest way to create a client for
 * development and testing.
 *
 * @param overrides - Optional configuration overrides
 * @returns Configured AuriteApiClient instance
 *
 * @example
 * ```typescript
 * import { createAuriteClientFromEnv } from '@aurite/api-client';
 *
 * // Uses AURITE_API_BASE_URL and API_KEY from environment
 * const client = createAuriteClientFromEnv();
 *
 * // Or with overrides
 * const client = createAuriteClientFromEnv({
 *   baseUrl: 'http://custom-server:8000'
 * });
 * ```
 */
export async function createAuriteClientFromEnv(
  overrides?: Partial<ApiConfig>
): Promise<AuriteApiClient> {
  // Import here to avoid circular dependencies and ensure environment is loaded
  const { getApiClientConfig } = await import('../config/browser-environment.js');
  const config = getApiClientConfig(overrides);
  return new AuriteApiClient(config);
}

// Re-export types for convenience
export * from '../types';
export { ExecutionFacadeClient } from '../routes/ExecutionFacadeClient';
export { MCPHostClient } from '../routes/MCPHostClient';
export { ConfigManagerClient } from '../routes/ConfigManagerClient';
