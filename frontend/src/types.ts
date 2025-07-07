/**
 * Shared TypeScript types and interfaces for the Aurite API Client
 */

// ==================== Request Types ====================

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

// ==================== Response Types ====================

/**
 * Result from agent execution
 */
export interface AgentRunResult {
  /** The execution status */
  status: 'success' | 'error' | 'max_iterations_reached';
  /** The final response from the agent (if successful) */
  final_response?: {
    role: string;
    content: string;
  };
  /** Complete conversation history including all messages and tool calls */
  conversation_history: Array<{
    role: string;
    content?: string;
    tool_calls?: any[];
  }>;
  /** Error message if the execution failed */
  error_message?: string;
}

/**
 * Result from workflow execution
 */
export interface WorkflowExecutionResult {
  /** Overall workflow status */
  status: 'success' | 'error';
  /** Details about each step in the workflow */
  steps: Array<{
    step_name: string;
    status: 'success' | 'error';
    result?: any;
    error?: string;
  }>;
  /** Final output from the workflow */
  final_output?: any;
  /** Error message if the workflow failed */
  error_message?: string;
}

/**
 * Result from tool execution
 */
export interface ToolCallResult {
  /** Content returned by the tool */
  content: Array<{
    type: string;
    text?: string;
  }>;
  /** Whether the tool execution resulted in an error */
  isError?: boolean;
}

// ==================== Configuration Types ====================

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

// ==================== Streaming Types ====================

/**
 * Events emitted during agent streaming
 */
export interface StreamEvent {
  /** The type of event */
  type: 'llm_response_start' | 'llm_response' | 'llm_response_stop' | 'tool_call' | 'tool_output' | 'error';
  /** Event-specific data */
  data: any;
}

// ==================== API Configuration ====================

/**
 * Configuration for the API client
 */
export interface ApiConfig {
  /** Base URL of the Aurite API (e.g., http://localhost:8000) */
  baseUrl: string;
  /** API key for authentication */
  apiKey: string;
}
