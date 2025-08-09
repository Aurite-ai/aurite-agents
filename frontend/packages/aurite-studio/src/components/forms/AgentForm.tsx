import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Loader2 } from 'lucide-react';
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
import { useAgentConfig, useUpdateAgent, useCreateAgent, useDeleteAgent } from '@/hooks/useAgents';
import { useClientsWithStatus } from '@/hooks/useClients';
import { useLLMsWithConfigs } from '@/hooks/useLLMs';

interface AgentFormProps {
  editMode?: boolean;
}

export default function AgentForm({ editMode = false }: AgentFormProps) {
  const navigate = useNavigate();
  const { name: agentNameParam } = useParams<{ name: string }>();
  const [searchParams] = useSearchParams();

  // Form state
  const [agentFormName, setAgentFormName] = useState('');
  const [agentSystemPrompt, setAgentSystemPrompt] = useState('');
  const [llmConfigOption, setLlmConfigOption] = useState('existing');
  const [selectedLLMConfig, setSelectedLLMConfig] = useState('');
  const [maxIterations, setMaxIterations] = useState('10');
  const [selectedMCPServers, setSelectedMCPServers] = useState<string[]>([]);
  const [inlineTemperature, setInlineTemperature] = useState('');
  const [inlineMaxTokens, setInlineMaxTokens] = useState('');
  const [inlineModel, setInlineModel] = useState('');
  const [formPopulated, setFormPopulated] = useState(false);
  const [showAgentDeleteConfirmation, setShowAgentDeleteConfirmation] = useState(false);
  const [deletingAgent, setDeletingAgent] = useState<any>(null);

  // Ref for auto-focus functionality
  const maxIterationsRef = useRef<HTMLInputElement>(null);

  // API Hooks
  const { data: clients = [] } = useClientsWithStatus();
  const { data: llms = [] } = useLLMsWithConfigs();

  // Agent-specific hooks
  const { data: agentConfig, isLoading: configLoading } = useAgentConfig(
    agentNameParam || '',
    !!agentNameParam && editMode
  );

  const updateAgent = useUpdateAgent();
  const createAgent = useCreateAgent();
  const deleteAgent = useDeleteAgent();

  // Effect to populate form when agent config is loaded in edit mode
  useEffect(() => {
    if (editMode && agentConfig && agentNameParam && !formPopulated) {
      // Safely extract agent name according to canonical AgentConfig model
      const safeName =
        typeof agentConfig.name === 'string'
          ? agentConfig.name
          : agentConfig.name && typeof agentConfig.name === 'object' && 'name' in agentConfig.name
            ? String((agentConfig.name as any).name)
            : String(agentConfig.name || 'Unknown Agent');

      // Populate basic form fields
      setAgentFormName(safeName);
      setAgentSystemPrompt(agentConfig.system_prompt || '');
      setSelectedMCPServers(agentConfig.mcp_servers || []);
      setMaxIterations(agentConfig.max_iterations?.toString() || '10');

      // Handle LLM configuration with improved logic
      if (agentConfig.llm_config_id) {
        // Agent uses existing LLM configuration
        setLlmConfigOption('existing');
        setSelectedLLMConfig(agentConfig.llm_config_id);

        // Clear inline fields
        setInlineModel('');
        setInlineTemperature('');
        setInlineMaxTokens('');
      } else if (
        agentConfig.model ||
        agentConfig.temperature !== undefined ||
        agentConfig.max_tokens !== undefined
      ) {
        // Agent uses inline LLM parameters
        setLlmConfigOption('inline');
        setInlineModel(agentConfig.model || '');
        setInlineTemperature(agentConfig.temperature?.toString() || '');
        setInlineMaxTokens(agentConfig.max_tokens?.toString() || '');

        // Clear existing config selection
        setSelectedLLMConfig('');
      } else {
        // No LLM configuration found - default to existing mode
        setLlmConfigOption('existing');
        setSelectedLLMConfig('');
        setInlineModel('');
        setInlineTemperature('');
        setInlineMaxTokens('');
      }

      // Mark form as populated to prevent re-population
      setFormPopulated(true);
    } else if (editMode && agentNameParam && !agentConfig && !configLoading) {
      // Failed to load agent config
    }
  }, [agentConfig, agentNameParam, editMode, configLoading, formPopulated]);

  // Initialize form for create mode
  useEffect(() => {
    if (!editMode && !formPopulated) {
      // Reset ALL form fields to empty/default values for new agent creation
      setAgentFormName('');
      setAgentSystemPrompt('');
      setSelectedMCPServers([]);
      setLlmConfigOption('existing');
      setSelectedLLMConfig('');
      setMaxIterations('10');
      setInlineTemperature('');
      setInlineMaxTokens('');
      setInlineModel('');

      // Mark form as populated to prevent re-initialization
      setFormPopulated(true);
    }
  }, [editMode, formPopulated]);

  // Auto-focus Max Iterations field when focus=max_iterations URL parameter is present
  useEffect(() => {
    const focusParam = searchParams.get('focus');
    if (focusParam === 'max_iterations' && formPopulated && maxIterationsRef.current) {
      // Small delay to ensure the form is fully rendered
      setTimeout(() => {
        maxIterationsRef.current?.focus();
        maxIterationsRef.current?.select();
        // Scroll to the field
        maxIterationsRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }, 500);
    }
  }, [searchParams, formPopulated]);

  const handleSubmit = () => {
    // Build the agent config object
    const agentConfig = {
      name: agentFormName,
      system_prompt: agentSystemPrompt,
      mcp_servers: selectedMCPServers,
      max_iterations: parseInt(maxIterations, 10) || 10,
      ...(llmConfigOption === 'existing' && selectedLLMConfig
        ? {
            llm_config_id: selectedLLMConfig,
          }
        : {}),
      ...(llmConfigOption === 'inline'
        ? {
            model: inlineModel,
            temperature: inlineTemperature ? parseFloat(inlineTemperature) : undefined,
            max_tokens: inlineMaxTokens ? parseInt(inlineMaxTokens, 10) : undefined,
          }
        : {}),
    };

    if (editMode && agentNameParam) {
      // Edit mode - update existing agent using PUT method
      updateAgent.mutate(
        {
          filename: agentNameParam,
          config: agentConfig,
        },
        {
          onSuccess: () => {
            navigate('/agents');
          },
          onError: error => {
            console.error('❌ Failed to update agent config:', error);
          },
        }
      );
    } else {
      // Create mode - create new agent using POST method
      createAgent.mutate(agentConfig, {
        onSuccess: () => {
          navigate('/agents');
        },
        onError: error => {
          console.error('❌ Failed to create agent config:', error);
        },
      });
    }
  };

  const handleDelete = () => {
    if (agentNameParam) {
      setDeletingAgent({ name: agentNameParam });
      setShowAgentDeleteConfirmation(true);
    }
  };

  const confirmDelete = () => {
    if (deletingAgent && deletingAgent.name) {
      deleteAgent.mutate(deletingAgent.name, {
        onSuccess: () => {
          setShowAgentDeleteConfirmation(false);
          setDeletingAgent(null);
          navigate('/agents');
        },
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
                onClick={() => navigate('/agents')}
                className="w-9 h-9"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <h1 className="text-3xl font-bold text-primary">
                {editMode ? 'Edit Agent' : 'Build New Agent'}
              </h1>
            </div>

            {/* Agent Details Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              {/* Loading State for Agent Config */}
              {configLoading && editMode && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading agent configuration...
                </div>
              )}

              {/* Agent Name */}
              <div className="space-y-2">
                <Label htmlFor="agent-form-name" className="text-sm font-medium text-foreground">
                  Agent Name
                </Label>
                <Input
                  id="agent-form-name"
                  placeholder="e.g., Customer Support Agent"
                  value={agentFormName}
                  onChange={e => setAgentFormName(e.target.value)}
                  className="text-base"
                />
              </div>

              {/* System Prompt */}
              <div className="space-y-2">
                <Label
                  htmlFor="agent-system-prompt"
                  className="text-sm font-medium text-foreground"
                >
                  System Prompt
                </Label>
                <Textarea
                  id="agent-system-prompt"
                  placeholder="e.g., You are a helpful assistant..."
                  value={agentSystemPrompt}
                  onChange={e => setAgentSystemPrompt(e.target.value)}
                  className="min-h-[100px] resize-none"
                />
              </div>
            </motion.div>

            {/* MCP Servers Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              <h2 className="text-lg font-semibold text-primary">MCP Servers</h2>

              {configLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading configuration...
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Selected Servers Pills */}
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-foreground">
                      Selected MCP Servers ({selectedMCPServers.length})
                    </Label>
                    {selectedMCPServers.length > 0 ? (
                      <div className="flex flex-wrap gap-2 p-3 bg-muted/20 border border-border rounded-lg min-h-[44px]">
                        {selectedMCPServers.map(server => (
                          <div
                            key={server}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground rounded-full text-sm font-medium"
                          >
                            <span>{server}</span>
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedMCPServers(selectedMCPServers.filter(s => s !== server));
                              }}
                              className="ml-1 hover:bg-primary-foreground/20 rounded-full p-0.5 transition-colors"
                              aria-label={`Remove ${server}`}
                            >
                              <svg
                                className="w-3 h-3"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M6 18L18 6M6 6l12 12"
                                />
                              </svg>
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-3 bg-muted/20 border border-border rounded-lg min-h-[44px] flex items-center">
                        <span className="text-sm text-muted-foreground">No servers selected</span>
                      </div>
                    )}
                  </div>

                  {/* Available Servers */}
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-foreground">
                      Available MCP Servers
                    </Label>
                    <div className="space-y-2">
                      {clients.map(client => {
                        const isSelected = selectedMCPServers.includes(client.name);
                        const isConnected = client.status === 'connected';

                        return (
                          <button
                            key={client.name}
                            type="button"
                            onClick={() => {
                              if (isConnected) {
                                if (isSelected) {
                                  setSelectedMCPServers(
                                    selectedMCPServers.filter(s => s !== client.name)
                                  );
                                } else {
                                  setSelectedMCPServers([...selectedMCPServers, client.name]);
                                }
                              }
                            }}
                            disabled={!isConnected}
                            className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all duration-200 text-left ${
                              isSelected
                                ? 'bg-primary/10 border-primary text-primary'
                                : isConnected
                                  ? 'bg-card border-border hover:bg-accent hover:border-accent-foreground/20'
                                  : 'bg-muted/50 border-border opacity-60 cursor-not-allowed'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <div
                                className={`w-4 h-4 rounded border-2 flex items-center justify-center ${
                                  isSelected
                                    ? 'bg-primary border-primary'
                                    : 'border-muted-foreground'
                                }`}
                              >
                                {isSelected && (
                                  <svg
                                    className="w-2.5 h-2.5 text-primary-foreground"
                                    fill="currentColor"
                                    viewBox="0 0 20 20"
                                  >
                                    <path
                                      fillRule="evenodd"
                                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                      clipRule="evenodd"
                                    />
                                  </svg>
                                )}
                              </div>
                              <span className="text-sm font-medium">{client.name}</span>
                            </div>
                            <span
                              className={`text-xs px-2 py-1 rounded-full ${
                                isConnected
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                  : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                              }`}
                            >
                              {client.status}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </motion.div>

            {/* LLM Configuration Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              <h2 className="text-lg font-semibold text-primary">LLM Configuration</h2>

              <div className="space-y-4">
                {/* Toggle Button Group */}
                <div className="p-1 bg-muted/20 border border-border rounded-lg">
                  <div className="flex gap-1">
                    <Button
                      type="button"
                      variant={llmConfigOption === 'existing' ? 'default' : 'ghost'}
                      size="sm"
                      onClick={() => setLlmConfigOption('existing')}
                      className="flex-1 transition-all duration-200 text-sm"
                    >
                      Use Existing LLM Config
                    </Button>
                    <Button
                      type="button"
                      variant={llmConfigOption === 'inline' ? 'default' : 'ghost'}
                      size="sm"
                      onClick={() => setLlmConfigOption('inline')}
                      className="flex-1 transition-all duration-200 text-sm"
                    >
                      Define Inline LLM Parameters
                    </Button>
                  </div>
                </div>
              </div>

              {llmConfigOption === 'existing' && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-foreground">Select LLM Config</Label>
                  <Select value={selectedLLMConfig} onValueChange={setSelectedLLMConfig}>
                    <SelectTrigger>
                      <SelectValue placeholder="-- Select LLM Config --" />
                    </SelectTrigger>
                    <SelectContent>
                      {llms.map(config => {
                        // Safely extract LLM config ID
                        const configId =
                          typeof config.id === 'string'
                            ? config.id
                            : config.id && typeof config.id === 'object' && 'name' in config.id
                              ? String((config.id as any).name)
                              : String(config.id || 'unknown_config');

                        return (
                          <SelectItem key={configId} value={configId}>
                            {configId}
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {llmConfigOption === 'inline' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-foreground">Model</Label>
                      <Input
                        placeholder="e.g., gpt-4, claude-3-opus"
                        value={inlineModel}
                        onChange={e => setInlineModel(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-foreground">Max Tokens</Label>
                      <Input
                        type="number"
                        min="1"
                        max="32768"
                        placeholder="2048"
                        value={inlineMaxTokens}
                        onChange={e => setInlineMaxTokens(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-foreground">
                      Temperature: {inlineTemperature || '0.7'}
                    </Label>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={inlineTemperature || '0.7'}
                      onChange={e => setInlineTemperature(e.target.value)}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Focused (0.0)</span>
                      <span>Balanced (1.0)</span>
                      <span>Creative (2.0)</span>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>

            {/* Other Parameters Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              <h2 className="text-lg font-semibold text-primary">Other Parameters</h2>

              <div className="space-y-2">
                <Label htmlFor="max-iterations" className="text-sm font-medium text-foreground">
                  Max Iterations: {maxIterations}
                </Label>
                <input
                  id="max-iterations"
                  ref={maxIterationsRef}
                  type="range"
                  min="1"
                  max="100"
                  step="1"
                  value={maxIterations}
                  onChange={e => setMaxIterations(e.target.value)}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Quick (1)</span>
                  <span>Moderate (50)</span>
                  <span>Extended (100)</span>
                </div>
              </div>
            </motion.div>

            {/* Action Buttons */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="flex justify-between"
            >
              {/* Delete Button - Only show in edit mode */}
              {editMode && (
                <Button
                  variant="destructive"
                  className="px-6"
                  onClick={handleDelete}
                  disabled={deleteAgent.isPending}
                >
                  {deleteAgent.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Deleting...
                    </>
                  ) : (
                    'Delete Agent'
                  )}
                </Button>
              )}

              {/* Spacer for alignment when no delete button */}
              {!editMode && <div />}

              <Button
                className="px-8"
                onClick={handleSubmit}
                disabled={updateAgent.isPending || createAgent.isPending || !agentFormName}
              >
                {updateAgent.isPending || createAgent.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    {editMode ? 'Updating...' : 'Creating...'}
                  </>
                ) : editMode ? (
                  'Update Agent Config'
                ) : (
                  'Create Agent Config'
                )}
              </Button>
            </motion.div>
          </motion.div>
        </main>
      </div>

      {/* Agent Delete Confirmation Dialog */}
      {showAgentDeleteConfirmation && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowAgentDeleteConfirmation(false)}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-card border border-border rounded-lg p-6 max-w-md mx-4 space-y-4"
            onClick={e => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-foreground">Delete Agent</h3>
            <p className="text-sm text-muted-foreground">
              Are you sure you want to delete the agent "{deletingAgent?.name}"? This action cannot
              be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setShowAgentDeleteConfirmation(false);
                  setDeletingAgent(null);
                }}
                disabled={deleteAgent.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={confirmDelete}
                disabled={deleteAgent.isPending}
              >
                {deleteAgent.isPending ? (
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
