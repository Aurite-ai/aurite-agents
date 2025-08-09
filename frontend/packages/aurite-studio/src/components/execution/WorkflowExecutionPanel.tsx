import React from 'react';
import { Workflow, CheckCircle, AlertCircle, StopCircle, User, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { WorkflowExecutionPanelProps } from '@/types/execution';
import { WorkflowProgress } from '@/components/execution/WorkflowProgress';
import { ContinueWorkflowConversation } from '@/components/execution/ContinueWorkflowConversation';

export const WorkflowExecutionPanel: React.FC<WorkflowExecutionPanelProps> = ({
  workflow,
  executionState,
  onStateChange,
}) => {
  const handleContinueConversation = (message: string) => {
    // TODO: Implement workflow conversation continuation
    console.log('Continue workflow conversation:', message);
  };

  const isCustomWorkflow = workflow.type === 'custom_workflow';

  const renderContent = () => {
    switch (executionState.status) {
      case 'idle':
        return (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
                <Workflow className="h-8 w-8 text-muted-foreground" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-medium">Ready to Execute Workflow</h3>
                <p className="text-sm text-muted-foreground">
                  Enter your initial input and click "Execute Workflow" to start
                </p>
                {!isCustomWorkflow && (
                  <div className="text-xs text-muted-foreground">
                    {workflow.steps?.length || 0} steps will be executed in sequence
                  </div>
                )}
                {isCustomWorkflow && (
                  <div className="text-xs text-muted-foreground">
                    Custom workflow will be executed as a single operation
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 'starting':
      case 'executing':
        if (isCustomWorkflow) {
          // Custom workflow execution - simple loading state
          return (
            <div className="flex-1 flex flex-col">
              {/* Simple Header */}
              <div className="p-4 border-b">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium">Executing Custom Workflow</h3>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      // TODO: Implement workflow cancellation
                      console.log('Cancel workflow execution');
                    }}
                  >
                    <StopCircle className="h-3 w-3 mr-1" />
                    Cancel
                  </Button>
                </div>
              </div>

              {/* Simple Execution Content - Top-aligned layout */}
              <div className="flex-1 flex flex-col items-center pt-8 p-4 space-y-4">
                {/* Loading Indicator */}
                <div className="flex flex-col items-center space-y-4">
                  <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                    <Loader2 className="h-8 w-8 text-primary animate-spin" />
                  </div>
                  <div className="text-center space-y-2">
                    <h4 className="font-medium">Processing Custom Workflow</h4>
                    <p className="text-sm text-muted-foreground">
                      Please wait while the workflow executes...
                    </p>
                  </div>
                </div>

                {/* Initial Input Display - Closer to loading indicator */}
                {executionState.initialInput && (
                  <div className="w-full max-w-md space-y-2">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                        <User className="h-3 w-3 text-primary-foreground" />
                      </div>
                      <span className="text-sm font-medium">Initial Input</span>
                    </div>
                    <div className="ml-8 p-3 bg-muted rounded-lg">
                      {executionState.initialInput}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        }
        // Linear workflow execution - step-by-step progress
        return (
          <div className="flex-1 flex flex-col">
            {/* Progress Header */}
            <div className="p-4 border-b space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Executing Workflow</h3>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    // TODO: Implement workflow cancellation
                    console.log('Cancel workflow execution');
                  }}
                >
                  <StopCircle className="h-3 w-3 mr-1" />
                  Cancel
                </Button>
              </div>

              <WorkflowProgress
                steps={workflow.steps || []}
                currentStepIndex={executionState.currentStepIndex}
                completedSteps={executionState.completedSteps}
                currentStepProgress={executionState.currentStepProgress}
                startTime={executionState.startTime}
              />
            </div>

            {/* Execution Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Initial Input Display */}
              {executionState.initialInput && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                      <User className="h-3 w-3 text-primary-foreground" />
                    </div>
                    <span className="text-sm font-medium">Initial Input</span>
                  </div>
                  <div className="ml-8 p-3 bg-muted rounded-lg">{executionState.initialInput}</div>
                </div>
              )}

              {/* Hide Step Execution Display during execution to avoid duplicate loading spinners */}
              {/* StepExecutionDisplay will only be shown in the completed state */}
            </div>
          </div>
        );

      case 'completed':
        return (
          <div className="flex-1 flex flex-col h-full">
            {/* Completion Header - Fixed */}
            <div className="flex-shrink-0 p-4 border-b">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <h3 className="font-medium">Workflow Completed</h3>
                </div>
                <div className="text-sm text-muted-foreground">
                  {executionState.endTime &&
                    executionState.startTime &&
                    `${Math.round((executionState.endTime.getTime() - executionState.startTime.getTime()) / 1000)}s`}
                </div>
              </div>
            </div>

            {/* Scrollable Results Content */}
            <div className="flex-1 overflow-y-auto min-h-0">
              <div className="p-4 space-y-4">
                {/* Final Workflow Output */}
                {executionState.result?.final_message && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-foreground">Final Result</h4>
                    <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                      <div className="text-sm">{executionState.result.final_message}</div>
                    </div>
                  </div>
                )}

                {/* Step Results Summary - Only show for linear workflows */}
                {!isCustomWorkflow && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-foreground">Step Summary</h4>
                    {(() => {
                      console.log(
                        '🔍 Rendering step summary. Completed steps:',
                        executionState.completedSteps
                      );
                      return null;
                    })()}
                    {executionState.completedSteps.length === 0 ? (
                      <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                        <div className="text-sm text-yellow-700 dark:text-yellow-300">
                          No step results available. Check console for debugging info.
                        </div>
                        <div className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                          Execution state: {executionState.status}, Steps:{' '}
                          {executionState.completedSteps.length}
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {executionState.completedSteps.map((step, index) => (
                          <div key={index} className="p-3 bg-muted/20 rounded-lg space-y-2">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <CheckCircle className="h-4 w-4 text-green-500" />
                                <span className="text-sm font-medium">{step.stepName}</span>
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {step.status === 'completed' ? 'Success' : step.status}
                              </div>
                            </div>
                            {/* Show final response preview */}
                            {step.result?.final_response?.content && (
                              <div className="text-xs text-muted-foreground bg-muted/30 p-2 rounded border-l-2 border-green-500">
                                {step.result.final_response.content.length > 100
                                  ? `${step.result.final_response.content.substring(0, 100)}...`
                                  : step.result.final_response.content}
                              </div>
                            )}
                            {/* Show tool calls count */}
                            {step.tool_calls && step.tool_calls.length > 0 && (
                              <div className="text-xs text-orange-600 dark:text-orange-400">
                                🔧 {step.tool_calls.length} tool call
                                {step.tool_calls.length !== 1 ? 's' : ''} made
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Continue Conversation - Fixed at Bottom */}
            {executionState.result?.session_id && (
              <div className="flex-shrink-0 border-t p-4">
                <ContinueWorkflowConversation
                  sessionId={executionState.result.session_id}
                  workflowName={workflow.name}
                  onSendMessage={handleContinueConversation}
                />
              </div>
            )}
          </div>
        );

      case 'failed':
        return (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto">
                <AlertCircle className="h-8 w-8 text-red-500" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-medium">Workflow Failed</h3>
                <p className="text-sm text-muted-foreground max-w-md">
                  {executionState.error ||
                    'An unexpected error occurred during workflow execution.'}
                </p>
                <Button
                  variant="outline"
                  onClick={() =>
                    onStateChange({
                      ...executionState,
                      status: 'idle',
                      error: undefined,
                      result: undefined,
                    })
                  }
                >
                  Try Again
                </Button>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return <div className="flex flex-col h-full">{renderContent()}</div>;
};
