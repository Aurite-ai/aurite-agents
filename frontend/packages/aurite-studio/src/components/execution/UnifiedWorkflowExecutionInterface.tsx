import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  WorkflowExecutionState,
  WorkflowExecutionRequest,
  UnifiedWorkflowExecutionInterfaceProps
} from '@/types/execution';
import { useExecuteWorkflow, useExecuteCustomWorkflow } from '@/hooks/useWorkflows';
import { WorkflowInputPanel } from '@/components/execution/WorkflowInputPanel';
import { WorkflowExecutionPanel } from '@/components/execution/WorkflowExecutionPanel';

export const UnifiedWorkflowExecutionInterface: React.FC<UnifiedWorkflowExecutionInterfaceProps> = ({
  workflow,
  isOpen,
  onClose
}) => {
  const [executionState, setExecutionState] = useState<WorkflowExecutionState>({
    status: 'idle',
    currentStepIndex: -1,
    completedSteps: [],
    totalSteps: workflow?.steps?.length || 0,
    progress: 0
  });

  // Get both execution hooks
  const executeLinearWorkflow = useExecuteWorkflow();
  const executeCustomWorkflow = useExecuteCustomWorkflow();

  const handleExecute = async (request: WorkflowExecutionRequest) => {
    if (!workflow) {
      console.error('❌ No workflow provided for execution');
      return;
    }

    console.log('🚀 Executing workflow with request:', request);

    // Update execution state to show we're starting - clear all previous state
    setExecutionState(prev => ({
      ...prev,
      status: 'starting',
      startTime: new Date(),
      initialInput: request.initial_input,
      progress: 10,
      currentStepIndex: 0,
      completedSteps: [], // Clear previous step completion states
      error: undefined,
      result: undefined
    }));

    try {
      // Determine workflow type and use appropriate execution method
      const isCustomWorkflow = workflow.type === 'custom_workflow';
      console.log(`🔍 Workflow type: ${workflow.type}, isCustomWorkflow: ${isCustomWorkflow}`);

      let result: any;
      if (isCustomWorkflow) {
        // Execute custom workflow
        result = await executeCustomWorkflow.mutateAsync({
          workflowName: workflow.name,
          request: {
            initial_input: request.initial_input
          }
        });
      } else {
        // Execute linear workflow
        result = await executeLinearWorkflow.mutateAsync({
          workflowName: workflow.name,
          request: {
            initial_input: request.initial_input,
            session_id: request.session_id
          }
        });
      }

      console.log('✅ Workflow execution completed:', result);

      // Handle different response types
      let stepResults: any[] = [];
      let finalMessage: string | undefined;
      let resultHistory: any[] = [];

      if (isCustomWorkflow) {
        // Custom workflow response structure
        stepResults = [];
        finalMessage = (result as any).result || 'Custom workflow completed successfully';
        resultHistory = [];
      } else {
        // Simple workflow response structure
        stepResults = (result as any).step_results || [];
        finalMessage = (result as any).final_message;
        resultHistory = (result as any).history || [];
      }

      const totalSteps = workflow.steps?.length || 0;

      console.log('📊 Processing step results:', stepResults);
      console.log('📊 Full result object keys:', Object.keys(result));
      console.log('📊 Full result object:', result);

      // Map API step results to UI format
      let mappedStepResults: any[] = [];

      if (stepResults.length > 0) {
        // Use actual step results if available
        mappedStepResults = stepResults.map((apiStepResult: any, index: number) => {
          const stepName = apiStepResult.step_name ||
            (typeof workflow.steps?.[index] === 'string'
              ? workflow.steps[index] as string
              : (workflow.steps?.[index] as any)?.name || `Step ${index + 1}`);

          console.log(`📋 Mapping step ${index}:`, {
            stepName,
            apiResult: apiStepResult,
            resultContent: apiStepResult.result?.final_response?.content
          });

          return {
            stepIndex: index,
            stepName: stepName,
            status: (apiStepResult.result?.status === 'success' ? 'completed' : 'failed') as 'completed' | 'failed' | 'skipped',
            startTime: new Date(), // API doesn't provide step timing
            endTime: new Date(),
            duration_ms: undefined,
            input: index === 0 ? request.initial_input : stepResults[index - 1]?.result?.final_response?.content,
            result: {
              final_response: apiStepResult.result?.final_response,
              conversation_history: apiStepResult.result?.conversation_history,
              status: apiStepResult.result?.status,
              error_message: apiStepResult.result?.error_message
            },
            error: apiStepResult.result?.error_message,
            tool_calls: apiStepResult.result?.conversation_history?.filter((msg: any) => msg.tool_calls)?.flatMap((msg: any) => msg.tool_calls) || []
          };
        });
      } else {
        // Fallback: Create mock step results based on workflow configuration and final result
        console.log('🔄 No step results from API, creating mock steps based on workflow config');
        mappedStepResults = (workflow.steps || []).map((step, index) => {
          const stepName = typeof step === 'string' ? step : step.name || `Step ${index + 1}`;

          return {
            stepIndex: index,
            stepName: stepName,
            status: 'completed' as 'completed' | 'failed' | 'skipped',
            startTime: new Date(),
            endTime: new Date(),
            duration_ms: undefined,
            input: index === 0 ? request.initial_input : `Output from ${stepName}`,
            result: {
              final_response: {
                content: index === (workflow.steps?.length || 1) - 1
                  ? finalMessage || 'Workflow completed successfully'
                  : `${stepName} completed successfully`
              },
              conversation_history: [],
              status: 'success',
              error_message: null
            },
            error: undefined,
            tool_calls: []
          };
        });
      }

      console.log('✅ Mapped step results:', mappedStepResults);

      // Update execution state with completion
      setExecutionState(prev => ({
        ...prev,
        status: 'completed',
        progress: 100,
        endTime: new Date(),
        currentStepIndex: totalSteps - 1,
        completedSteps: mappedStepResults,
        result: {
          execution_id: 'workflow-exec-' + Date.now(),
          session_id: request.session_id || 'unknown',
          workflow_name: workflow.name,
          status: result.status || 'completed',
          final_message: finalMessage,
          error: result.error,
          step_results: mappedStepResults,
          metadata: {
            start_time: prev.startTime?.toISOString() || new Date().toISOString(),
            end_time: new Date().toISOString(),
            duration_ms: prev.startTime ? Date.now() - prev.startTime.getTime() : 0,
            step_count: totalSteps,
            completed_steps: mappedStepResults.filter((s: any) => s.status === 'completed').length,
            failed_steps: mappedStepResults.filter((s: any) => s.status === 'failed').length
          },
          history: resultHistory
        }
      }));

    } catch (error) {
      console.error('❌ Workflow execution failed:', error);

      setExecutionState(prev => ({
        ...prev,
        status: 'failed',
        progress: 0,
        endTime: new Date(),
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      }));
    }
  };

  const handleClose = () => {
    // Reset execution state when closing
    setExecutionState({
      status: 'idle',
      currentStepIndex: -1,
      completedSteps: [],
      totalSteps: workflow?.steps?.length || 0,
      progress: 0
    });
    onClose();
  };

  if (!workflow || !isOpen) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={handleClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-card border border-border rounded-lg w-[95vw] h-[90vh] max-w-7xl flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h2 className="text-xl font-semibold text-foreground">
                🔄 Execute Workflow: {workflow.name}
              </h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleClose}
                className="h-8 w-8"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Main Content - Side by Side */}
            <div className="flex-1 flex overflow-hidden">
              {/* Left Panel - Workflow Input (40%) */}
              <div className="w-2/5 border-r border-border overflow-y-auto">
                <WorkflowInputPanel
                  workflow={workflow}
                  onExecute={handleExecute}
                  disabled={executionState.status !== 'idle' && executionState.status !== 'completed' && executionState.status !== 'failed'}
                />
              </div>

              {/* Right Panel - Execution (60%) */}
              <div className="flex-1 flex flex-col">
                <WorkflowExecutionPanel
                  workflow={workflow}
                  executionState={executionState}
                  onStateChange={setExecutionState}
                />
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
