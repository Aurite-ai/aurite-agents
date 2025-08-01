import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { ReadOnlyWorkflowCanvas } from './ReadOnlyWorkflowCanvas';
import { WorkflowNode, WorkflowEdge, VisualWorkflow } from '@/types/execution/visual-workflow';
import { convertTextToVisual, validateVisualWorkflow } from '@/utils/workflowConverter';
import { WorkflowConfig } from '@/types/execution';
import { Button } from '@/components/ui/button';
import { AlertCircle, CheckCircle, XCircle, Play, Settings } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface VisualWorkflowRunnerProps {
  workflow: WorkflowConfig;
  onExecute: (input: string, sessionId?: string) => void;
  onConvertToText: () => void;
  isExecuting?: boolean;
}

// Custom comparison function for React.memo
const arePropsEqual = (prevProps: VisualWorkflowRunnerProps, nextProps: VisualWorkflowRunnerProps) => {
  // Compare workflow properties
  if (prevProps.workflow.name !== nextProps.workflow.name) return false;
  if (prevProps.workflow.type !== nextProps.workflow.type) return false;
  if (prevProps.workflow.description !== nextProps.workflow.description) return false;
  if (prevProps.isExecuting !== nextProps.isExecuting) return false;
  
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

const VisualWorkflowRunnerComponent: React.FC<VisualWorkflowRunnerProps> = ({
  workflow,
  onExecute,
  onConvertToText,
  isExecuting = false
}) => {
  // State
  const [visualWorkflow, setVisualWorkflow] = useState<VisualWorkflow | null>(null);
  const [validation, setValidation] = useState<{ isValid: boolean; errors: string[]; warnings: string[] }>({
    isValid: true,
    errors: [],
    warnings: []
  });
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState<string>('');
  const [sessionId, setSessionId] = useState<string>('new');
  const [showAdvancedOptions, setShowAdvancedOptions] = useState<boolean>(false);

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

  // Handle execution
  const handleExecute = useCallback(() => {
    if (!validation.isValid) {
      return;
    }
    
    const finalSessionId = sessionId === 'new' ? undefined : sessionId;
    onExecute(input, finalSessionId);
  }, [input, sessionId, validation.isValid, onExecute]);

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

  const stepCount = visualWorkflow.nodes.filter(node => 
    node.type === 'agent' || node.type === 'workflow'
  ).length;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div>
          <h3 className="font-medium text-foreground">Execute Workflow: {workflow.name}</h3>
          <p className="text-sm text-muted-foreground">
            {stepCount} steps will be executed
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onConvertToText}
          >
            Switch to Text Mode
          </Button>
        </div>
      </div>

      {/* Validation Messages */}
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
        {/* Left Panel - Execution Controls */}
        <div className="w-80 border-r border-border overflow-y-auto">
          <div className="p-4 space-y-6">
            {/* Workflow Information */}
            <div>
              <h4 className="font-medium text-foreground mb-2">Workflow Information</h4>
              <div className="space-y-2 text-sm">
                <div><span className="font-medium">Name:</span> {workflow.name}</div>
                <div><span className="font-medium">Steps:</span> {stepCount}</div>
                {workflow.description && (
                  <div><span className="font-medium">Description:</span> {workflow.description}</div>
                )}
              </div>
            </div>

            {/* Workflow Steps */}
            <div>
              <h4 className="font-medium text-foreground mb-2">Workflow Steps</h4>
              <div className="space-y-1">
                {visualWorkflow.nodes
                  .filter(node => node.type === 'agent' || node.type === 'workflow')
                  .sort((a, b) => (a.data.stepIndex || 0) - (b.data.stepIndex || 0))
                  .map((node, index) => (
                    <div key={node.id} className="flex items-center gap-2 text-sm">
                      <span className="font-medium">{index + 1}:</span>
                      <span>{node.data.name}</span>
                    </div>
                  ))}
              </div>
            </div>

            {/* Initial Input */}
            <div>
              <Label htmlFor="workflow-input" className="font-medium text-foreground">
                Initial Input*
              </Label>
              <Textarea
                id="workflow-input"
                placeholder="Enter the initial input for this workflow..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                className="mt-2"
                rows={4}
              />
              <div className="text-xs text-muted-foreground mt-1 text-right">
                {input.length} characters
              </div>
            </div>

            {/* Session */}
            <div>
              <Label htmlFor="session-select" className="font-medium text-foreground">
                Session
              </Label>
              <Select value={sessionId} onValueChange={setSessionId}>
                <SelectTrigger className="mt-2">
                  <SelectValue placeholder="Select session" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="new">+ New conversation</SelectItem>
                  {/* Add existing sessions here if available */}
                </SelectContent>
              </Select>
            </div>

            {/* Advanced Options */}
            <div>
              <button
                onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
                className="flex items-center justify-between w-full text-left font-medium text-foreground"
              >
                Advanced Options
                <Settings className={`h-4 w-4 transition-transform ${showAdvancedOptions ? 'rotate-90' : ''}`} />
              </button>
              {showAdvancedOptions && (
                <div className="mt-2 space-y-2 text-sm text-muted-foreground">
                  <div>• Execution timeout: 30s</div>
                  <div>• Max retries: 3</div>
                  <div>• Debug mode: disabled</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Panel - Workflow Canvas */}
        <div className="flex-1">
          <ReadOnlyWorkflowCanvas
            nodes={visualWorkflow.nodes}
            edges={visualWorkflow.edges}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border bg-muted/50">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            {visualWorkflow.nodes.length} nodes • {visualWorkflow.edges.length} connections
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              Status: {validation.isValid ? 'Valid' : 'Invalid'}
            </span>
            <Button
              onClick={handleExecute}
              disabled={!validation.isValid || isExecuting || !input.trim()}
              className="bg-primary hover:bg-primary/90"
            >
              <Play className="h-4 w-4 mr-2" />
              {isExecuting ? 'Executing...' : 'Execute Workflow'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Export the memoized component
export const VisualWorkflowRunner = React.memo(VisualWorkflowRunnerComponent, arePropsEqual); 