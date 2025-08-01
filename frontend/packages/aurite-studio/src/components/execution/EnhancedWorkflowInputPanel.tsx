import React, { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Loader2, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { WorkflowInputPanelProps, WorkflowExecutionRequest, WorkflowConfig } from '@/types/execution';
import { WorkflowMode } from '@/types/execution/visual-workflow';
import { WorkflowSessionSelector } from './WorkflowSessionSelector';
import { WorkflowModeToggle } from './WorkflowModeToggle';
import { VisualWorkflowBuilder } from './visual/VisualWorkflowBuilder';
import { VisualWorkflowRunner } from './visual/VisualWorkflowRunner';

interface EnhancedWorkflowInputPanelProps extends WorkflowInputPanelProps {
  mode: WorkflowMode;
  onModeChange: (mode: WorkflowMode) => void;
  onWorkflowChange?: (workflow: WorkflowConfig) => void;
}

// Custom comparison function for React.memo
const areEnhancedWorkflowInputPanelPropsEqual = (
  prevProps: EnhancedWorkflowInputPanelProps, 
  nextProps: EnhancedWorkflowInputPanelProps
) => {
  // Compare workflow properties
  if (prevProps.workflow.name !== nextProps.workflow.name) return false;
  if (prevProps.workflow.type !== nextProps.workflow.type) return false;
  if (prevProps.workflow.description !== nextProps.workflow.description) return false;
  if (prevProps.disabled !== nextProps.disabled) return false;
  if (prevProps.mode !== nextProps.mode) return false;
  
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

const EnhancedWorkflowInputPanelComponent: React.FC<EnhancedWorkflowInputPanelProps> = ({
  workflow,
  onExecute,
  disabled = false,
  mode,
  onModeChange,
  onWorkflowChange
}) => {
  const [message, setMessage] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [debugMode, setDebugMode] = useState(false);

  // Memoize the workflow to ensure it's stable
  const memoizedWorkflow = useMemo(() => workflow, [workflow]);

  const handleSessionCreate = useCallback((sessionName: string) => {
    // For now, we'll just generate a mock session ID
    // In the future, this would call an API to create the session
    const newSessionId = `workflow-session-${Date.now()}`;
    setSessionId(newSessionId);
    console.log(`Created new workflow session: ${sessionName} (${newSessionId})`);
  }, []);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || disabled) return;

    const request: WorkflowExecutionRequest = {
      initial_input: message.trim(),
      session_id: sessionId || undefined,
      debug_mode: debugMode
    };

    onExecute(request);
  }, [message, disabled, sessionId, debugMode, onExecute]);

  const getWorkflowExampleInputs = useCallback((workflow: WorkflowConfig): string[] => {
    // Generate example inputs based on workflow type and steps
    const examples = [
      `Execute the ${workflow.name} workflow`,
      'Start the workflow process',
      'Run this workflow for me'
    ];

    // Add workflow-specific examples based on name patterns
    const workflowName = workflow.name.toLowerCase();
    if (workflowName.includes('briefing') || workflowName.includes('summary')) {
      examples.push('Generate today\'s briefing', 'Create a summary report');
    } else if (workflowName.includes('analysis') || workflowName.includes('research')) {
      examples.push('Analyze the current situation', 'Research the latest trends');
    } else if (workflowName.includes('data') || workflowName.includes('processing')) {
      examples.push('Process the data files', 'Clean and analyze the dataset');
    }

    return examples.slice(0, 4); // Limit to 4 examples
  }, []);

  const handleWorkflowChange = useCallback((updatedWorkflow: WorkflowConfig) => {
    if (onWorkflowChange) {
      onWorkflowChange(updatedWorkflow);
    }
  }, [onWorkflowChange]);

  return (
    <div className="h-full flex flex-col">
      {/* Mode Toggle */}
      <div className="p-4 border-b border-border">
        <WorkflowModeToggle
          mode={mode}
          onModeChange={onModeChange}
          disabled={disabled}
        />
      </div>

      {/* Content based on mode */}
      <div className="flex-1 overflow-hidden">
        {mode === 'text' ? (
          // Text Mode - Original WorkflowInputPanel content
          <div className="p-4 space-y-6 h-full overflow-y-auto">
            {/* Workflow Info */}
            <div className="space-y-3">
              <h3 className="font-medium text-foreground">Workflow Information</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Name:</span>
                  <span className="text-sm font-medium">{memoizedWorkflow.name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Steps:</span>
                  <span className="text-sm font-medium">{memoizedWorkflow.steps?.length || 0}</span>
                </div>
                {memoizedWorkflow.description && (
                  <div className="space-y-1">
                    <span className="text-sm text-muted-foreground">Description:</span>
                    <p className="text-sm">{memoizedWorkflow.description}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Step Preview */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-foreground">Workflow Steps</h4>
              <div className="space-y-2">
                {memoizedWorkflow.steps?.map((step, index) => (
                  <div key={index} className="flex items-center gap-2 text-sm">
                    <span className="w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
                      {index + 1}
                    </span>
                    <span className="text-muted-foreground">
                      {typeof step === 'string' ? step : step.name}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Initial Input */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="initial-input">Initial Input *</Label>
                <Textarea
                  id="initial-input"
                  placeholder="Enter the initial input for this workflow..."
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="min-h-[120px] resize-none"
                  disabled={disabled}
                />
                <div className="text-xs text-muted-foreground text-right">
                  {message.length} characters
                </div>
              </div>

              {/* Session Management */}
              <WorkflowSessionSelector
                workflowName={memoizedWorkflow.name}
                selectedSessionId={sessionId}
                onSessionSelect={setSessionId}
                onSessionCreate={handleSessionCreate}
                disabled={disabled}
              />

              {/* Advanced Options */}
              <div className="space-y-3">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="w-full justify-between"
                  disabled={disabled}
                >
                  Advanced Options
                  <ChevronDown className={`h-4 w-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
                </Button>
                
                <AnimatePresence>
                  {showAdvanced && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="space-y-3 overflow-hidden"
                    >
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="debug"
                          checked={debugMode}
                          onCheckedChange={setDebugMode}
                          disabled={disabled}
                        />
                        <Label htmlFor="debug" className="text-sm">Debug mode (show step details)</Label>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Execute Button */}
              <Button
                type="submit"
                className="w-full"
                disabled={!message.trim() || disabled}
              >
                {disabled ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Executing Workflow...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Execute Workflow
                  </>
                )}
              </Button>
            </form>

            {/* Input Examples */}
            {!disabled && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-muted-foreground">Example inputs:</h4>
                <div className="space-y-1">
                  {getWorkflowExampleInputs(memoizedWorkflow).map((example, index) => (
                    <button
                      key={index}
                      type="button"
                      onClick={() => setMessage(example)}
                      className="block w-full text-left text-xs text-muted-foreground hover:text-foreground p-2 rounded border border-border hover:bg-accent transition-colors"
                    >
                      "{example}"
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          // Visual Mode - Visual Workflow Runner
          <VisualWorkflowRunner
            workflow={memoizedWorkflow}
            onExecute={(input, sessionId) => {
              const request: WorkflowExecutionRequest = {
                initial_input: input,
                session_id: sessionId,
                debug_mode: debugMode
              };
              onExecute(request);
            }}
            onConvertToText={() => onModeChange('text')}
            isExecuting={disabled}
          />
        )}
      </div>
    </div>
  );
};

// Export the memoized component
export const EnhancedWorkflowInputPanel = React.memo(EnhancedWorkflowInputPanelComponent, areEnhancedWorkflowInputPanelPropsEqual); 