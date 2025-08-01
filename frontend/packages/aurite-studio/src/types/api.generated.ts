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
  // Core Identity
  type?: 'agent';
  name: string;
  description?: string;

  // LLM Configuration
  llm_config_id?: string;
  
  // LLM Override Parameters (optional, overrides llm_config_id settings)
  model?: string;
  temperature?: number;
  max_tokens?: number;

  // Behavior Control
  system_prompt?: string;
  max_iterations?: number;
  include_history?: boolean;
  auto?: boolean;

  // Capability Management
  mcp_servers?: string[];
  exclude_components?: string[];

  // Framework Metadata (read-only, added by system)
  _source_file?: string;
  _context_path?: string;
  _context_level?: string;
  _project_name?: string;
  _workspace_name?: string;
}

export interface AgentExecutionResult {
  final_response?: {
    role: string;
    content: any[];
  };
  error?: string | null;
  history?: any[];
  session_id?: string;
}

// Workflow types
export interface WorkflowConfig {
  name: string;
  type: "simple_workflow";
  steps: string[];
  description?: string;
}

// Runtime information for UI display
export interface WorkflowDisplayModel {
  name: string;
  description?: string;
  stepCount: number;
  stepPreview: string; // "Agent A → Agent B → Agent C"
  type: 'simple_workflow' | 'custom_workflow';
  status: 'active' | 'inactive' | 'error';
  configFile?: string;
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
  execution_id?: string;
  session_id?: string;
  step_results?: any[];
  history?: any[];
}

export interface ExecuteCustomWorkflowResponse {
  workflow_name: string;
  status: 'completed' | 'failed';
  result?: any;
  error?: string | null;
}

// Root configuration interface
export interface RootConfig {
  uri: string;
  name: string;
  capabilities: string[];
}

// Legacy client config (deprecated - use MCPServerConfig instead)
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

// Complete MCP Server Configuration Interface (API-compliant)
export interface MCPServerConfig {
  // Required fields
  name: string;
  type: "mcp_server";
  capabilities: string[];

  // Optional common fields
  description?: string;
  transport_type?: "stdio" | "http_stream" | "local";
  timeout?: number;
  registration_timeout?: number;
  routing_weight?: number;
  exclude?: string[];
  roots?: RootConfig[];

  // Stdio transport fields
  server_path?: string;

  // HTTP stream transport fields
  http_endpoint?: string;
  headers?: Record<string, string>;

  // Local transport fields
  command?: string;
  args?: string[];
}

// Transport-specific interfaces for type safety
export interface MCPServerStdioConfig extends Omit<MCPServerConfig, 'transport_type'> {
  transport_type: "stdio";
  server_path: string;
  // Explicitly exclude other transport fields
  http_endpoint?: never;
  headers?: never;
  command?: never;
  args?: never;
}

export interface MCPServerHttpConfig extends Omit<MCPServerConfig, 'transport_type'> {
  transport_type: "http_stream";
  http_endpoint: string;
  headers?: Record<string, string>;
  // Explicitly exclude other transport fields
  server_path?: never;
  command?: never;
  args?: never;
}

export interface MCPServerLocalConfig extends Omit<MCPServerConfig, 'transport_type'> {
  transport_type: "local";
  command: string;
  args?: string[];
  // Explicitly exclude other transport fields
  server_path?: never;
  http_endpoint?: never;
  headers?: never;
}

// Union type for type-safe transport handling
export type MCPServerTransportConfig = 
  | MCPServerStdioConfig 
  | MCPServerHttpConfig 
  | MCPServerLocalConfig;

// Form fields interface for React components
export interface MCPServerFormFields {
  // Basic fields
  name: string;
  description: string;
  capabilities: string[];
  
  // Transport selection
  transport_type: "stdio" | "http_stream" | "local";
  
  // Stdio fields
  server_path: string;
  
  // HTTP fields
  http_endpoint: string;
  headers: Array<{key: string; value: string}>;
  
  // Local fields
  command: string;
  args: string[];
  
  // Advanced fields
  timeout: number;
  registration_timeout: number;
  routing_weight: number;
  exclude: string[];
}

// LLM types
export interface LLMConfig {
  name: string;
  type: 'llm';
  provider: string;
  model: string;
  description?: string;
  temperature?: number;
  max_tokens?: number;
  default_system_prompt?: string;
  api_base?: string;
  api_key?: string;
  api_version?: string;
  api_key_env_var?: string;
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
  initial_input: string;
  session_id?: string;
}

export interface ExecuteCustomWorkflowRequest {
  initial_input: any;
  session_id?: string;
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
