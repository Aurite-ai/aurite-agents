/**
 * Response types from API calls
 */

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

/**
 * Detailed information about a specific tool.
 */
export interface ToolDetails {
  name: string;
  description: string;
  server_name: string;
  inputSchema: Record<string, any>;
}

/**
 * Events emitted during agent streaming
 */
export interface StreamEvent {
  /** The type of event */
  type:
    | 'llm_response_start'
    | 'llm_response'
    | 'llm_response_stop'
    | 'tool_call'
    | 'tool_output'
    | 'error';
  /** Event-specific data */
  data: any;
}

/**
 * Streaming options for agent execution
 */
export interface StreamingOptions {
  /** Timeout for streaming connection */
  timeout?: number;
  /** AbortSignal for cancelling the stream */
  signal?: AbortSignal;
}

/**
 * Status types for workflows
 */
export type WorkflowStatus = 'success' | 'error';
export type StepStatus = 'success' | 'error';

export interface ServerDetailedStatus {
  name: string;
  registered: boolean;
  status: string;
  transport_type?: string;
  tools: string[];
  registration_time?: string; // ISO 8601 date string
  session_active: boolean;
}

/**
 * Runtime information about a registered MCP server.
 */
export interface ServerRuntimeInfo {
  name: string;
  status: string;
  transport_type: string;
  tools_count: number;
  registration_time: string; // ISO 8601 date string
}

/**
 * Result of testing an MCP server configuration.
 */
export interface ServerTestResult {
  status: 'success' | 'failed';
  server_name: string;
  connection_time?: number;
  tools_discovered?: string[];
  test_tool_result?: Record<string, any>;
  error?: string;
}
