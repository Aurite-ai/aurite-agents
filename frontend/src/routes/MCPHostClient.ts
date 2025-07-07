/**
 * Client for the MCP Host API endpoints
 *
 * The MCP (Model Context Protocol) Host manages connections to MCP servers that provide:
 * - Tools: Functions that agents can call (e.g., weather lookup, file operations)
 * - Resources: Data sources that agents can access
 * - Prompts: Pre-defined prompt templates
 *
 * MCP servers can be local Python scripts or remote HTTP services.
 */

import { BaseClient } from '../BaseClient';
import type { ServerConfig, ToolCallResult } from '../types';

export class MCPHostClient extends BaseClient {
  /**
   * Get the status of the MCP Host
   *
   * Returns information about the host's current state, including
   * the number of tools currently available from all registered servers.
   *
   * @returns Host status and tool count
   * @example
   * ```typescript
   * const status = await client.host.getStatus();
   * console.log(`Host is ${status.status} with ${status.tool_count} tools available`);
   * ```
   */
  async getStatus(): Promise<{ status: string; tool_count: number }> {
    return this.request('GET', '/host/status');
  }

  /**
   * List all available tools from registered MCP servers
   *
   * Tools are functions that agents can call during conversations.
   * Each tool has:
   * - A unique name
   * - A description of what it does
   * - An input schema defining required parameters
   *
   * @returns Array of tool definitions
   * @example
   * ```typescript
   * const tools = await client.host.listTools();
   * tools.forEach(tool => {
   *   console.log(`${tool.name}: ${tool.description}`);
   * });
   * ```
   */
  async listTools(): Promise<Array<{
    name: string;
    description?: string;
    inputSchema: any;
  }>> {
    return this.request('GET', '/host/tools');
  }

  /**
   * Register an MCP server by its configured name
   *
   * This method looks up the server configuration by name and registers it.
   * The server must be pre-configured in the Aurite configuration files.
   *
   * Once registered, the server's tools become available for agents to use.
   *
   * @param serverName - Name of the pre-configured server
   * @returns Registration result with server name
   * @throws Error if the server configuration is not found
   *
   * @example
   * ```typescript
   * // Register a weather server (must be configured in Aurite)
   * await client.host.registerServerByName('weather_server');
   *
   * // Now agents can use weather tools
   * const tools = await client.host.listTools();
   * // tools now includes weather_lookup, etc.
   * ```
   */
  async registerServerByName(serverName: string): Promise<{ status: string; name: string }> {
    return this.request('POST', `/host/register/${encodeURIComponent(serverName)}`);
  }

  /**
   * Register an MCP server with a custom configuration
   *
   * This method allows dynamic server registration without pre-configuration.
   * Useful for:
   * - Temporary servers
   * - Testing new servers
   * - Dynamic server discovery
   *
   * @param config - Complete server configuration
   * @returns Registration result with server name
   * @throws Error if registration fails
   *
   * @example
   * ```typescript
   * // Register a custom local server
   * await client.host.registerServerByConfig({
   *   name: 'my_custom_server',
   *   server_path: '/path/to/server.py',
   *   transport_type: 'stdio',
   *   capabilities: ['tools'],
   *   timeout: 30
   * });
   *
   * // Register an HTTP streaming server
   * await client.host.registerServerByConfig({
   *   name: 'remote_server',
   *   http_endpoint: 'https://api.example.com/mcp',
   *   transport_type: 'http_stream',
   *   headers: { 'Authorization': 'Bearer token' }
   * });
   * ```
   */
  async registerServerByConfig(config: ServerConfig): Promise<{ status: string; name: string }> {
    return this.request('POST', '/host/register/config', config);
  }

  /**
   * Unregister an MCP server
   *
   * Removes a server and all its tools from the host.
   * Any agents currently using the server's tools will receive errors.
   *
   * @param serverName - Name of the server to unregister
   * @returns Unregistration result
   * @throws Error if the server is not found
   *
   * @example
   * ```typescript
   * // Clean up when done
   * await client.host.unregisterServer('weather_server');
   * ```
   */
  async unregisterServer(serverName: string): Promise<{ status: string; name: string }> {
    return this.request('DELETE', `/host/servers/${encodeURIComponent(serverName)}`);
  }

  /**
   * Call a tool directly (without going through an agent)
   *
   * This is useful for:
   * - Testing tools before using them in agents
   * - Building custom integrations
   * - Debugging tool behavior
   *
   * Note: The tool must be available (its server must be registered).
   *
   * @param toolName - Name of the tool to call
   * @param args - Arguments to pass to the tool
   * @returns Tool execution result
   * @throws Error if the tool is not found or execution fails
   *
   * @example
   * ```typescript
   * // Call a weather lookup tool directly
   * const result = await client.host.callTool('weather_lookup', {
   *   location: 'San Francisco'
   * });
   *
   * console.log(result.content[0].text);
   * // "Weather for San Francisco: Sunny, 72°F..."
   *
   * // Call a calculation tool
   * const calcResult = await client.host.callTool('calculate', {
   *   expression: '2 + 2'
   * });
   * ```
   */
  async callTool(toolName: string, args: Record<string, any>): Promise<ToolCallResult> {
    return this.request('POST', `/host/tools/${encodeURIComponent(toolName)}/call`, { args });
  }
}
