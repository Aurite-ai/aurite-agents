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
  /** Unique name for the agent */
  name: string;
  /** Optional description */
  description?: string;
  /** System prompt for the agent */
  system_prompt: string;
  /** LLM configuration ID to use */
  llm_config_id: string;
  /** Optional MCP servers to connect */
  mcp_servers?: string[];
  /** Maximum iterations for agent execution */
  max_iterations?: number;
  /** Whether to include conversation history */
  include_history?: boolean;
  /** Temperature override for this agent */
  temperature_override?: number;
}

/**
 * LLM configuration interface
 */
export interface LLMConfig {
  /** Unique name for the LLM config */
  name: string;
  /** LLM provider */
  provider: 'openai' | 'anthropic' | 'local' | 'azure';
  /** Model name/identifier */
  model: string;
  /** Temperature setting */
  temperature?: number;
  /** Maximum tokens */
  max_tokens?: number;
  /** Environment variable name for API key */
  api_key_env_var?: string;
  /** Base URL for the API */
  base_url?: string;
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
