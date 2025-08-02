import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, CheckCircle, AlertCircle, StopCircle, User, Bot, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ExecutionPanelProps } from '@/types/execution';
import { ExecutionProgress } from './ExecutionProgress';
import { ToolCallIndicator } from './ToolCallIndicator';
import { ResponseDisplay } from './ResponseDisplay';
import { ContinueConversation } from './ContinueConversation';
import { DebugSection } from './DebugSection';

export const ExecutionPanel: React.FC<ExecutionPanelProps> = ({
  agent,
  executionState,
  onStateChange,
  onClose
}) => {
  const navigate = useNavigate();
  const handleCancelExecution = () => {
    onStateChange({
      ...executionState,
      status: 'cancelled',
      endTime: new Date()
    });
  };

  const handleContinueConversation = (message: string) => {
    console.log('Continue conversation with:', message);
    // TODO: Implement continue conversation logic
  };

  const renderContent = () => {
    switch (executionState.status) {
      case 'idle':
        return (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
                <Play className="h-8 w-8 text-muted-foreground" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-medium">Ready to Execute</h3>
                <p className="text-sm text-muted-foreground">
                  Enter your message and click "Execute Agent" to start
                </p>
              </div>
            </div>
          </div>
        );

      case 'starting':
      case 'executing':
        return (
          <div className="flex-1 flex flex-col h-full">
            {/* Progress Header */}
            <div className="flex-shrink-0 p-4 border-b space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Executing Agent</h3>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCancelExecution}
                >
                  <StopCircle className="h-3 w-3 mr-1" />
                  Cancel
                </Button>
              </div>
              
              <ExecutionProgress
                progress={executionState.progress}
                currentStep={executionState.currentStep}
                startTime={executionState.startTime}
              />
            </div>

            {/* Execution Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 max-h-[calc(100vh-300px)]">
              {/* User Message */}
              {executionState.userMessage && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                      <User className="h-3 w-3 text-primary-foreground" />
                    </div>
                    <span className="text-sm font-medium">You</span>
                  </div>
                  <div className="ml-8 p-3 bg-muted rounded-lg">
                    {executionState.userMessage}
                  </div>
                </div>
              )}

              {/* Tool Calls */}
              {executionState.toolCalls.map((toolCall) => (
                <ToolCallIndicator
                  key={toolCall.id}
                  toolCall={toolCall}
                />
              ))}

              {/* Assistant Response */}
              {executionState.currentResponse && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                      <Bot className="h-3 w-3 text-white" />
                    </div>
                    <span className="text-sm font-medium">Assistant</span>
                    {executionState.status === 'executing' && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        typing...
                      </div>
                    )}
                  </div>
                  <div className="ml-8">
                    <ResponseDisplay
                      content={executionState.currentResponse}
                      isStreaming={executionState.status === 'executing'}
                    />
                  </div>
                </div>
              )}

              {/* Mock execution progress for demo */}
              {executionState.status === 'starting' && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                      <Loader2 className="h-3 w-3 animate-spin text-white" />
                    </div>
                    <span className="text-sm font-medium">System</span>
                  </div>
                  <div className="ml-8 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <p className="text-sm text-blue-700 dark:text-blue-300">
                      Initializing agent execution...
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        );

      case 'completed':
        return (
          <div className="flex-1 flex flex-col h-full">
            {/* Completion Header */}
            <div className="flex-shrink-0 p-4 border-b">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <h3 className="font-medium">Execution Completed</h3>
                </div>
                <div className="text-sm text-muted-foreground">
                  {executionState.endTime && executionState.startTime && 
                    `${Math.round((executionState.endTime.getTime() - executionState.startTime.getTime()) / 1000)}s`
                  }
                </div>
              </div>
            </div>

            {/* Results */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 max-h-[calc(100vh-300px)]">
              {/* Conversation History */}
              <div className="space-y-4">
                {/* User Message */}
                {executionState.userMessage && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      <span className="text-sm font-medium">You</span>
                    </div>
                    <div className="ml-6 p-3 bg-muted rounded-lg">
                      {executionState.userMessage}
                    </div>
                  </div>
                )}

                {/* Assistant Response */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Bot className="h-4 w-4 text-green-500" />
                    <span className="text-sm font-medium">Assistant</span>
                  </div>
                  <div className="ml-6">
                    <ResponseDisplay
                      content={executionState.result?.final_response?.content?.[0]?.text || executionState.currentResponse || 'No response available'}
                      isStreaming={false}
                    />
                  </div>
                </div>
              </div>

              {/* Tool Execution Summary */}
              {executionState.toolCalls.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Tools Used</h4>
                  <div className="space-y-2">
                    {executionState.toolCalls.map((toolCall) => (
                      <ToolCallIndicator
                        key={toolCall.id}
                        toolCall={toolCall}
                        showDetails={false}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Debug Section */}
              <DebugSection
                toolCalls={executionState.result?.tool_calls || executionState.toolCalls}
                streamEvents={executionState.streamEvents}
                isVisible={!!executionState.debugMode}
              />
            </div>

            {/* Continue Conversation */}
            <div className="flex-shrink-0 border-t p-4">
              <ContinueConversation
                sessionId={executionState.result?.session_id || 'current-session'}
                agentName={agent.name}
                onSendMessage={handleContinueConversation}
              />
            </div>
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
                <h3 className="text-lg font-medium">Execution Failed</h3>
                <p className="text-sm text-muted-foreground max-w-md">
                  {executionState.error || 'An unexpected error occurred during execution.'}
                </p>
                <Button
                  variant="outline"
                  onClick={() => onStateChange({ ...executionState, status: 'idle' })}
                >
                  Try Again
                </Button>
              </div>
            </div>
          </div>
        );

      case 'cancelled':
        return (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-yellow-100 dark:bg-yellow-900/30 rounded-full flex items-center justify-center mx-auto">
                <StopCircle className="h-8 w-8 text-yellow-500" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-medium">Execution Cancelled</h3>
                <p className="text-sm text-muted-foreground max-w-md">
                  The execution was cancelled by the user.
                </p>
                <Button
                  variant="outline"
                  onClick={() => onStateChange({ ...executionState, status: 'idle' })}
                >
                  Start New Execution
                </Button>
              </div>
            </div>
          </div>
        );

      case 'max_iterations_reached':
        return (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-orange-100 dark:bg-orange-900/30 rounded-full flex items-center justify-center mx-auto">
                <AlertCircle className="h-8 w-8 text-orange-500" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-medium">Maximum Iterations Reached</h3>
                <p className="text-sm text-muted-foreground max-w-md">
                  The agent reached its maximum iteration limit{agent.max_iterations ? ` of ${agent.max_iterations}` : ''}. 
                  Consider increasing the max_iterations setting or simplifying your request.
                </p>
                <div className="flex gap-2 justify-center">
                  <Button
                    variant="outline"
                    onClick={() => onStateChange({ ...executionState, status: 'idle' })}
                  >
                    Try Again
                  </Button>
                  <Button
                    variant="default"
                    onClick={() => {
                      // Navigate to agent edit page and close modal
                      navigate(`/agents/${encodeURIComponent(agent.name)}/edit?focus=max_iterations`);
                      onClose?.();
                    }}
                  >
                    Adjust Settings
                  </Button>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {renderContent()}
    </div>
  );
};
