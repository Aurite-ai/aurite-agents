// Generated TypeScript types from OpenAPI specification

// Error response
export interface ErrorResponse {
  detail: string;
  status: number;
}

// Project types
export interface ProjectConfig {
  name: string;
  description?: string;
  mcp_servers?: Record<string, any>;
  agents?: Record<string, any>;
  llms?: Record<string, any>;
  simple_workflows?: Record<string, any>;
  custom_workflows?: Record<string, any>;
}

export interface LoadComponentsResponse {
  status: string;
  message: string;
  loaded_components: {
    agents: string[];
    clients: string[];
    workflows: string[];
  };
}

// Agent types
export interface AgentConfig {
  name: string;
  mcp_servers?: string[];
  system_prompt?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  max_iterations?: number;
  include_history?: boolean;
  exclude_components?: string[];
}

export interface AgentExecutionResult {
  final_response?: {
    role: string;
    content: any[];
  };
  error?: string | null;
  history?: any[];
}

// Workflow types
export interface WorkflowConfig {
  name: string;
  steps: string[];
  description?: string;
}

export interface CustomWorkflowConfig {
  name: string;
  class_name: string;
  module_path: string;
  description?: string;
}

export interface ExecuteWorkflowResponse {
  workflow_name: string;
  status: 'completed' | 'failed';
  final_message?: string;
  error?: string | null;
}

export interface ExecuteCustomWorkflowResponse {
  workflow_name: string;
  status: 'completed' | 'failed';
  result?: any;
  error?: string | null;
}

// Client types
export interface ClientConfig {
  name: string;
  server_path?: string;
  roots?: string[];
  capabilities?: ('tools' | 'prompts' | 'resources')[];
  timeout?: number;
  routing_weight?: number;
  exclude?: string[];
  gcp_secrets?: Record<string, any>;
}

// LLM types
export interface LLMConfig {
  llm_id: string;
  provider: string;
  model: string;
  api_key_env_var?: string;
  default_system_prompt?: string;
  max_tokens?: number;
  temperature?: number;
}

// Request types
export interface CreateProjectRequest {
  filename: string;
  project_name: string;
  project_description?: string;
}

export interface UpdateProjectRequest {
  content: any;
}

export interface LoadComponentsRequest {
  project_config_path: string;
}

export interface ExecuteAgentRequest {
  user_message: string;
  system_prompt?: string;
}

export interface ExecuteWorkflowRequest {
  initial_user_message: string;
}

export interface ExecuteCustomWorkflowRequest {
  initial_input: any;
}

export interface CreateConfigRequest {
  content: any;
}

// Response types
export interface HealthResponse {
  status: string;
}

export interface StatusResponse {
  status: string;
  manager_status: string;
}

export interface SuccessResponse {
  status: string;
  message?: string;
  [key: string]: any;
}

export interface DeleteResponse {
  status: string;
  filename: string;
  message: string;
}

// Component types
export type ComponentType = 'agents' | 'clients' | 'llms' | 'simple-workflows' | 'custom-workflows';
export type ProjectComponentType = 'agents' | 'simple_workflows' | 'custom_workflows' | 'clients' | 'llms';
