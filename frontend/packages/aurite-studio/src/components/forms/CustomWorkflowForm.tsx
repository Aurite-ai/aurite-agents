import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { FilePicker } from '@/components/ui/FilePicker';
import { useCustomWorkflowConfigByName, useUpdateCustomWorkflow, useDeleteCustomWorkflow, useCreateCustomWorkflow } from '@/hooks/useWorkflows';

interface CustomWorkflowFormProps {
  editMode?: boolean;
}

export default function CustomWorkflowForm({ editMode = false }: CustomWorkflowFormProps) {
  const navigate = useNavigate();
  const { name: workflowNameParam } = useParams<{ name: string }>();
  
  // Custom workflow form state
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [customWorkflowModulePath, setCustomWorkflowModulePath] = useState('');
  const [customWorkflowClassName, setCustomWorkflowClassName] = useState('');
  
  // Form control state
  const [customWorkflowFormPopulated, setCustomWorkflowFormPopulated] = useState(false);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);

  // API Hooks
  const { data: customWorkflowConfig, isLoading: customWorkflowConfigLoading } = useCustomWorkflowConfigByName(
    workflowNameParam || '',
    !!workflowNameParam && editMode
  );
  
  const updateCustomWorkflow = useUpdateCustomWorkflow();
  const deleteCustomWorkflow = useDeleteCustomWorkflow();
  const createCustomWorkflow = useCreateCustomWorkflow();

  // Effect to populate custom workflow form when custom workflow config is loaded
  useEffect(() => {
    if (editMode && customWorkflowConfig && workflowNameParam && !customWorkflowFormPopulated) {
      console.log('🔄 Populating custom workflow form with config:', customWorkflowConfig);
      
      // Populate custom workflow form fields
      setWorkflowName(customWorkflowConfig.name || '');
      setWorkflowDescription(customWorkflowConfig.description || '');
      setCustomWorkflowModulePath(customWorkflowConfig.module_path || '');
      setCustomWorkflowClassName(customWorkflowConfig.class_name || '');
      
      // Mark form as populated to prevent re-population
      setCustomWorkflowFormPopulated(true);
      console.log('✅ Custom workflow form populated successfully');
    } else if (editMode && workflowNameParam && !customWorkflowConfig && !customWorkflowConfigLoading) {
      console.log('❌ Failed to load custom workflow config for:', workflowNameParam);
    }
  }, [customWorkflowConfig, workflowNameParam, editMode, customWorkflowConfigLoading, customWorkflowFormPopulated]);

  // Initialize form for create mode
  useEffect(() => {
    if (!editMode && !customWorkflowFormPopulated) {
      // Reset ALL form fields to empty/default values for new custom workflow creation
      setWorkflowName('');
      setWorkflowDescription('');
      setCustomWorkflowModulePath('');
      setCustomWorkflowClassName('');
      
      // Mark form as populated to prevent re-initialization
      setCustomWorkflowFormPopulated(true);
    }
  }, [editMode, customWorkflowFormPopulated]);

  const handleSubmit = () => {
    // Build the custom workflow config object from form state
    const customWorkflowConfig = {
      name: workflowName,
      module_path: customWorkflowModulePath,
      class_name: customWorkflowClassName,
      description: workflowDescription || undefined
    };

    console.log('💾 Saving custom workflow config:', customWorkflowConfig);

    if (editMode && workflowNameParam) {
      // Edit mode - update existing custom workflow using PUT method
      updateCustomWorkflow.mutate({
        filename: workflowNameParam,
        config: customWorkflowConfig
      }, {
        onSuccess: () => {
          console.log('✅ Custom workflow updated successfully');
          navigate('/workflows');
        },
        onError: (error) => {
          console.error('❌ Failed to update custom workflow:', error);
        }
      });
    } else {
      // Create mode - create new custom workflow using POST method
      createCustomWorkflow.mutate(customWorkflowConfig, {
        onSuccess: () => {
          console.log('✅ Custom workflow created successfully');
          navigate('/workflows');
        },
        onError: (error) => {
          console.error('❌ Failed to create custom workflow:', error);
        }
      });
    }
  };

  const handleDelete = () => {
    setShowDeleteConfirmation(true);
  };

  const confirmDelete = () => {
    if (workflowNameParam) {
      deleteCustomWorkflow.mutate(workflowNameParam, {
        onSuccess: () => {
          setShowDeleteConfirmation(false);
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
                {editMode ? 'Edit Custom Workflow' : 'Create Custom Workflow'}
              </h1>
            </div>

            {/* Loading State for Custom Workflow Config */}
            {customWorkflowConfigLoading && editMode && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading custom workflow configuration...
              </div>
            )}

            {/* Basic Details Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              <h2 className="text-lg font-semibold text-primary">Basic Details</h2>
              
              {/* Workflow Name */}
              <div className="space-y-2">
                <Label htmlFor="custom-workflow-name" className="text-sm font-medium text-foreground">Workflow Name</Label>
                <Input
                  id="custom-workflow-name"
                  placeholder="e.g., Data Processing Workflow"
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  className="text-base"
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="custom-workflow-description" className="text-sm font-medium text-foreground">Description (Optional)</Label>
                <Textarea
                  id="custom-workflow-description"
                  placeholder="Brief description of what this workflow does"
                  value={workflowDescription}
                  onChange={(e) => setWorkflowDescription(e.target.value)}
                  className="min-h-[80px] resize-none"
                />
              </div>
            </motion.div>

            {/* Python Implementation Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              <h2 className="text-lg font-semibold text-primary">Python Implementation</h2>
              
              <div className="space-y-4">
                {/* Module Path with File Picker */}
                <FilePicker
                  value={customWorkflowModulePath}
                  onChange={setCustomWorkflowModulePath}
                  placeholder="Select Python workflow file..."
                  defaultDirectory="custom_workflows"
                  label="Module Path"
                />

                {/* Class Name */}
                <div className="space-y-2">
                  <Label htmlFor="class-name" className="text-sm font-medium text-foreground">Class Name *</Label>
                  <Input
                    id="class-name"
                    placeholder="e.g., DataProcessingWorkflow"
                    value={customWorkflowClassName}
                    onChange={(e) => setCustomWorkflowClassName(e.target.value)}
                    className="text-base"
                  />
                  <p className="text-xs text-muted-foreground">
                    Name of the class implementing the workflow interface
                  </p>
                </div>

                {/* Requirements Help Text */}
                <div className="p-4 bg-muted/20 rounded-lg">
                  <h4 className="font-medium text-sm mb-2">Requirements:</h4>
                  <ul className="text-xs text-muted-foreground space-y-1">
                    <li>• Class must inherit from BaseCustomWorkflow</li>
                    <li>• Implement the execute() method</li>
                    <li>• Module must be importable from the Python path</li>
                  </ul>
                </div>
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
                  disabled={deleteCustomWorkflow.isPending}
                >
                  {deleteCustomWorkflow.isPending ? (
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
                disabled={(updateCustomWorkflow.isPending || createCustomWorkflow.isPending) || !workflowName.trim() || !customWorkflowModulePath.trim() || !customWorkflowClassName.trim()}
              >
                {(updateCustomWorkflow.isPending || createCustomWorkflow.isPending) ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    {editMode ? 'Updating...' : 'Creating...'}
                  </>
                ) : (
                  editMode ? 'Update Custom Workflow' : 'Save Custom Workflow'
                )}
              </Button>
            </motion.div>
          </motion.div>
        </main>
      </div>

      {/* Delete Confirmation Dialog */}
      <AnimatePresence>
        {showDeleteConfirmation && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowDeleteConfirmation(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border rounded-lg p-6 max-w-md mx-4 space-y-4"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-foreground">
                Delete Custom Workflow
              </h3>
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete the custom workflow "{workflowName}"? This action cannot be undone.
              </p>
              <div className="flex gap-3 justify-end">
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteConfirmation(false)}
                  disabled={deleteCustomWorkflow.isPending}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={confirmDelete}
                  disabled={deleteCustomWorkflow.isPending}
                >
                  {deleteCustomWorkflow.isPending ? (
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
      </AnimatePresence>
    </div>
  );
}
