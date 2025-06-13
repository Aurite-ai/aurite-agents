// frontend/src/types/projectManagement.ts

// Based on src/config/config_models.py
export interface GCPSecretConfig {
  secret_id: string;
  env_var_name: string;
}

export interface RootConfig {
  uri: string;
  name: string;
  capabilities: string[];
}

export interface McpServerConfig {
  name: string;
  transport_type?: 'stdio' | 'http_stream' | 'local';
  server_path?: string;
  http_endpoint?: string;
  headers?: Record<string, string>;
  command?: string;
  args?: string[];
  roots?: RootConfig[];
  capabilities: string[];
  timeout?: number;
  routing_weight?: number;
  exclude?: string[];
  gcp_secrets?: GCPSecretConfig[];
}

export interface LLMConfig {
  llm_id: string;
  provider?: string;
  model_name?: string;
  temperature?: number;
  max_tokens?: number;
  default_system_prompt?: string;
  // Allow additional provider-specific fields
  [key: string]: any;
}

export interface AgentConfig {
  name?: string;
  mcp_servers?: string[];
  llm_config_id?: string;
  system_prompt?: string;
  config_validation_schema?: Record<string, any>;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  max_iterations?: number;
  include_history?: boolean;
  exclude_components?: string[];
  evaluation?: string;
}

export interface WorkflowConfig { // For Simple Workflows
  name: string;
  steps: string[];
  description?: string;
}

export interface CustomWorkflowConfig {
  name: string;
  module_path: string; // In Python it's Path, in JSON/TS it will be string
  class_name: string;
  description?: string;
}

export interface ProjectConfig {
  name: string;
  description?: string;
  mcp_servers: Record<string, McpServerConfig>;
  llms: Record<string, LLMConfig>;
  agents: Record<string, AgentConfig>;
  simple_workflows: Record<string, WorkflowConfig>;
  custom_workflows: Record<string, CustomWorkflowConfig>;
}

// For API responses
export interface LoadComponentsResponse {
  success: boolean;
  message: string;
  details?: any; // Could be refined if backend provides specific details structure
}

export interface ApiError {
  message: string;
  status?: number;
  details?: any;
}

// Types for Agent Execution (mirroring backend src/agents/agent_models.py)
export interface AgentOutputContentBlock {
  type: 'text' | 'tool_use' | 'tool_result' | 'final_response_data' | 'placeholder' | 'thinking_finalized' | string; // Removed 'json_stream'
  text?: string; // For type 'text'. For 'final_response_data', this could be the raw JSON string part.
  // Add other fields like id, input, name for tool_use if needed for display
  id?: string; // For tool_use or tool_result
  input?: Record<string, any>; // For tool_use
  name?: string; // For tool_use
  tool_use_id?: string; // For tool_result
  content?: AgentOutputContentBlock[] | string; // For tool_result content (can be string or list of blocks)
  is_error?: boolean; // For tool_result, indicating if it's an error result
  parsedJson?: Record<string, any>; // For 'final_response_data' type
  thinkingText?: string; // For 'final_response_data' type (though now largely superseded by 'thinking_finalized')

  // Internal frontend-only state properties for streaming management
  _originalIndex?: number; // To store the LLM's original index for a streaming block
  _finalized?: boolean;    // To mark if a block (especially text) has been fully processed by content_block_stop
  _inputFinalized?: boolean; // Specifically for tool_use blocks to mark if their input has been finalized
}

export interface AgentOutputMessage {
  role: string;
  content: AgentOutputContentBlock[];
  id?: string;
  model?: string;
  stop_reason?: string;
  stop_sequence?: string;
  usage?: Record<string, number>;
}

export interface AgentExecutionResult {
  conversation: AgentOutputMessage[];
  final_response?: AgentOutputMessage;
  tool_uses_in_final_turn?: Record<string, any>[]; // List of dicts
  error?: string;
}

export interface ExecuteCustomWorkflowRequest { // Already defined in backend, adding here for frontend use if needed
  initial_input: any;
}

export interface ExecuteCustomWorkflowResponse {
  workflow_name: string;
  status: 'completed' | 'failed';
  result?: any;
  error?: string;
}

export interface ExecuteWorkflowRequest {
  initial_user_message: string;
}

export interface ExecuteWorkflowResponse {
  workflow_name: string;
  status: 'completed' | 'failed';
  final_message?: string;
  error?: string;
}
