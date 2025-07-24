import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Loader2, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { WorkflowInputPanelProps, WorkflowExecutionRequest, WorkflowConfig } from '@/types/execution';
import { WorkflowSessionSelector } from './WorkflowSessionSelector';

export const WorkflowInputPanel: React.FC<WorkflowInputPanelProps> = ({
  workflow,
  onExecute,
  disabled = false
}) => {
  const [message, setMessage] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [debugMode, setDebugMode] = useState(false);

  const handleSessionCreate = (sessionName: string) => {
    // For now, we'll just generate a mock session ID
    // In the future, this would call an API to create the session
    const newSessionId = `workflow-session-${Date.now()}`;
    setSessionId(newSessionId);
    console.log(`Created new workflow session: ${sessionName} (${newSessionId})`);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || disabled) return;

    const request: WorkflowExecutionRequest = {
      initial_input: message.trim(),
      session_id: sessionId || undefined,
      debug_mode: debugMode
    };

    onExecute(request);
  };

  const getWorkflowExampleInputs = (workflow: WorkflowConfig): string[] => {
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
  };

  return (
    <div className="p-4 space-y-6">
      {/* Workflow Info */}
      <div className="space-y-3">
        <h3 className="font-medium text-foreground">Workflow Information</h3>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Name:</span>
            <span className="text-sm font-medium">{workflow.name}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Steps:</span>
            <span className="text-sm font-medium">{workflow.steps?.length || 0}</span>
          </div>
          {workflow.description && (
            <div className="space-y-1">
              <span className="text-sm text-muted-foreground">Description:</span>
              <p className="text-sm">{workflow.description}</p>
            </div>
          )}
        </div>
      </div>

      {/* Step Preview */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-foreground">Workflow Steps</h4>
        <div className="space-y-2">
          {workflow.steps?.map((step, index) => (
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
          workflowName={workflow.name}
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
            {getWorkflowExampleInputs(workflow).map((example, index) => (
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
  );
};
