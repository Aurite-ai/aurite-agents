import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Check, X, Loader2, Circle, MinusCircle, CheckCircle, XCircle, MessageSquare, Wrench } from 'lucide-react';
import { StepExecutionDisplayProps } from '@/types/execution';

export const StepExecutionDisplay: React.FC<StepExecutionDisplayProps> = ({ 
  steps, 
  currentStepIndex, 
  completedSteps, 
  currentStepProgress 
}) => {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  const toggleStepExpansion = (stepIndex: number) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepIndex)) {
      newExpanded.delete(stepIndex);
    } else {
      newExpanded.add(stepIndex);
    }
    setExpandedSteps(newExpanded);
  };

  return (
    <div className="space-y-3">
      {steps.map((step, index) => {
        const stepName = typeof step === 'string' ? step : step.name;
        const completedStep = completedSteps.find(s => s.stepIndex === index);
        const isExecuting = index === currentStepIndex;
        const isCompleted = !!completedStep;
        const isPending = index > currentStepIndex;
        const isExpanded = expandedSteps.has(index);

        return (
          <div 
            key={index}
            className={`border rounded-lg transition-all duration-200 ${
              isExecuting ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' :
              isCompleted ? 'border-green-500 bg-green-50 dark:bg-green-900/20' :
              'border-border bg-card'
            }`}
          >
            {/* Step Header */}
            <div 
              className="p-4 cursor-pointer"
              onClick={() => (isCompleted || isExecuting) && toggleStepExpansion(index)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    isExecuting ? 'bg-blue-500 text-white' :
                    isCompleted ? 'bg-green-500 text-white' :
                    'bg-muted text-muted-foreground'
                  }`}>
                    {isExecuting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : isCompleted ? (
                      completedStep?.status === 'failed' ? (
                        <X className="h-4 w-4" />
                      ) : (
                        <Check className="h-4 w-4" />
                      )
                    ) : (
                      index + 1
                    )}
                  </div>
                  <div>
                    <h4 className="font-medium">{stepName}</h4>
                    <p className="text-sm text-muted-foreground">
                      {isExecuting ? 'Executing...' :
                       isCompleted ? `Completed` :
                       'Pending'}
                    </p>
                  </div>
                </div>
                
                {(isCompleted || isExecuting) && (
                  <ChevronDown className={`h-4 w-4 transition-transform ${
                    isExpanded ? 'rotate-180' : ''
                  }`} />
                )}
              </div>
            </div>

            {/* Step Content - Expandable */}
            <AnimatePresence>
              {isExpanded && (isCompleted || isExecuting) && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-border"
                >
                  <div className="p-4 space-y-4">
                    {/* Step Input */}
                    {completedStep?.input && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <MessageSquare className="h-4 w-4 text-blue-500" />
                          <h5 className="text-sm font-medium">Input:</h5>
                        </div>
                        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-sm">
                          {typeof completedStep.input === 'string' 
                            ? completedStep.input 
                            : JSON.stringify(completedStep.input, null, 2)
                          }
                        </div>
                      </div>
                    )}

                    {/* Step Final Response */}
                    {completedStep?.result?.final_response?.content && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Check className="h-4 w-4 text-green-500" />
                          <h5 className="text-sm font-medium">Final Response:</h5>
                        </div>
                        <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-sm">
                          {completedStep.result.final_response.content}
                        </div>
                      </div>
                    )}

                    {/* Tool Calls */}
                    {completedStep?.tool_calls && completedStep.tool_calls.length > 0 && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Wrench className="h-4 w-4 text-orange-500" />
                          <h5 className="text-sm font-medium">Tool Calls ({completedStep.tool_calls.length}):</h5>
                        </div>
                        <div className="space-y-2">
                          {completedStep.tool_calls.map((toolCall: any, toolIndex: number) => (
                            <div key={toolIndex} className="p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
                              <div className="text-sm">
                                <div className="font-medium text-orange-700 dark:text-orange-300">
                                  {toolCall.function?.name || toolCall.name || 'Tool Call'}
                                </div>
                                {toolCall.function?.arguments && (
                                  <div className="mt-1 text-xs text-orange-600 dark:text-orange-400">
                                    {typeof toolCall.function.arguments === 'string' 
                                      ? toolCall.function.arguments 
                                      : JSON.stringify(toolCall.function.arguments, null, 2)
                                    }
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Conversation History */}
                    {completedStep?.result?.conversation_history && completedStep.result.conversation_history.length > 0 && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <MessageSquare className="h-4 w-4 text-purple-500" />
                          <h5 className="text-sm font-medium">Conversation History ({completedStep.result.conversation_history.length} messages):</h5>
                        </div>
                        <div className="max-h-40 overflow-y-auto space-y-2">
                          {completedStep.result.conversation_history.map((message: any, msgIndex: number) => (
                            <div key={msgIndex} className={`p-2 rounded text-xs ${
                              message.role === 'user' 
                                ? 'bg-blue-50 dark:bg-blue-900/20 border-l-2 border-blue-500' 
                                : message.role === 'assistant'
                                ? 'bg-green-50 dark:bg-green-900/20 border-l-2 border-green-500'
                                : 'bg-gray-50 dark:bg-gray-900/20 border-l-2 border-gray-500'
                            }`}>
                              <div className="font-medium capitalize">{message.role}:</div>
                              <div className="mt-1">
                                {typeof message.content === 'string' 
                                  ? message.content 
                                  : JSON.stringify(message.content, null, 2)
                                }
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Step Error */}
                    {completedStep?.error && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <X className="h-4 w-4 text-red-500" />
                          <h5 className="text-sm font-medium text-red-600">Error:</h5>
                        </div>
                        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
                          {completedStep.error}
                        </div>
                      </div>
                    )}

                    {/* Current Step Progress */}
                    {isExecuting && currentStepProgress !== undefined && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span>Step Progress:</span>
                          <span>{Math.round(currentStepProgress)}%</span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-2">
                          <div 
                            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${currentStepProgress}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
};
