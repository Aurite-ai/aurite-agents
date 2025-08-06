import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Loader2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useAgentsWithConfigs } from '@/hooks/useAgents';
import { useWorkflowConfigByName, useUpdateWorkflow, useCreateWorkflow, useDeleteWorkflow } from '@/hooks/useWorkflows';
import { useQueryClient } from '@tanstack/react-query';

interface WorkflowFormProps {
  editMode?: boolean;
}

export default function WorkflowForm({ editMode = false }: WorkflowFormProps) {
  const navigate = useNavigate();
  const { name: workflowNameParam } = useParams<{ name: string }>();

  // Form state
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [workflowSteps, setWorkflowSteps] = useState<Array<{id: number, agent: string}>>([]);
  const [selectedAgentToAdd, setSelectedAgentToAdd] = useState('');
  const [workflowFormPopulated, setWorkflowFormPopulated] = useState(false);
  const [showWorkflowDeleteConfirmation, setShowWorkflowDeleteConfirmation] = useState(false);

  // API Hooks
  const { data: agents = [], isLoading: agentsLoading } = useAgentsWithConfigs();

  // Workflow-specific hooks
  const { data: workflowConfig, isLoading: workflowConfigLoading } = useWorkflowConfigByName(
    workflowNameParam || '',
    !!workflowNameParam && editMode
  );

  const updateWorkflow = useUpdateWorkflow();
  const createWorkflow = useCreateWorkflow();
  const deleteWorkflow = useDeleteWorkflow();

  // Query client for cache invalidation
  const queryClient = useQueryClient();

  // Helper function to extract agent name from complex agent object
  const extractAgentName = (agent: any): string => {
    if (typeof agent.name === 'string') {
      return agent.name;
    } else if (agent.name && typeof agent.name === 'object' && 'name' in agent.name) {
      return String((agent.name as any).name);
    } else if (agent.name) {
      return String(agent.name);
    } else {
      return 'Unknown Agent';
    }
  };

  // Effect to populate workflow form when workflow config is loaded
  useEffect(() => {
    if (editMode && workflowConfig && workflowNameParam && !workflowFormPopulated) {
      // Populate workflow form fields
      setWorkflowName(workflowConfig.name || '');
      setWorkflowDescription(workflowConfig.description || '');

      // Convert steps array to UI format
      if (workflowConfig.steps && Array.isArray(workflowConfig.steps)) {
        const stepsWithIds = workflowConfig.steps.map((step, index) => ({
          id: Date.now() + index,
          agent: step
        }));
        setWorkflowSteps(stepsWithIds);
      } else {
        setWorkflowSteps([]);
      }

      // Mark form as populated to prevent re-population
      setWorkflowFormPopulated(true);
    } else if (editMode && workflowNameParam && !workflowConfig && !workflowConfigLoading) {
      // Failed to load workflow config
    }
  }, [workflowConfig, workflowNameParam, editMode, workflowConfigLoading, workflowFormPopulated]);

  // Initialize form for create mode
  useEffect(() => {
    if (!editMode && !workflowFormPopulated) {
      // Reset ALL form fields to empty/default values for new workflow creation
      setWorkflowName('');
      setWorkflowDescription('');
      setWorkflowSteps([]);
      setSelectedAgentToAdd('');

      // Mark form as populated to prevent re-initialization
      setWorkflowFormPopulated(true);
    }
  }, [editMode, workflowFormPopulated]);

  const addWorkflowStep = () => {
    if (selectedAgentToAdd) {
      setWorkflowSteps([...workflowSteps, { id: Date.now(), agent: selectedAgentToAdd }]);
      setSelectedAgentToAdd(''); // Reset selection after adding
    }
  };

  const removeWorkflowStep = (stepId: number) => {
    setWorkflowSteps(workflowSteps.filter(step => step.id !== stepId));
  };

  const handleSubmit = () => {
    // Build the workflow config object from form state
    const workflowConfig = {
      name: workflowName,
      type: "linear_workflow" as const,
      steps: workflowSteps.map(step => step.agent), // Convert UI format to API format
      description: workflowDescription || undefined
    };

    if (editMode && workflowNameParam) {
      // Edit mode - update existing workflow using PUT method
      updateWorkflow.mutate({
        filename: workflowNameParam,
        config: workflowConfig
      }, {
        onSuccess: () => {
          // Invalidate workflow config cache to force fresh data load
          queryClient.invalidateQueries({
            queryKey: ['workflow-config-by-name', workflowNameParam]
          });

          navigate('/workflows');
        },
        onError: (error) => {
          console.error('❌ Failed to update workflow:', error);
        }
      });
    } else {
      // Create mode - create new workflow using POST method
      createWorkflow.mutate(workflowConfig, {
        onSuccess: () => {
          navigate('/workflows');
        },
        onError: (error) => {
          console.error('❌ Failed to create workflow:', error);
        }
      });
    }
  };

  const handleDelete = () => {
    setShowWorkflowDeleteConfirmation(true);
  };

  const confirmDelete = () => {
    if (workflowNameParam) {
      deleteWorkflow.mutate(workflowNameParam, {
        onSuccess: () => {
          setShowWorkflowDeleteConfirmation(false);
          navigate('/workflows');
        }
      });
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Main Content */}
      <div className="flex-1 flex flex-col relative">
        {/* Main Content Area */}
        <main className="flex-1 flex flex-col px-6 pt-12 pb-8">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="w-full max-w-4xl mx-auto space-y-8"
          >
            {/* Header */}
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate('/workflows')}
                className="w-9 h-9"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <h1 className="text-3xl font-bold text-primary">
                {editMode ? 'Edit Linear Workflow' : 'Build New Linear Workflow'}
              </h1>
            </div>

            {/* Workflow Details Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              {/* Loading State for Workflow Config */}
              {workflowConfigLoading && editMode && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading workflow configuration...
                </div>
              )}

              {/* Workflow Name */}
              <div className="space-y-2">
                <Label htmlFor="workflow-name" className="text-sm font-medium text-foreground">Workflow Name</Label>
                <Input
                  id="workflow-name"
                  placeholder="e.g., Daily Briefing Workflow"
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  className="text-base"
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="workflow-description" className="text-sm font-medium text-foreground">Description (Optional)</Label>
                <Textarea
                  id="workflow-description"
                  placeholder="A brief description of what this workflow does."
                  value={workflowDescription}
                  onChange={(e) => setWorkflowDescription(e.target.value)}
                  className="min-h-[100px] resize-none"
                />
              </div>
            </motion.div>

            {/* Workflow Steps Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-primary">Workflow Steps (Agent Sequence)</h2>
              </div>

              {workflowSteps.length === 0 ? (
                <p className="text-sm text-muted-foreground">No steps added yet.</p>
              ) : (
                <div className="space-y-2">
                  {workflowSteps.map((step, index) => (
                    <div key={step.id} className="flex items-center justify-between gap-2 p-3 bg-muted/20 rounded-md border border-border hover:bg-muted/30 transition-colors">
                      <span className="text-sm font-medium">{index + 1}. {step.agent}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeWorkflowStep(step.id)}
                        className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                        aria-label={`Remove step ${index + 1}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-2">
                <Select value={selectedAgentToAdd} onValueChange={setSelectedAgentToAdd}>
                  <SelectTrigger className="flex-1">
                    <SelectValue placeholder="Select an agent to add..." />
                  </SelectTrigger>
                  <SelectContent>
                    {agentsLoading ? (
                      <SelectItem value="__loading__" disabled>
                        <div className="flex items-center gap-2">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Loading agents...
                        </div>
                      </SelectItem>
                    ) : agents.length === 0 ? (
                      <SelectItem value="__no_agents__" disabled>
                        No agents available
                      </SelectItem>
                    ) : (
                      agents.map((agent, index) => {
                        const agentName = extractAgentName(agent);
                        return (
                          <SelectItem key={`${agentName}-${index}`} value={agentName}>
                            {agentName}
                          </SelectItem>
                        );
                      })
                    )}
                  </SelectContent>
                </Select>
                <Button
                  onClick={addWorkflowStep}
                  variant="outline"
                  disabled={!selectedAgentToAdd}
                >
                  Add Step
                </Button>
              </div>
            </motion.div>

            {/* Action Buttons */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="flex justify-between"
            >
              {/* Delete Button - Only show in edit mode */}
              {editMode && (
                <Button
                  variant="destructive"
                  className="px-6"
                  onClick={handleDelete}
                  disabled={deleteWorkflow.isPending}
                >
                  {deleteWorkflow.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Deleting...
                    </>
                  ) : (
                    'Delete Workflow'
                  )}
                </Button>
              )}

              {/* Spacer for alignment when no delete button */}
              {!editMode && <div />}

              <Button
                className="px-8"
                onClick={handleSubmit}
                disabled={(updateWorkflow.isPending || createWorkflow.isPending) || !workflowName.trim() || workflowSteps.length === 0}
              >
                {(updateWorkflow.isPending || createWorkflow.isPending) ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    {editMode ? 'Updating...' : 'Creating...'}
                  </>
                ) : (
                  editMode ? 'Update Linear Workflow' : 'Save Linear Workflow'
                )}
              </Button>
            </motion.div>
          </motion.div>
        </main>
      </div>

      {/* Workflow Delete Confirmation Dialog */}
      {showWorkflowDeleteConfirmation && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowWorkflowDeleteConfirmation(false)}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-card border border-border rounded-lg p-6 max-w-md mx-4 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-foreground">
              Delete Workflow
            </h3>
            <p className="text-sm text-muted-foreground">
              Are you sure you want to delete the workflow "{workflowName}"? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowWorkflowDeleteConfirmation(false)}
                disabled={deleteWorkflow.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={confirmDelete}
                disabled={deleteWorkflow.isPending}
              >
                {deleteWorkflow.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Deleting...
                  </>
                ) : (
                  'Delete'
                )}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
}
