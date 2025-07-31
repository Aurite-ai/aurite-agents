// Core Execution Types for Simple Agent Execution UX

// Agent Configuration (from existing API alignment)
export interface AgentConfig {
  type: 'agent';
  name: string;
  description?: string;
  llm_config_id?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  system_prompt?: string;
  max_iterations?: number;
  include_history?: boolean;
  auto?: boolean;
  mcp_servers?: string[];
  exclude_components?: string[];
  _source_file?: string;
  _context_path?: string;
  _context_level?: string;
  _project_name?: string;
  _workspace_name?: string;
}

// Execution Request
export interface ExecutionRequest {
  user_message: string;
  session_id?: string;
  system_prompt?: string;
  stream?: boolean;
  debug_mode?: boolean;
  context?: Record<string, any>;
}

// Execution State
export interface ExecutionState {
  status: 'idle' | 'starting' | 'executing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  currentStep?: string;
  startTime?: Date;
  endTime?: Date;
  result?: ExecutionResult;
  error?: string;
  toolCalls: ToolCall[];
  streamEvents: StreamEvent[];
  currentResponse: string;
  userMessage?: string;
  debugMode?: boolean;
}

// Execution Result
export interface ExecutionResult {
  execution_id: string;
  session_id: string;
  status: 'completed' | 'failed' | 'cancelled';
  final_response?: {
    role: string;
    content: Array<{ type: string; text: string }>;
  };
  tool_calls?: ToolCall[];
  metadata: ExecutionMetadata;
  error?: string;
  history: ConversationMessage[];
}

// Execution Metadata
export interface ExecutionMetadata {
  start_time: string;
  end_time?: string;
  duration_ms?: number;
  token_usage?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  cost_estimate?: number;
  model_used?: string;
  tool_count?: number;
}

// Conversation Message
export interface ConversationMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

// Tool Call
export interface ToolCall {
  id: string;
  name: string;
  parameters: Record<string, any>;
  status: 'queued' | 'executing' | 'completed' | 'failed';
  start_time?: Date;
  end_time?: Date;
  duration_ms?: number;
  result?: any;
  error?: string;
}

// Stream Event
export interface StreamEvent {
  type: 'llm_response_start' | 'llm_response' | 'llm_response_stop' | 
        'tool_call' | 'tool_output' | 'error' | 'complete';
  data: any;
  timestamp: Date;
  execution_id: string;
}

// Session Information
export interface SessionInfo {
  id: string;
  name: string;
  agent_name: string;
  message_count: number;
  last_activity: Date;
  created_at: Date;
  status: 'active' | 'archived';
}

// Component Props Interfaces

export interface UnifiedExecutionInterfaceProps {
  agent: AgentConfig | null;
  isOpen: boolean;
  onClose: () => void;
}

export interface InputPanelProps {
  agent: AgentConfig;
  onExecute: (request: ExecutionRequest) => void;
  disabled?: boolean;
}

export interface ExecutionPanelProps {
  agent: AgentConfig;
  executionState: ExecutionState;
  onStateChange: (state: ExecutionState) => void;
}

export interface StreamingHandlerProps {
  agentName: string;
  request: ExecutionRequest;
  onEvent: (event: StreamEvent) => void;
  onComplete: (result: ExecutionResult) => void;
  onError: (error: string) => void;
}

export interface SimulatedDisplayProps {
  result: ExecutionResult;
  onProgress: (progress: number) => void;
  onComplete: () => void;
  speed?: 'slow' | 'normal' | 'fast';
}

export interface SessionSelectorProps {
  agentName: string;
  selectedSessionId?: string | null;
  onSessionSelect: (sessionId: string | null) => void;
  onSessionCreate: (sessionName: string) => void;
  disabled?: boolean;
}

export interface ToolCallIndicatorProps {
  toolCall: ToolCall;
  onRetry?: (toolCall: ToolCall) => void;
  onViewDetails?: (toolCall: ToolCall) => void;
  showDetails?: boolean;
}

export interface ResponseDisplayProps {
  content: string;
  isStreaming?: boolean;
  onCopy?: () => void;
  onExport?: (format: 'pdf' | 'html' | 'markdown') => void;
}

export interface ExecutionProgressProps {
  progress: number;
  currentStep?: string;
  startTime?: Date;
  estimatedDuration?: number;
}

export interface ContinueConversationProps {
  sessionId: string;
  agentName: string;
  onSendMessage: (message: string) => void;
  onRegenerateResponse?: () => void;
  isLoading?: boolean;
}

// Hook Return Types

export interface UseAgentExecutionReturn {
  executeAgent: (request: ExecutionRequest) => Promise<void>;
  cancelExecution: () => void;
  isExecuting: boolean;
}

export interface UseExecutionSessionsReturn {
  sessions: SessionInfo[];
  isLoading: boolean;
  error: string | null;
  createSession: (name: string) => Promise<string>;
  deleteSession: (sessionId: string) => Promise<void>;
  getSessionHistory: (sessionId: string) => Promise<ConversationMessage[]>;
}

// Workflow-Specific Types (extending agent execution patterns)

// Workflow Configuration (from existing API alignment)
export interface WorkflowConfig {
  type: 'linear_workflow' | 'custom_workflow';
  name: string;
  description?: string;
  steps?: (string | { name: string; type?: string })[];
  module_path?: string; // For custom workflows
  class_name?: string; // For custom workflows
  _source_file?: string;
  _context_path?: string;
  _context_level?: string;
  _project_name?: string;
  _workspace_name?: string;
}

// Workflow Execution Request
export interface WorkflowExecutionRequest {
  initial_input: string;
  session_id?: string;
  workflow_parameters?: Record<string, any>;
  debug_mode?: boolean;
}

// Workflow Execution State
export interface WorkflowExecutionState {
  status: 'idle' | 'starting' | 'executing' | 'completed' | 'failed' | 'cancelled';
  currentStepIndex: number;
  completedSteps: StepResult[];
  totalSteps: number;
  progress: number;
  currentStepProgress?: number;
  startTime?: Date;
  endTime?: Date;
  result?: WorkflowExecutionResult;
  error?: string;
  initialInput?: string;
}

// Workflow Execution Result
export interface WorkflowExecutionResult {
  execution_id: string;
  session_id: string;
  workflow_name: string;
  status: 'completed' | 'failed' | 'cancelled';
  final_message?: string;
  error?: string | null;
  step_results: StepResult[];
  metadata: WorkflowExecutionMetadata;
  history: ConversationMessage[];
}

// Step Result
export interface StepResult {
  stepIndex: number;
  stepName: string;
  status: 'completed' | 'failed' | 'skipped';
  startTime: Date;
  endTime?: Date;
  duration_ms?: number;
  input?: any;
  result?: any;
  error?: string;
  tool_calls?: ToolCall[];
}

// Workflow Execution Metadata
export interface WorkflowExecutionMetadata {
  start_time: string;
  end_time?: string;
  duration_ms?: number;
  step_count: number;
  completed_steps: number;
  failed_steps: number;
  token_usage?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
}

// Workflow Session Information
export interface WorkflowSessionInfo {
  id: string;
  name: string;
  workflow_name: string;
  step_count: number;
  last_activity: Date;
  created_at: Date;
  status: 'active' | 'archived';
  current_step?: number;
}

// Workflow Component Props Interfaces

export interface UnifiedWorkflowExecutionInterfaceProps {
  workflow: WorkflowConfig | null;
  isOpen: boolean;
  onClose: () => void;
}

export interface WorkflowInputPanelProps {
  workflow: WorkflowConfig;
  onExecute: (request: WorkflowExecutionRequest) => void;
  disabled?: boolean;
}

export interface WorkflowExecutionPanelProps {
  workflow: WorkflowConfig;
  executionState: WorkflowExecutionState;
  onStateChange: (state: WorkflowExecutionState) => void;
}

export interface WorkflowProgressProps {
  steps: (string | { name: string; type?: string })[];
  currentStepIndex: number;
  completedSteps: StepResult[];
  currentStepProgress?: number;
  startTime?: Date;
}

export interface StepExecutionDisplayProps {
  steps: (string | { name: string; type?: string })[];
  currentStepIndex: number;
  completedSteps: StepResult[];
  currentStepProgress?: number;
}

export interface WorkflowSessionSelectorProps {
  workflowName: string;
  selectedSessionId?: string | null;
  onSessionSelect: (sessionId: string | null) => void;
  onSessionCreate: (sessionName: string) => void;
  disabled?: boolean;
}

export interface ContinueWorkflowConversationProps {
  sessionId: string;
  workflowName: string;
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

// Workflow Hook Return Types

export interface UseWorkflowExecutionReturn {
  executeWorkflow: (request: WorkflowExecutionRequest) => Promise<void>;
  cancelExecution: () => void;
  isExecuting: boolean;
  executionState: WorkflowExecutionState;
}

export interface UseWorkflowExecutionSessionsReturn {
  sessions: WorkflowSessionInfo[];
  isLoading: boolean;
  error: string | null;
  createSession: (name: string) => Promise<string>;
  deleteSession: (sessionId: string) => Promise<void>;
}

// Utility Types

export type ExecutionStatus = ExecutionState['status'];
export type ToolCallStatus = ToolCall['status'];
export type StreamEventType = StreamEvent['type'];
export type WorkflowExecutionStatus = WorkflowExecutionState['status'];
export type StepStatus = StepResult['status'];
