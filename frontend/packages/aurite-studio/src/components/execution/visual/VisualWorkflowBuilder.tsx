import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { WorkflowCanvas } from './WorkflowCanvas';
import { NodePalette } from './NodePalette';
import { WorkflowNode, WorkflowEdge, VisualWorkflow } from '@/types/execution/visual-workflow';
import { convertTextToVisual, convertVisualToText, validateVisualWorkflow } from '@/utils/workflowConverter';
import { WorkflowConfig } from '@/types/execution';
import { useAgentsWithConfigs } from '@/hooks/useAgents';
import { useWorkflowsWithConfigs } from '@/hooks/useWorkflows';
import { Button } from '@/components/ui/button';
import { AlertCircle, CheckCircle, XCircle } from 'lucide-react';

interface VisualWorkflowBuilderProps {
  workflow: WorkflowConfig;
  onWorkflowChange: (workflow: WorkflowConfig) => void;
  onConvertToText: () => void;
}

// Custom comparison function for React.memo
const arePropsEqual = (prevProps: VisualWorkflowBuilderProps, nextProps: VisualWorkflowBuilderProps) => {
  // Compare workflow properties
  if (prevProps.workflow.name !== nextProps.workflow.name) return false;
  if (prevProps.workflow.type !== nextProps.workflow.type) return false;
  if (prevProps.workflow.description !== nextProps.workflow.description) return false;
  
  // Compare steps array
  if (prevProps.workflow.steps?.length !== nextProps.workflow.steps?.length) return false;
  if (prevProps.workflow.steps && nextProps.workflow.steps) {
    for (let i = 0; i < prevProps.workflow.steps.length; i++) {
      const prevStep = prevProps.workflow.steps[i];
      const nextStep = nextProps.workflow.steps[i];
      if (typeof prevStep === 'string' && typeof nextStep === 'string') {
        if (prevStep !== nextStep) return false;
      } else if (typeof prevStep === 'object' && typeof nextStep === 'object') {
        if (prevStep.name !== nextStep.name) return false;
      } else {
        return false; // Different types
      }
    }
  }
  
  return true;
};

const VisualWorkflowBuilderComponent: React.FC<VisualWorkflowBuilderProps> = ({
  workflow,
  onWorkflowChange,
  onConvertToText
}) => {
  // State
  const [visualWorkflow, setVisualWorkflow] = useState<VisualWorkflow | null>(null);
  const [validation, setValidation] = useState<{ isValid: boolean; errors: string[]; warnings: string[] }>({
    isValid: true,
    errors: [],
    warnings: []
  });
  const [error, setError] = useState<string | null>(null);

  // API Hooks
  const { data: agents = [] } = useAgentsWithConfigs();
  const { data: workflows = [] } = useWorkflowsWithConfigs();

  // Memoize the workflow to prevent unnecessary re-renders
  const memoizedWorkflow = useMemo(() => {
    if (!workflow) return null;
    
    return {
      name: workflow.name,
      type: workflow.type,
      description: workflow.description,
      steps: workflow.steps
    };
  }, [workflow?.name, workflow?.type, workflow?.description, workflow?.steps]);

  // Initialize visual workflow from text workflow
  useEffect(() => {
    try {
      if (memoizedWorkflow) {
        console.log('Converting workflow to visual:', memoizedWorkflow);
        console.log('Workflow type:', typeof memoizedWorkflow);
        console.log('Workflow keys:', Object.keys(memoizedWorkflow));
        
        const visual = convertTextToVisual(memoizedWorkflow);
        console.log('Visual workflow created:', visual);
        setVisualWorkflow(visual);
        validateWorkflow(visual);
        setError(null);
      }
    } catch (err) {
      console.error('Error converting workflow to visual:', err);
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    }
  }, [memoizedWorkflow]);

  // Validate workflow whenever it changes
  const validateWorkflow = useCallback((workflow: VisualWorkflow) => {
    try {
      const result = validateVisualWorkflow(workflow);
      setValidation(result);
    } catch (err) {
      console.error('Error validating workflow:', err);
      setValidation({
        isValid: false,
        errors: ['Validation error occurred'],
        warnings: []
      });
    }
  }, []);

  // Handle workflow changes
  const handleWorkflowChange = useCallback((nodes: WorkflowNode[], edges: WorkflowEdge[]) => {
    if (!visualWorkflow) return;

    try {
      const updatedWorkflow: VisualWorkflow = {
        ...visualWorkflow,
        nodes,
        edges
      };

      setVisualWorkflow(updatedWorkflow);
      validateWorkflow(updatedWorkflow);

      // Convert back to text format and notify parent
      const textWorkflow = convertVisualToText(updatedWorkflow);
      onWorkflowChange(textWorkflow);
    } catch (err) {
      console.error('Error handling workflow change:', err);
    }
  }, [visualWorkflow, validateWorkflow, onWorkflowChange]);

  // Handle node drag from palette
  const handleNodeDrag = useCallback((nodeType: string, nodeData: any) => {
    console.log('Node dragged:', nodeType, nodeData);
  }, []);

  // Convert to text mode
  const handleConvertToText = useCallback(() => {
    onConvertToText();
  }, [onConvertToText]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-red-600">
          Error loading visual workflow: {error}
        </div>
      </div>
    );
  }

  if (!visualWorkflow) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading visual workflow...</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div>
          <h3 className="font-medium text-foreground">Visual Workflow Builder</h3>
          <p className="text-sm text-muted-foreground">
            Drag and drop components to build your workflow
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleConvertToText}
          >
            Switch to Text Mode
          </Button>
        </div>
      </div>

      {/* Validation Messages - Simplified */}
      {validation.errors.length > 0 && (
        <div className="mx-4 mt-4 p-4 border border-red-200 bg-red-50 rounded-lg">
          <div className="flex items-center gap-2 text-red-800">
            <XCircle className="h-4 w-4" />
            <span className="font-medium">Workflow has errors:</span>
          </div>
          <ul className="list-disc list-inside space-y-1 mt-2">
            {validation.errors.map((error, index) => (
              <li key={index} className="text-sm text-red-700">{error}</li>
            ))}
          </ul>
        </div>
      )}

      {validation.warnings.length > 0 && (
        <div className="mx-4 mt-4 p-4 border border-yellow-200 bg-yellow-50 rounded-lg">
          <div className="flex items-center gap-2 text-yellow-800">
            <AlertCircle className="h-4 w-4" />
            <span className="font-medium">Workflow warnings:</span>
          </div>
          <ul className="list-disc list-inside space-y-1 mt-2">
            {validation.warnings.map((warning, index) => (
              <li key={index} className="text-sm text-yellow-700">{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {validation.isValid && validation.errors.length === 0 && (
        <div className="mx-4 mt-4 p-4 border border-green-200 bg-green-50 rounded-lg">
          <div className="flex items-center gap-2 text-green-800">
            <CheckCircle className="h-4 w-4" />
            <span>Workflow is valid and ready to execute</span>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Node Palette */}
        <div className="w-64 border-r border-border overflow-y-auto">
          <div className="p-4">
            <NodePalette
              availableAgents={agents}
              availableWorkflows={workflows}
              onNodeDrag={handleNodeDrag}
            />
          </div>
        </div>

        {/* Right Panel - Workflow Canvas */}
        <div className="flex-1">
          <WorkflowCanvas
            nodes={visualWorkflow.nodes}
            edges={visualWorkflow.edges}
            onNodesChange={() => {}} // Handled by WorkflowCanvas internally
            onEdgesChange={() => {}} // Handled by WorkflowCanvas internally
            onConnect={() => {}} // Handled by WorkflowCanvas internally
            onWorkflowChange={handleWorkflowChange}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border bg-muted/50">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <div>
            {visualWorkflow.nodes.length} nodes • {visualWorkflow.edges.length} connections
          </div>
          <div className="flex items-center gap-4">
            <span>Status: {validation.isValid ? 'Valid' : 'Invalid'}</span>
            {validation.errors.length > 0 && (
              <span className="text-red-600">{validation.errors.length} errors</span>
            )}
            {validation.warnings.length > 0 && (
              <span className="text-yellow-600">{validation.warnings.length} warnings</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Export the memoized component
export const VisualWorkflowBuilder = React.memo(VisualWorkflowBuilderComponent, arePropsEqual); 