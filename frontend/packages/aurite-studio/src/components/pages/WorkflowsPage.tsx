import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Workflow, Plus, Edit, Play, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useWorkflowsWithConfigs, useCustomWorkflowsWithConfigs, useExecuteWorkflow, useExecuteCustomWorkflow } from '@/hooks/useWorkflows';
import { UnifiedWorkflowExecutionInterface } from '@/components/execution/UnifiedWorkflowExecutionInterface';
import { WorkflowConfig } from '@/types/execution';
import workflowsService from '@/services/workflows.service';
import toast from 'react-hot-toast';

export default function WorkflowsPage() {
  const navigate = useNavigate();

  // API Hooks
  const { data: workflows = [], isLoading: workflowsLoading } = useWorkflowsWithConfigs();
  const { data: customWorkflows = [], isLoading: customWorkflowsLoading } = useCustomWorkflowsWithConfigs();
  const executeWorkflow = useExecuteWorkflow();
  const executeCustomWorkflow = useExecuteCustomWorkflow();

  // Workflow Execution Interface State
  const [workflowExecutionInterface, setWorkflowExecutionInterface] = useState<{
    isOpen: boolean;
    workflow: WorkflowConfig | null;
  }>({ isOpen: false, workflow: null });

  const isLoading = workflowsLoading || customWorkflowsLoading;
  const allWorkflows = [...workflows, ...customWorkflows];

  const handleNewWorkflow = () => {
    // Navigate to new workflow form
    navigate('/workflows/new');
  };

  const handleEditWorkflow = (workflow: any) => {
    const workflowName = typeof workflow.name === 'string' ? workflow.name : (workflow.name as any)?.name || 'Unknown Workflow';

    // Navigate to edit form
    navigate(`/workflows/${encodeURIComponent(workflowName)}/edit`);
  };

  const handleRunWorkflow = async (workflow: any) => {
    const workflowName = typeof workflow.name === 'string' ? workflow.name : (workflow.name as any)?.name || 'Unknown Workflow';

    try {
      // Fetch the actual workflow configuration to get the steps
      let workflowConfig: WorkflowConfig;

      if (workflow.type === 'custom_workflow') {
        const config = await workflowsService.getCustomWorkflowConfigByName(workflowName);
        workflowConfig = {
          type: 'custom_workflow',
          name: workflowName,
          description: config.description,
          module_path: config.module_path,
          class_name: config.class_name,
          _source_file: workflow.configFile,
        };
      } else {
        const config = await workflowsService.getWorkflowConfigByName(workflowName);
        workflowConfig = {
          type: 'linear_workflow',
          name: workflowName,
          description: config.description,
          steps: config.steps || [],
          _source_file: workflow.configFile,
        };
      }

      setWorkflowExecutionInterface({
        isOpen: true,
        workflow: workflowConfig
      });
    } catch (error) {
      console.error('Failed to load workflow configuration:', error);
      toast.error('Failed to load workflow configuration');
    }
  };

  return (
    <>
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-6xl mx-auto space-y-6"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Workflows</h1>
            <p className="text-muted-foreground mt-1">Design and manage agent workflows</p>
          </div>
          <Button className="gap-2" onClick={handleNewWorkflow}>
            <Plus className="h-4 w-4" />
            New Workflow
          </Button>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Empty State */}
        {!isLoading && allWorkflows.length === 0 && (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="bg-card border border-border rounded-lg p-12 text-center space-y-4"
          >
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
              <Workflow className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-medium text-foreground">No workflows created yet</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Create your first workflow to automate your agent processes
              </p>
            </div>
            <Button className="gap-2" onClick={handleNewWorkflow}>
              <Plus className="h-4 w-4" />
              Create Your First Workflow
            </Button>
          </motion.div>
        )}

        {/* Workflows Grid */}
        {!isLoading && allWorkflows.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {allWorkflows.map((workflow, index) => {
              const workflowName = typeof workflow.name === 'string' ? workflow.name : (workflow.name as any)?.name || 'Unknown Workflow';
              const badgeText = workflow.type === 'linear_workflow' ? 'Linear' : 'Custom';
              const badgeColor = workflow.type === 'linear_workflow' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' : 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400';

              return (
                <motion.div
                  key={workflowName}
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: index * 0.1 }}
                  className="gradient-card rounded-lg p-4 space-y-3 hover:shadow-md transition-all duration-200 gradient-glow"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-foreground">{workflowName}</h3>
                      <span className={`px-2 py-1 text-xs rounded-full font-medium ${badgeColor}`}>
                        {badgeText}
                      </span>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">
                        {'description' in workflow ? workflow.description || (workflow.configFile ? 'Configured and ready' : 'Configuration pending') : (workflow.configFile ? 'Configured and ready' : 'Configuration pending')}
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1.5"
                      onClick={() => handleEditWorkflow(workflow)}
                    >
                      <Edit className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      className="gap-1.5"
                      onClick={() => handleRunWorkflow(workflow)}
                      disabled={
                        workflow.type === 'custom_workflow'
                          ? executeCustomWorkflow.isWorkflowExecuting(workflowName)
                          : executeWorkflow.isWorkflowExecuting(workflowName)
                      }
                    >
                      {(workflow.type === 'custom_workflow'
                        ? executeCustomWorkflow.isWorkflowExecuting(workflowName)
                        : executeWorkflow.isWorkflowExecuting(workflowName)
                      ) ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Play className="h-3.5 w-3.5" />
                      )}
                      Run
                    </Button>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </motion.div>

      {/* Unified Workflow Execution Interface */}
      <UnifiedWorkflowExecutionInterface
        workflow={workflowExecutionInterface.workflow}
        isOpen={workflowExecutionInterface.isOpen}
        onClose={() => setWorkflowExecutionInterface({ isOpen: false, workflow: null })}
      />
    </>
  );
}
