import React, { useState } from 'react';
import { VisualWorkflowRunner } from '@/components/execution/visual/VisualWorkflowRunner';
import { WorkflowConfig } from '@/types/execution';
import { Button } from '@/components/ui/button';
import { Play, ArrowLeft } from 'lucide-react';

// Example workflow for demo
const demoWorkflow: WorkflowConfig = {
  name: 'History Test Workflow A',
  type: 'simple_workflow',
  description: 'Base case: 2 agents both enabled for history',
  steps: [
    'History Test Agent A1',
    'History Test Agent A2'
  ]
};

const WorkflowRunnerDemo: React.FC = () => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<string | null>(null);

  const handleExecute = async (input: string, sessionId?: string) => {
    console.log('Executing workflow with:', { input, sessionId });
    
    setIsExecuting(true);
    setExecutionResult(null);

    // Simulate workflow execution
    setTimeout(() => {
      setIsExecuting(false);
      setExecutionResult(`Workflow executed successfully with input: "${input}"`);
    }, 3000);
  };

  const handleConvertToText = () => {
    console.log('Switching to text mode');
    // In a real app, this would switch to text mode
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-xl font-semibold text-foreground">Workflow Runner Demo</h1>
            <p className="text-sm text-muted-foreground">
              Visual workflow execution interface
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.location.href = '/workflows'}
          >
            View All Workflows
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <VisualWorkflowRunner
          workflow={demoWorkflow}
          onExecute={handleExecute}
          onConvertToText={handleConvertToText}
          isExecuting={isExecuting}
        />
      </div>

      {/* Execution Result Toast */}
      {executionResult && (
        <div className="fixed bottom-4 right-4 bg-green-600 text-white p-4 rounded-lg shadow-lg">
          <div className="flex items-center gap-2">
            <Play className="h-4 w-4" />
            <span>{executionResult}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkflowRunnerDemo; 