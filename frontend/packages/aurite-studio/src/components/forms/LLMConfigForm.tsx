import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { useLLMConfig, useUpdateLLM, useCreateLLM, useDeleteLLM } from '@/hooks/useLLMs';

interface LLMConfigFormProps {
  editMode?: boolean;
}

export default function LLMConfigForm({ editMode = false }: LLMConfigFormProps) {
  const navigate = useNavigate();
  const { name: llmNameParam } = useParams<{ name: string }>();
  
  // Form state
  const [llmId, setLlmId] = useState('');
  const [llmProvider, setLlmProvider] = useState('');
  const [llmModelName, setLlmModelName] = useState('');
  const [llmTemperature, setLlmTemperature] = useState('');
  const [llmMaxTokens, setLlmMaxTokens] = useState('');
  const [llmSystemPrompt, setLlmSystemPrompt] = useState('');
  const [llmApiKeyEnvVar, setLlmApiKeyEnvVar] = useState('');
  const [formPopulated, setFormPopulated] = useState(false);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);

  // API Hooks
  const { data: llmConfig, isLoading: llmConfigLoading } = useLLMConfig(
    llmNameParam || '',
    !!llmNameParam && editMode
  );
  
  const updateLLM = useUpdateLLM();
  const createLLM = useCreateLLM();
  const deleteLLM = useDeleteLLM();

  // Effect to populate LLM form when LLM config is loaded
  useEffect(() => {
    if (editMode && llmConfig && llmNameParam && !formPopulated) {
      console.log('🔄 Populating LLM form with config:', llmConfig);
      
      setLlmId(llmConfig.name || '');
      setLlmProvider(llmConfig.provider || '');
      setLlmModelName(llmConfig.model || '');
      setLlmTemperature(llmConfig.temperature?.toString() || '');
      setLlmMaxTokens(llmConfig.max_tokens?.toString() || '');
      setLlmSystemPrompt(llmConfig.default_system_prompt || '');
      setLlmApiKeyEnvVar(llmConfig.api_key_env_var || '');
      
      // Mark form as populated to prevent re-population
      setFormPopulated(true);
      console.log('✅ LLM form populated successfully');
    } else if (editMode && llmNameParam && !llmConfig && !llmConfigLoading) {
      console.log('❌ Failed to load LLM config for:', llmNameParam);
    }
  }, [llmConfig, llmNameParam, editMode, llmConfigLoading, formPopulated]);

  // Initialize form for create mode
  useEffect(() => {
    if (!editMode && !formPopulated) {
      // Reset ALL form fields to empty/default values for new LLM creation
      setLlmId('');
      setLlmProvider('');
      setLlmModelName('');
      setLlmTemperature('');
      setLlmMaxTokens('');
      setLlmSystemPrompt('');
      setLlmApiKeyEnvVar('');
      
      // Mark form as populated to prevent re-initialization
      setFormPopulated(true);
    }
  }, [editMode, formPopulated]);

  const handleSubmit = () => {
    // Build the LLM config object
    const llmConfig: any = {
      name: llmId,
      type: 'llm',
    };

    // Only include fields that have values
    if (llmProvider) llmConfig.provider = llmProvider;
    if (llmModelName) llmConfig.model = llmModelName;
    if (llmTemperature) llmConfig.temperature = parseFloat(llmTemperature);
    if (llmMaxTokens) llmConfig.max_tokens = parseInt(llmMaxTokens);
    if (llmSystemPrompt) llmConfig.default_system_prompt = llmSystemPrompt;
    if (llmApiKeyEnvVar) llmConfig.api_key_env_var = llmApiKeyEnvVar;

    console.log('💾 Saving LLM config:', llmConfig);

    if (editMode && llmNameParam) {
      // Edit mode - update existing LLM configuration
      updateLLM.mutate({
        filename: llmNameParam,
        config: llmConfig
      }, {
        onSuccess: () => {
          console.log('✅ LLM config updated successfully');
          navigate('/llm-configs');
        },
        onError: (error) => {
          console.error('❌ Failed to update LLM config:', error);
        }
      });
    } else {
      // Create mode - create new LLM configuration
      createLLM.mutate(llmConfig, {
        onSuccess: () => {
          console.log('✅ New LLM config created successfully');
          navigate('/llm-configs');
        },
        onError: (error) => {
          console.error('❌ Failed to create LLM config:', error);
        }
      });
    }
  };

  const handleDelete = () => {
    setShowDeleteConfirmation(true);
  };

  const confirmDelete = () => {
    if (llmNameParam) {
      deleteLLM.mutate(llmNameParam, {
        onSuccess: () => {
          setShowDeleteConfirmation(false);
          navigate('/llm-configs');
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
                onClick={() => navigate('/llm-configs')}
                className="w-9 h-9"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <h1 className="text-3xl font-bold text-primary">
                {editMode ? 'Edit LLM Configuration' : 'Build New LLM Configuration'}
              </h1>
            </div>

            {/* LLM Configuration Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              {/* Loading State for LLM Config */}
              {llmConfigLoading && editMode && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading LLM configuration...
                </div>
              )}

              {/* LLM Name */}
              <div className="space-y-2">
                <Label htmlFor="llm-name" className="text-sm font-medium text-foreground">LLM Name *</Label>
                <Input
                  id="llm-name"
                  placeholder="e.g., my_claude_opus_config"
                  value={llmId}
                  onChange={(e) => setLlmId(e.target.value)}
                  className="text-base"
                />
              </div>

              {/* Provider */}
              <div className="space-y-2">
                <Label htmlFor="provider" className="text-sm font-medium text-foreground">Provider (Optional)</Label>
                <Input
                  id="provider"
                  placeholder="e.g., anthropic, openai, google"
                  value={llmProvider}
                  onChange={(e) => setLlmProvider(e.target.value)}
                  className="text-base"
                />
              </div>

              {/* Model Name */}
              <div className="space-y-2">
                <Label htmlFor="model-name" className="text-sm font-medium text-foreground">Model Name (Optional)</Label>
                <Input
                  id="model-name"
                  placeholder="e.g., claude-3-opus-20240229, gpt-4-turbo"
                  value={llmModelName}
                  onChange={(e) => setLlmModelName(e.target.value)}
                  className="text-base"
                />
              </div>

              {/* Temperature and Max Tokens Row */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Temperature */}
                <div className="space-y-2">
                  <Label htmlFor="temperature" className="text-sm font-medium text-foreground">Temperature (Optional)</Label>
                  <Input
                    id="temperature"
                    placeholder="e.g., 0.7 (0.0 to 2.0)"
                    value={llmTemperature}
                    onChange={(e) => setLlmTemperature(e.target.value)}
                    className="text-base"
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                  />
                </div>

                {/* Max Tokens */}
                <div className="space-y-2">
                  <Label htmlFor="max-tokens" className="text-sm font-medium text-foreground">Max Tokens (Optional)</Label>
                  <Input
                    id="max-tokens"
                    placeholder="e.g., 2048"
                    value={llmMaxTokens}
                    onChange={(e) => setLlmMaxTokens(e.target.value)}
                    className="text-base"
                    type="number"
                  />
                </div>
              </div>

              {/* API Key Environment Variable */}
              <div className="space-y-2">
                <Label htmlFor="api-key-env-var" className="text-sm font-medium text-foreground">API Key Environment Variable (Optional)</Label>
                <Input
                  id="api-key-env-var"
                  placeholder="e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY"
                  value={llmApiKeyEnvVar}
                  onChange={(e) => setLlmApiKeyEnvVar(e.target.value)}
                  className="text-base"
                />
              </div>

              {/* Default System Prompt */}
              <div className="space-y-2">
                <Label htmlFor="system-prompt" className="text-sm font-medium text-foreground">Default System Prompt (Optional)</Label>
                <Textarea
                  id="system-prompt"
                  placeholder="Enter a default system prompt for this LLM configuration."
                  value={llmSystemPrompt}
                  onChange={(e) => setLlmSystemPrompt(e.target.value)}
                  className="min-h-[100px] resize-none"
                />
              </div>
            </motion.div>

            {/* Action Buttons */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="flex justify-between"
            >
              {/* Delete Button - Only show in edit mode */}
              {editMode && (
                <Button 
                  variant="destructive"
                  className="px-6"
                  onClick={handleDelete}
                  disabled={deleteLLM.isPending}
                >
                  {deleteLLM.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Deleting...
                    </>
                  ) : (
                    'Delete LLM Config'
                  )}
                </Button>
              )}
              
              {/* Spacer for alignment when no delete button */}
              {!editMode && <div />}
              
              <Button 
                className="px-8"
                onClick={handleSubmit}
                disabled={(updateLLM.isPending || createLLM.isPending) || !llmId.trim()}
              >
                {(updateLLM.isPending || createLLM.isPending) ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    {editMode ? 'Updating...' : 'Creating...'}
                  </>
                ) : (
                  editMode ? 'Update LLM Config' : 'Create LLM Config'
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
                Delete LLM Configuration
              </h3>
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete the LLM configuration "{llmId}"? This action cannot be undone.
              </p>
              <div className="flex gap-3 justify-end">
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteConfirmation(false)}
                  disabled={deleteLLM.isPending}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={confirmDelete}
                  disabled={deleteLLM.isPending}
                >
                  {deleteLLM.isPending ? (
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
