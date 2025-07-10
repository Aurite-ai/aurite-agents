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

import { BaseClient } from '../client/BaseClient';
import type { ServerConfig, ToolCallResult, ServerDetailedStatus, ServerRuntimeInfo, ToolDetails, ServerTestResult } from '../types';
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
    return this.request('GET', '/tools/status');
  }

  /**
   * List all available tools from registered MCP servers.
   *
   * Tools are functions that agents can call during conversations.
   *
   * @returns Array of tool definitions.
   * @example
   * ```typescript
   * const tools = await client.host.listTools();
   * tools.forEach(tool => {
   *   console.log(`${tool.name}: ${tool.description}`);
   * });
   * ```
   */
  async listTools(): Promise<ToolDetails[]> {
    return this.request('GET', '/tools/');
  }

  /**
   * Get detailed information about a specific tool.
   *
   * @param toolName - The name of the tool.
   * @returns Detailed information about the tool.
   */
  async getToolDetails(toolName: string): Promise<ToolDetails> {
    return this.request('GET', `/tools/${encodeURIComponent(toolName)}`);
  }

  /**
   * Call a tool directly (without going through an agent).
   *
   * This is useful for testing tools, building custom integrations, or debugging.
   * The tool's server must be registered.
   *
   * @param toolName - Name of the tool to call.
   * @param args - Arguments to pass to the tool.
   * @returns The result of the tool execution.
   * @throws Error if the tool is not found or execution fails.
   */
  async callTool(toolName: string, args: Record<string, any>): Promise<ToolCallResult> {
    return this.request('POST', `/tools/${encodeURIComponent(toolName)}/call`, { args });
  }

  /**
   * List all currently registered MCP servers with runtime information.
   *
   * @returns An array of server runtime information objects.
   */
  async listRegisteredServers(): Promise<ServerRuntimeInfo[]> {
    return this.request('GET', '/tools/servers');
  }

  /**
   * Get detailed runtime status for a specific MCP server.
   *
   * @param serverName - The name of the server.
   * @returns Detailed status information for the server.
   */
  async getServerStatus(serverName: string): Promise<ServerDetailedStatus> {
    return this.request('GET', `/tools/servers/${encodeURIComponent(serverName)}`);
  }

  /**
   * List all tools provided by a specific registered server.
   *
   * @param serverName - The name of the server.
   * @returns A list of tools with their full details.
   */
  async getServerTools(serverName: string): Promise<ToolDetails[]> {
    return this.request('GET', `/tools/servers/${encodeURIComponent(serverName)}/tools`);
  }

  /**
   * Test an MCP server configuration by temporarily registering it.
   *
   * @param serverName - The name of the server configuration to test.
   * @returns The result of the server test.
   */
  async testServer(serverName: string): Promise<ServerTestResult> {
    return this.request('POST', `/tools/servers/${encodeURIComponent(serverName)}/test`);
  }

  /**
   * Register an MCP server by its configured name.
   *
   * The server must be pre-configured in the Aurite configuration files.
   *
   * @param serverName - Name of the pre-configured server.
   * @returns Registration result with server name.
   */
  async registerServerByName(serverName: string): Promise<{ status: string; name: string }> {
    return this.request('POST', `/tools/register/${encodeURIComponent(serverName)}`);
  }

  /**
   * Register an MCP server with a custom configuration.
   *
   * This method allows dynamic server registration without pre-configuration.
   *
   * @param config - Complete server configuration.
   * @returns Registration result with server name.
   */
  async registerServerByConfig(config: ServerConfig): Promise<{ status: string; name: string }> {
    return this.request('POST', '/tools/register/config', config);
  }

  /**
   * Unregister an MCP server.
   *
   * Removes a server and all its tools from the host.
   *
   * @param serverName - Name of the server to unregister.
   * @returns Unregistration result.
   */
  async unregisterServer(serverName: string): Promise<{ status: string; name: string }> {
    return this.request('DELETE', `/tools/servers/${encodeURIComponent(serverName)}`);
  }
}
