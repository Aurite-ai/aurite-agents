/**
 * Request payload types for API calls
 */

/**
 * Request payload for running an agent
 */
export interface AgentRunRequest {
  /** The message from the user to send to the agent */
  user_message: string;
  /** Optional custom system prompt to override the agent's default */
  system_prompt?: string;
  /** Optional session ID for maintaining conversation history */
  session_id?: string;
}

/**
 * Request payload for running workflows
 */
export interface WorkflowRunRequest {
  /** The initial input data for the workflow */
  initial_input: any;
  /** Optional session ID for workflow execution tracking */
  session_id?: string;
}

/**
 * Arguments for tool execution
 */
export interface ToolCallArgs {
  /** Key-value pairs of arguments required by the tool */
  args: Record<string, any>;
}

/**
 * Agent configuration interface
 */
export interface AgentConfig {
  // Core Identity
  /** Component type (automatically set to "agent") */
  type?: 'agent';
  /** Unique name for the agent */
  name: string;
  /** Optional description */
  description?: string;

  // LLM Configuration
  /** LLM configuration ID to use */
  llm_config_id?: string;
  
  // LLM Override Parameters (optional, overrides llm_config_id settings)
  /** Model name/identifier override */
  model?: string;
  /** Temperature setting (0.0-2.0) override */
  temperature?: number;
  /** Maximum tokens to generate override */
  max_tokens?: number;

  // Behavior Control
  /** System prompt for the agent */
  system_prompt?: string;
  /** Maximum iterations for agent execution */
  max_iterations?: number;
  /** Whether to include conversation history */
  include_history?: boolean;
  /** Whether the agent runs automatically */
  auto?: boolean;

  // Capability Management
  /** Optional MCP servers to connect */
  mcp_servers?: string[];
  /** Components to exclude from agent */
  exclude_components?: string[];

  // Framework Metadata (read-only, added by system)
  /** Source file path */
  _source_file?: string;
  /** Context path */
  _context_path?: string;
  /** Context level */
  _context_level?: string;
  /** Project name */
  _project_name?: string;
  /** Workspace name */
  _workspace_name?: string;
}

/**
 * LLM configuration interface
 */
export interface LLMConfig {
  /** Unique name for the LLM config */
  name: string;
  /** Component type (automatically set to "llm") */
  type: 'llm';
  /** LLM provider (e.g., "anthropic", "openai", "gemini") */
  provider: string;
  /** Model name/identifier */
  model: string;
  /** Brief description of the LLM config */
  description?: string;
  /** Temperature setting (0.0-2.0) */
  temperature?: number;
  /** Maximum tokens to generate */
  max_tokens?: number;
  /** Default system prompt for this LLM */
  default_system_prompt?: string;
  /** Base URL for the LLM API */
  api_base?: string;
  /** API key for the LLM */
  api_key?: string;
  /** API version for the LLM */
  api_version?: string;
  /** Environment variable name for API key */
  api_key_env_var?: string;
}

/**
 * MCP Server configuration
 */
export interface ServerConfig {
  /** Unique name for the server */
  name: string;
  /** Path to the server executable (for stdio transport) */
  server_path?: string;
  /** Command to execute (for local transport) */
  command?: string;
  /** Command arguments */
  args?: string[];
  /** Transport type for server communication */
  transport_type?: 'stdio' | 'local' | 'http_stream';
  /** HTTP endpoint URL (for http_stream transport) */
  http_endpoint?: string;
  /** HTTP headers (for http_stream transport) */
  headers?: Record<string, string>;
  /** Server capabilities */
  capabilities?: string[];
  /** Connection timeout in seconds */
  timeout?: number;
}
