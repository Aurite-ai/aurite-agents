import { VisualWorkflow, WorkflowNode, WorkflowEdge } from '@/types/execution/visual-workflow';
import { WorkflowConfig } from '@/types/execution';

/**
 * Convert text-based workflow configuration to visual workflow format
 */
export const convertTextToVisual = (workflowConfig: WorkflowConfig): VisualWorkflow => {
  const nodes: WorkflowNode[] = [];
  const edges: WorkflowEdge[] = [];
  
  // Add input node
  const inputNode: WorkflowNode = {
    id: 'input',
    type: 'input',
    position: { x: 50, y: 100 },
    data: {
      name: 'Input',
      description: 'Workflow input',
      stepIndex: 0
    }
  };
  nodes.push(inputNode);
  
  // Convert steps to nodes
  workflowConfig.steps?.forEach((step, index) => {
    const nodeId = `step-${index}`;
    const stepName = typeof step === 'string' ? step : step.name;
    
    const node: WorkflowNode = {
      id: nodeId,
      type: 'agent',
      position: { x: 250 + (index * 200), y: 100 },
      data: {
        name: stepName,
        description: `Step ${index + 1}: ${stepName}`,
        agentId: stepName,
        stepIndex: index + 1
      }
    };
    nodes.push(node);
    
    // Create edges between steps
    if (index === 0) {
      // Connect input to first step
      edges.push({
        id: `edge-input-${index}`,
        source: 'input',
        target: nodeId,
        type: 'default',
        data: { stepIndex: index }
      });
    } else {
      // Connect previous step to current step
      edges.push({
        id: `edge-${index-1}-${index}`,
        source: `step-${index-1}`,
        target: nodeId,
        type: 'default',
        data: { stepIndex: index }
      });
    }
  });
  
  // Add output node if there are steps
  if (workflowConfig.steps && workflowConfig.steps.length > 0) {
    const lastStepIndex = workflowConfig.steps.length - 1;
    const outputNode: WorkflowNode = {
      id: 'output',
      type: 'output',
      position: { x: 250 + ((lastStepIndex + 1) * 200), y: 100 },
      data: {
        name: 'Output',
        description: 'Workflow output',
        stepIndex: lastStepIndex + 2
      }
    };
    nodes.push(outputNode);
    
    // Connect last step to output
    edges.push({
      id: `edge-${lastStepIndex}-output`,
      source: `step-${lastStepIndex}`,
      target: 'output',
      type: 'default',
      data: { stepIndex: lastStepIndex + 1 }
    });
  }
  
  return {
    nodes,
    edges,
    metadata: {
      name: workflowConfig.name,
      description: workflowConfig.description,
      type: workflowConfig.type
    }
  };
};

/**
 * Convert visual workflow format to text-based workflow configuration
 */
export const convertVisualToText = (visualWorkflow: VisualWorkflow): WorkflowConfig => {
  const steps: string[] = [];
  
  // Sort nodes by stepIndex to maintain order
  const agentNodes = visualWorkflow.nodes
    .filter(node => node.type === 'agent')
    .sort((a, b) => (a.data.stepIndex || 0) - (b.data.stepIndex || 0));
  
  agentNodes.forEach(node => {
    steps.push(node.data.name);
  });
  
  return {
    name: visualWorkflow.metadata.name,
    description: visualWorkflow.metadata.description,
    type: visualWorkflow.metadata.type,
    steps
  };
};

/**
 * Validate visual workflow structure
 */
export const validateVisualWorkflow = (visualWorkflow: VisualWorkflow): {
  isValid: boolean;
  errors: string[];
  warnings: string[];
} => {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  // Check if workflow has nodes
  if (visualWorkflow.nodes.length === 0) {
    errors.push('Workflow must have at least one node');
  }
  
  // Check if workflow has input and output nodes
  const hasInput = visualWorkflow.nodes.some(node => node.type === 'input');
  const hasOutput = visualWorkflow.nodes.some(node => node.type === 'output');
  
  if (!hasInput) {
    warnings.push('Workflow should have an input node');
  }
  
  if (!hasOutput) {
    warnings.push('Workflow should have an output node');
  }
  
  // Check if all agent nodes are connected
  const agentNodes = visualWorkflow.nodes.filter(node => node.type === 'agent');
  const connectedNodes = new Set<string>();
  
  visualWorkflow.edges.forEach(edge => {
    connectedNodes.add(edge.source);
    connectedNodes.add(edge.target);
  });
  
  agentNodes.forEach(node => {
    if (!connectedNodes.has(node.id)) {
      warnings.push(`Agent node "${node.data.name}" is not connected`);
    }
  });
  
  // Check for cycles (basic check)
  const visited = new Set<string>();
  const recStack = new Set<string>();
  
  const hasCycle = (nodeId: string): boolean => {
    if (recStack.has(nodeId)) return true;
    if (visited.has(nodeId)) return false;
    
    visited.add(nodeId);
    recStack.add(nodeId);
    
    const outgoingEdges = visualWorkflow.edges.filter(edge => edge.source === nodeId);
    for (const edge of outgoingEdges) {
      if (hasCycle(edge.target)) return true;
    }
    
    recStack.delete(nodeId);
    return false;
  };
  
  for (const node of visualWorkflow.nodes) {
    if (hasCycle(node.id)) {
      errors.push('Workflow contains cycles which are not supported');
      break;
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

/**
 * Generate a unique node ID
 */
export const generateNodeId = (prefix: string = 'node'): string => {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Get the next available step index
 */
export const getNextStepIndex = (nodes: WorkflowNode[]): number => {
  const stepIndices = nodes
    .map(node => node.data.stepIndex || 0)
    .filter(index => index > 0);
  
  return stepIndices.length > 0 ? Math.max(...stepIndices) + 1 : 1;
}; 