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

export interface ClientConfig {
  client_id: string;
  server_path: string; // In Python it's Path, in JSON/TS it will be string
  roots: RootConfig[];
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
  client_ids?: string[];
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
  clients: Record<string, ClientConfig>;
  llm_configs: Record<string, LLMConfig>;
  agent_configs: Record<string, AgentConfig>;
  simple_workflow_configs: Record<string, WorkflowConfig>;
  custom_workflow_configs: Record<string, CustomWorkflowConfig>;
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
  type: string;
  text?: string | Record<string, any>; // Text can be a string or a JSON object from schema
  // Add other fields like id, input, name for tool_use if needed for display
  id?: string; // For tool_use or tool_result
  input?: Record<string, any>; // For tool_use
  name?: string; // For tool_use
  tool_use_id?: string; // For tool_result
  content?: AgentOutputContentBlock[]; // For nested content in tool_result
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
