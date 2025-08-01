import { Node, Edge } from '@xyflow/react';

// Visual Workflow Types
export interface VisualWorkflow {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  metadata: {
    name: string;
    description?: string;
    type: 'simple_workflow' | 'custom_workflow';
  };
}

export interface WorkflowNode extends Node {
  type: 'agent' | 'workflow' | 'input' | 'output';
  data: {
    name: string;
    description?: string;
    config?: any;
    agentId?: string;
    workflowId?: string;
    stepIndex?: number;
  };
}

export interface WorkflowEdge extends Edge {
  type: 'default' | 'conditional';
  data?: {
    condition?: string;
    label?: string;
    stepIndex?: number;
  };
}

// Node Types for React Flow
export const NODE_TYPES = {
  AGENT: 'agent',
  WORKFLOW: 'workflow',
  INPUT: 'input',
  OUTPUT: 'output'
} as const;

export const EDGE_TYPES = {
  DEFAULT: 'default',
  CONDITIONAL: 'conditional'
} as const;

// Workflow Mode Types
export type WorkflowMode = 'text' | 'visual';

// Conversion Functions Types
export interface WorkflowConverter {
  textToVisual: (workflowConfig: any) => VisualWorkflow;
  visualToText: (visualWorkflow: VisualWorkflow) => any;
}

// Validation Types
export interface WorkflowValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

// Node Palette Types
export interface PaletteItem {
  id: string;
  name: string;
  type: 'agent' | 'workflow';
  description?: string;
  icon?: string;
  config?: any;
}

// Properties Panel Types
export interface NodeProperties {
  id: string;
  name: string;
  description?: string;
  config?: any;
  agentId?: string;
  workflowId?: string;
} 