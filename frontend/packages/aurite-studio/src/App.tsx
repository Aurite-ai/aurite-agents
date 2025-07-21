import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Home, Users, Workflow, Database, Cloud, Sparkles, Link, Wand2, Sun, Moon, Plus, Edit, Play, ArrowLeft, Loader2, Trash2, Check } from 'lucide-react';
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
import { Checkbox } from '@/components/ui/checkbox';
import { useTheme } from '@/contexts/ThemeContext';
import { Logo } from '@/components/Logo';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { useAgentsWithConfigs, useExecuteAgent, useAgentConfig, useUpdateAgent, useCreateAgent, useDeleteAgent } from '@/hooks/useAgents';
import { useWorkflowsWithConfigs, useCustomWorkflowsWithConfigs, useWorkflowConfigByName, useUpdateWorkflow, useDeleteWorkflow, useCreateWorkflow, useExecuteWorkflow, useExecuteCustomWorkflow, useCustomWorkflowConfigByName, useUpdateCustomWorkflow, useDeleteCustomWorkflow } from '@/hooks/useWorkflows';
import { useQueryClient } from '@tanstack/react-query';
import workflowsService from '@/services/workflows.service';
import toast from 'react-hot-toast';
import { useClientsWithStatus, useClientConfig, useUpdateClient, useCreateMCPServer, useRegisterMCPServer, useUnregisterMCPServer, useClientConfigComplete, useDeleteClient } from '@/hooks/useClients';
import { useLLMsWithConfigs, useLLMConfig, useUpdateLLM, useCreateLLM, useDeleteLLM } from '@/hooks/useLLMs';
import { MCPClientCard } from '@/components/MCPClientCard';
import { UnifiedExecutionInterface } from '@/components/execution/UnifiedExecutionInterface';
import { UnifiedWorkflowExecutionInterface } from '@/components/execution/UnifiedWorkflowExecutionInterface';
import { AgentConfig, WorkflowConfig } from '@/types/execution';

const sidebarItems = [
  { icon: Home, label: 'Home', id: 'home' },
  { icon: Users, label: 'All Agents', id: 'agents' },
  { icon: Workflow, label: 'Workflows', id: 'workflows' },
];

const configItems = [
  { icon: Database, label: 'MCP Clients', id: 'mcp' },
  { icon: Cloud, label: 'LLM Configs', id: 'llm' },
];

const mcpClients = [
  'Weather API',
  'Web Search', 
  'File System',
  'Database'
];

const quickActions = [
  'Build a data analysis agent',
  'Create a customer service bot',
  'Make a content generation assistant',
  'Build a code review agent'
];


const sampleLLMConfigs = [
  {
    id: 1,
    name: 'GPT-4',
    description: 'OpenAI GPT-4 model configuration with custom parameters',
    provider: 'OpenAI',
    status: 'active'
  },
  {
    id: 2,
    name: 'Claude 3',
    description: 'Anthropic Claude 3 model with optimized settings for reasoning',
    provider: 'Anthropic',
    status: 'active'
  },
  {
    id: 3,
    name: 'Llama 2',
    description: 'Meta Llama 2 model running on local infrastructure',
    provider: 'Meta',
    status: 'inactive'
  }
];

function App() {
  const [agentName, setAgentName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [sidebarHovered, setSidebarHovered] = useState(false);
  const [activeTab, setActiveTab] = useState('home');
  const [showWorkflowForm, setShowWorkflowForm] = useState(false);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [workflowSteps, setWorkflowSteps] = useState<Array<{id: number, agent: string}>>([]);
  const [selectedAgentToAdd, setSelectedAgentToAdd] = useState('');
  const [showMCPForm, setShowMCPForm] = useState(false);
  // Enhanced MCP form state for full schema support
  const [mcpClientId, setMcpClientId] = useState('');
  const [mcpDescription, setMcpDescription] = useState('');
  const [mcpTransportType, setMcpTransportType] = useState<'stdio' | 'http_stream' | 'local'>('stdio');
  const [mcpCapabilities, setMcpCapabilities] = useState('');
  const [mcpTimeout, setMcpTimeout] = useState('');
  const [mcpRegistrationTimeout, setMcpRegistrationTimeout] = useState('');
  const [mcpRoutingWeight, setMcpRoutingWeight] = useState('');
  
  // Stdio transport fields
  const [mcpServerPath, setMcpServerPath] = useState('');
  
  // HTTP stream transport fields
  const [mcpHttpEndpoint, setMcpHttpEndpoint] = useState('');
  const [mcpHeaders, setMcpHeaders] = useState<Array<{key: string; value: string}>>([]);
  
  // Local transport fields
  const [mcpCommand, setMcpCommand] = useState('');
  const [mcpArgs, setMcpArgs] = useState<string[]>([]);
  const [showLLMForm, setShowLLMForm] = useState(false);
  const [llmId, setLlmId] = useState('');
  const [llmProvider, setLlmProvider] = useState('');
  const [llmModelName, setLlmModelName] = useState('');
  const [llmTemperature, setLlmTemperature] = useState('');
  const [llmMaxTokens, setLlmMaxTokens] = useState('');
  const [llmSystemPrompt, setLlmSystemPrompt] = useState('');
  const [llmApiKeyEnvVar, setLlmApiKeyEnvVar] = useState('');
  const [showLLMEditForm, setShowLLMEditForm] = useState(false);
  const [editingLLM, setEditingLLM] = useState<any>(null);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);
  const [showMCPDeleteConfirmation, setShowMCPDeleteConfirmation] = useState(false);
  const [showAgentDeleteConfirmation, setShowAgentDeleteConfirmation] = useState(false);
  const [deletingAgent, setDeletingAgent] = useState<any>(null);
  const [isCreatingLLM, setIsCreatingLLM] = useState(false);
  const [showAgentForm, setShowAgentForm] = useState(false);
  const [editingAgent, setEditingAgent] = useState<any>(null);
  const [editingMCPClient, setEditingMCPClient] = useState<any>(null);
  const [agentFormName, setAgentFormName] = useState('');
  const [agentSystemPrompt, setAgentSystemPrompt] = useState('');
  const [llmConfigOption, setLlmConfigOption] = useState('existing');
  const [selectedLLMConfig, setSelectedLLMConfig] = useState('');
  const [maxIterations, setMaxIterations] = useState('10');
  const [selectedMCPServers, setSelectedMCPServers] = useState<string[]>([]);
  const [selectedLandingMCPServers, setSelectedLandingMCPServers] = useState<string[]>([]);
  const [agentConfigLoading, setAgentConfigLoading] = useState(false);
  const [inlineTemperature, setInlineTemperature] = useState('');
  const [inlineMaxTokens, setInlineMaxTokens] = useState('');
  const [inlineModel, setInlineModel] = useState('');
  const [formPopulated, setFormPopulated] = useState(false);
  
  // Workflow edit state - similar to LLM edit pattern
  const [editingWorkflow, setEditingWorkflow] = useState<any>(null);
  const [showWorkflowDeleteConfirmation, setShowWorkflowDeleteConfirmation] = useState(false);
  const [workflowFormPopulated, setWorkflowFormPopulated] = useState(false);
  
  // Execution Interface State
  const [executionInterface, setExecutionInterface] = useState<{
    isOpen: boolean;
    agentName: string | null;
  }>({ isOpen: false, agentName: null });
  
  // Workflow Execution Interface State
  const [workflowExecutionInterface, setWorkflowExecutionInterface] = useState<{
    isOpen: boolean;
    workflow: WorkflowConfig | null;
  }>({ isOpen: false, workflow: null });
  // Custom workflow edit state
  const [showCustomWorkflowForm, setShowCustomWorkflowForm] = useState(false);
  const [customWorkflowModulePath, setCustomWorkflowModulePath] = useState('');
  const [customWorkflowClassName, setCustomWorkflowClassName] = useState('');
  const [customWorkflowFormPopulated, setCustomWorkflowFormPopulated] = useState(false);
  
  const { theme, toggleTheme } = useTheme();

  // API Hooks - must be at component level
  const { data: agents = [], isLoading: agentsLoading } = useAgentsWithConfigs();
  const executeAgent = useExecuteAgent();
  const updateAgent = useUpdateAgent();
  const createAgent = useCreateAgent();
  const deleteAgent = useDeleteAgent();
  const { data: clients = [], isLoading: clientsLoading } = useClientsWithStatus();
  const { data: llms = [], isLoading: llmsLoading } = useLLMsWithConfigs();
  const { data: workflows = [], isLoading: workflowsLoading } = useWorkflowsWithConfigs();
  const { data: customWorkflows = [], isLoading: customWorkflowsLoading } = useCustomWorkflowsWithConfigs();
  
  // Hook for fetching agent config - use agent name directly
  const { data: agentConfig, isLoading: configLoading } = useAgentConfig(
    editingAgent?.name || '',
    !!editingAgent?.name && showAgentForm
  );

  // Hook for fetching LLM config - only enabled when we have an LLM ID and are in edit mode
  const { data: llmConfig, isLoading: llmConfigLoading } = useLLMConfig(
    editingLLM?.id || '',
    !!editingLLM?.id && (showLLMEditForm || showLLMForm)
  );

  // Hook for updating LLM configuration
  const updateLLM = useUpdateLLM();
  
  // Hook for creating LLM configuration
  const createLLM = useCreateLLM();
  
  // Hook for deleting LLM configuration
  const deleteLLM = useDeleteLLM();

  // Hook for fetching MCP client config - only enabled when we have a server name
  const { data: mcpClientConfig, isLoading: mcpClientConfigLoading } = useClientConfig(
    editingMCPClient?.name || '',
    !!editingMCPClient?.name && showMCPForm
  );

  // Hook for fetching workflow config - only enabled when we have a workflow name and are in edit mode
  const { data: workflowConfig, isLoading: workflowConfigLoading } = useWorkflowConfigByName(
    editingWorkflow?.name || '',
    !!editingWorkflow?.name && showWorkflowForm && editingWorkflow?.type !== 'custom_workflow'
  );

  // Hook for updating MCP client configuration
  const updateMCPClient = useUpdateClient();
  
  // Hook for creating new MCP server configuration
  const createMCPServer = useCreateMCPServer();
  
  // Hooks for register/unregister MCP servers
  const registerMCPServer = useRegisterMCPServer();
  const unregisterMCPServer = useUnregisterMCPServer();
  
  // Hook for deleting MCP client configuration
  const deleteMCPClient = useDeleteClient();

  // Workflow mutation hooks
  const createWorkflow = useCreateWorkflow();
  const updateWorkflow = useUpdateWorkflow();
  const deleteWorkflow = useDeleteWorkflow();
  const executeWorkflow = useExecuteWorkflow();
  const executeCustomWorkflow = useExecuteCustomWorkflow();
  
  // Custom workflow hooks
  const { data: customWorkflowConfig, isLoading: customWorkflowConfigLoading } = useCustomWorkflowConfigByName(
    editingWorkflow?.name || '',
    !!editingWorkflow?.name && showCustomWorkflowForm && editingWorkflow?.type === 'custom_workflow'
  );
  const updateCustomWorkflow = useUpdateCustomWorkflow();
  const deleteCustomWorkflow = useDeleteCustomWorkflow();
  
  // Query client for cache invalidation
  const queryClient = useQueryClient();

  // Show advanced options when user starts typing description
  React.useEffect(() => {
    if (description.trim().length > 10 && !showAdvancedOptions) {
      setShowAdvancedOptions(true);
    }
  }, [description, showAdvancedOptions]);

  const addWorkflowStep = () => {
    if (selectedAgentToAdd) {
      setWorkflowSteps([...workflowSteps, { id: Date.now(), agent: selectedAgentToAdd }]);
      setSelectedAgentToAdd(''); // Reset selection after adding
    }
  };

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

  const removeWorkflowStep = (stepId: number) => {
    setWorkflowSteps(workflowSteps.filter(step => step.id !== stepId));
  };

  const renderHomeContent = () => (
    <div className="w-full h-full flex flex-col">
      {/* Announcement Banner - Positioned at very top */}
      <motion.div
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="flex justify-center pt-32 pb-4"
      >
        <motion.div
          whileHover={{ scale: 1.02 }}
          className="relative overflow-hidden bg-gradient-to-r from-purple-600/20 via-pink-600/20 to-purple-600/20 border border-purple-500/30 rounded-full px-4 py-2 cursor-pointer group"
        >
          {/* Sparkle Animation Background */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 ease-out" />
          
          {/* Content */}
          <div className="relative flex items-center justify-center gap-2 text-xs font-medium">
            <motion.span
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              className="text-sm"
            >
              🎉
            </motion.span>
            <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              The Future of Work is Agent-Powered!
            </span>
            <motion.span
              animate={{ x: [0, 2, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              className="text-purple-400 text-sm"
            >
              {/* → */}
            </motion.span>
          </div>
          
          {/* Glow Effect */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-r from-purple-600/20 to-pink-600/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        </motion.div>
      </motion.div>

      {/* Main Content - Centered */}
      <motion.div
        initial={{ y: 50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="flex-1 flex items-center justify-center"
      >
        <div className="w-full max-w-2xl mx-auto text-center space-y-8">
          {/* Main Heading */}
          <div className="space-y-3">
            <motion.h1 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-4xl md:text-5xl font-bold tracking-tight"
            >
              What's Your Dream AI Agent?
            </motion.h1>
            <motion.p 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="text-lg text-muted-foreground"
            >
              Create intelligent AI agents by describing what you need.
            </motion.p>
          </div>

          {/* Main Input */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="relative"
          >
            <Textarea
              placeholder="Describe your AI agent... (e.g., 'I need an agent that can analyze customer feedback and generate insights')"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="min-h-[136px] text-base p-4 border border-border focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background focus:border-primary transition-all duration-200 rounded-lg resize-none gradient-card gradient-glow"
            />
            <div className="absolute bottom-3 left-3 flex items-center gap-2 text-muted-foreground">
              <Link className="h-3.5 w-3.5" />
              <Wand2 className="h-3.5 w-3.5" />
            </div>
          </motion.div>

          {/* Quick Action Buttons */}
          {!showAdvancedOptions && (
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="space-y-3"
            >
              <p className="text-sm text-muted-foreground">or try one of these:</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {quickActions.map((action, index) => (
                  <motion.button
                    key={action}
                    initial={{ y: 10, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.6 + index * 0.1 }}
                    onClick={() => setDescription(action)}
                    className="p-2.5 text-left border border-gray-300 dark:border-border rounded-md hover:ring-2 hover:ring-primary hover:ring-offset-2 hover:ring-offset-background hover:border-primary hover:bg-accent transition-all duration-200 text-sm bg-card/30"
                  >
                    {action}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Advanced Options - Show after user types description */}
          <AnimatePresence>
            {showAdvancedOptions && (
              <motion.div
                initial={{ y: 30, opacity: 0, height: 0 }}
                animate={{ y: 0, opacity: 1, height: 'auto' }}
                exit={{ y: -30, opacity: 0, height: 0 }}
                transition={{ duration: 0.5 }}
                className="space-y-6 pt-8 border-t border-border"
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Agent Name */}
                  <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="space-y-1.5"
                  >
                    <Label htmlFor="agent-name" className="text-xs font-medium text-muted-foreground">Agent Name</Label>
                    <Input
                      id="agent-name"
                      placeholder="My AI Agent"
                      value={agentName}
                      onChange={(e) => setAgentName(e.target.value)}
                      className="h-9 text-sm transition-all duration-200"
                    />
                  </motion.div>

                  {/* LLM Model */}
                  <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="space-y-1.5"
                  >
                    <Label className="text-xs font-medium text-muted-foreground">LLM Model</Label>
                    <Select value={selectedModel} onValueChange={setSelectedModel}>
                      <SelectTrigger className="h-9 text-sm">
                        <SelectValue placeholder="Select model..." />
                      </SelectTrigger>
                      <SelectContent>
                        {llmsLoading ? (
                          <SelectItem value="" disabled>
                            <div className="flex items-center gap-2">
                              <Loader2 className="h-3 w-3 animate-spin" />
                              Loading configurations...
                            </div>
                          </SelectItem>
                        ) : llms.length === 0 ? (
                          <SelectItem value="" disabled>
                            No LLM configurations available
                          </SelectItem>
                        ) : (
                          llms.map((config) => {
                            // Safely extract LLM config ID
                            const configId = typeof config.id === 'string' 
                              ? config.id 
                              : (config.id && typeof config.id === 'object' && 'name' in config.id)
                                ? String((config.id as any).name)
                                : String(config.id || 'unknown_config');
                            
                            return (
                              <SelectItem key={configId} value={configId}>
                                {configId}
                              </SelectItem>
                            );
                          })
                        )}
                      </SelectContent>
                    </Select>
                  </motion.div>

                  {/* MCP Clients */}
                  <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="space-y-1.5"
                  >
                    <Label className="text-xs font-medium text-muted-foreground">MCP Clients</Label>
                    <Select>
                      <SelectTrigger className="h-9 text-sm">
                        <SelectValue placeholder={
                          selectedLandingMCPServers.length > 0 
                            ? `${selectedLandingMCPServers.length} servers selected`
                            : "Select servers..."
                        } />
                      </SelectTrigger>
                      <SelectContent>
                        {clientsLoading ? (
                          <div className="flex items-center gap-2 p-2">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            Loading servers...
                          </div>
                        ) : clients.length === 0 ? (
                          <div className="p-2 text-sm text-muted-foreground">
                            No MCP servers available
                          </div>
                        ) : (
                          <div className="p-2 space-y-2">
                            {clients.map((client) => (
                              <div key={client.name} className="flex items-center gap-2">
                                <Checkbox 
                                  checked={selectedLandingMCPServers.includes(client.name)}
                                  disabled={client.status !== 'connected'}
                                  onCheckedChange={(checked: boolean) => {
                                    if (checked) {
                                      setSelectedLandingMCPServers([...selectedLandingMCPServers, client.name]);
                                    } else {
                                      setSelectedLandingMCPServers(selectedLandingMCPServers.filter(s => s !== client.name));
                                    }
                                  }}
                                />
                                <span className="text-sm">{client.name}</span>
                                <span className={`text-xs px-1 py-0.5 rounded ${
                                  client.status === 'connected' 
                                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                                    : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                }`}>
                                  {client.status}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </SelectContent>
                    </Select>
                  </motion.div>
                </div>

                {/* Create Button */}
                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className="pt-2"
                >
                  <Button 
                    className="px-6 py-2 text-sm font-medium transition-all duration-200 hover:scale-105"
                    disabled={!description.trim() || createAgent.isPending}
                    onClick={() => {
                      // Build the agent config object from landing page form data
                      const agentConfig = {
                        name: agentName.trim() || 'Untitled Agent',
                        system_prompt: description.trim(),
                        description: description.trim(),
                        llm_config_id: selectedModel || undefined,
                        mcp_servers: selectedLandingMCPServers,
                        max_iterations: 10,
                        type: 'agent' as const
                      };

                      console.log('🚀 Creating agent from landing page:', agentConfig);

                      createAgent.mutate(agentConfig, {
                        onSuccess: (data) => {
                          console.log('✅ Agent created successfully:', data);
                          
                          // Reset form fields
                          setDescription('');
                          setAgentName('');
                          setSelectedModel('');
                          setSelectedLandingMCPServers([]);
                          setShowAdvancedOptions(false);
                          
                          // Navigate to agents page to show the newly created agent
                          setActiveTab('agents');
                        },
                        onError: (error) => {
                          console.error('❌ Failed to create agent:', error);
                        }
                      });
                    }}
                  >
                    {createAgent.isPending ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-3.5 w-3.5 mr-2" />
                        Create Agent
                      </>
                    )}
                  </Button>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );

  const handleEditAgent = (agent: any) => {
    // Extract the actual name from the agent object
    const agentName = typeof agent.name === 'string' ? agent.name : (typeof agent.name === 'object' ? agent.name?.name : agent.name) || 'Unknown Agent';
    
    // Reset form state
    setAgentFormName(agentName);
    setAgentSystemPrompt('');
    setSelectedMCPServers([]);
    setLlmConfigOption('existing');
    setSelectedLLMConfig('');
    setMaxIterations('10');
    setInlineTemperature('');
    setInlineMaxTokens('');
    setInlineModel('');
    
    // Reset form population flag to allow re-population
    setFormPopulated(false);
    
    // Set editing agent and show form
    setEditingAgent(agent);
    setShowAgentForm(true);
  };

  const handleNewAgent = () => {
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
    
    // Clear editing state - this is create mode, not edit mode
    setEditingAgent(null);
    
    // Mark form as populated to prevent the useEffect from trying to load config
    setFormPopulated(true);
    
    // Show the form
    setShowAgentForm(true);
  };

  const handleNewWorkflow = () => {
    // Reset ALL workflow form fields to empty/default values for new workflow creation
    setWorkflowName('');
    setWorkflowDescription('');
    setWorkflowSteps([]);
    setSelectedAgentToAdd('');
    
    // Clear editing state - this is create mode, not edit mode
    setEditingWorkflow(null);
    
    // Mark form as populated to prevent the useEffect from trying to load config
    setWorkflowFormPopulated(true);
    
    // Show the form
    setShowWorkflowForm(true);
  };

  // Effect to populate form when agent config is loaded
  React.useEffect(() => {
    if (agentConfig && editingAgent && !formPopulated) {
      console.log('🔄 Populating agent form with config:', agentConfig);
      
      // Safely extract agent name according to canonical AgentConfig model
      const safeName = typeof agentConfig.name === 'string' 
        ? agentConfig.name 
        : (agentConfig.name && typeof agentConfig.name === 'object' && 'name' in agentConfig.name)
          ? String((agentConfig.name as any).name)
          : String(agentConfig.name || 'Unknown Agent');
      
      console.log('📝 Setting form fields:', {
        name: safeName,
        system_prompt: agentConfig.system_prompt,
        mcp_servers: agentConfig.mcp_servers,
        max_iterations: agentConfig.max_iterations,
        llm_config_id: agentConfig.llm_config_id,
        model: agentConfig.model,
        temperature: agentConfig.temperature,
        max_tokens: agentConfig.max_tokens
      });
      
      // Populate basic form fields
      setAgentFormName(safeName);
      setAgentSystemPrompt(agentConfig.system_prompt || '');
      setSelectedMCPServers(agentConfig.mcp_servers || []);
      setMaxIterations(agentConfig.max_iterations?.toString() || '10');
      
      // Handle LLM configuration with improved logic
      if (agentConfig.llm_config_id) {
        // Agent uses existing LLM configuration
        console.log('✅ Using existing LLM config:', agentConfig.llm_config_id);
        setLlmConfigOption('existing');
        setSelectedLLMConfig(agentConfig.llm_config_id);
        
        // Clear inline fields
        setInlineModel('');
        setInlineTemperature('');
        setInlineMaxTokens('');
      } else if (agentConfig.model || agentConfig.temperature !== undefined || agentConfig.max_tokens !== undefined) {
        // Agent uses inline LLM parameters
        console.log('✅ Using inline LLM parameters');
        setLlmConfigOption('inline');
        setInlineModel(agentConfig.model || '');
        setInlineTemperature(agentConfig.temperature?.toString() || '');
        setInlineMaxTokens(agentConfig.max_tokens?.toString() || '');
        
        // Clear existing config selection
        setSelectedLLMConfig('');
      } else {
        // No LLM configuration found - default to existing mode
        console.log('⚠️ No LLM configuration found, defaulting to existing mode');
        setLlmConfigOption('existing');
        setSelectedLLMConfig('');
        setInlineModel('');
        setInlineTemperature('');
        setInlineMaxTokens('');
      }
      
      // Mark form as populated to prevent re-population
      setFormPopulated(true);
      console.log('✅ Agent form populated successfully');
    } else if (editingAgent && !agentConfig && !configLoading) {
      console.log('❌ Failed to load agent config for:', editingAgent);
    }
  }, [agentConfig, editingAgent, llms, configLoading, formPopulated]);

  // Effect to populate LLM form when LLM config is loaded
  React.useEffect(() => {
    if (llmConfig && editingLLM) {
      setLlmId(llmConfig.name || '');
      setLlmProvider(llmConfig.provider || '');
      setLlmModelName(llmConfig.model || '');
      setLlmTemperature(llmConfig.temperature?.toString() || '');
      setLlmMaxTokens(llmConfig.max_tokens?.toString() || '');
      setLlmSystemPrompt(llmConfig.default_system_prompt || '');
      setLlmApiKeyEnvVar(llmConfig.api_key_env_var || '');
    }
  }, [llmConfig, editingLLM]);

  // Effect to populate MCP form when MCP client config is loaded
  React.useEffect(() => {
    console.log('🔍 MCP Form Population Effect Triggered');
    console.log('mcpClientConfig:', mcpClientConfig);
    console.log('editingMCPClient:', editingMCPClient);
    
    if (mcpClientConfig && editingMCPClient) {
      console.log('✅ Both mcpClientConfig and editingMCPClient exist');
      
      // Access the nested config object - API returns { config: { ... }, name: ..., ... }
      const config = (mcpClientConfig as any).config || mcpClientConfig;
      console.log('📋 Config object to use:', config);
      console.log('📋 Full config structure:', JSON.stringify(config, null, 2));
      
      // Log each field being set with more detail
      console.log('Setting form fields:');
      console.log('- name:', config.name);
      console.log('- description:', config.description);
      console.log('- transport_type:', config.transport_type);
      console.log('- capabilities:', config.capabilities);
      console.log('- timeout:', config.timeout);
      console.log('- server_path:', config.server_path);
      
      // Try different possible field names based on the API response structure
      const name = config.name || (mcpClientConfig as any).name;
      const description = config.description;
      const transportType = config.transport_type;
      const capabilities = config.capabilities;
      const timeout = config.timeout;
      const serverPath = config.server_path;
      const httpEndpoint = config.http_endpoint;
      const command = config.command;
      const args = config.args;
      const headers = config.headers;
      const registrationTimeout = config.registration_timeout;
      const routingWeight = config.routing_weight;
      
      console.log('🔧 Processed values:');
      console.log('- processed name:', name);
      console.log('- processed description:', description);
      console.log('- processed transportType:', transportType);
      console.log('- processed capabilities:', capabilities);
      console.log('- processed timeout:', timeout);
      console.log('- processed serverPath:', serverPath);
      
      setMcpClientId(name || '');
      setMcpDescription(description || '');
      setMcpTransportType(transportType || 'stdio');
      setMcpCapabilities(Array.isArray(capabilities) ? capabilities.join(', ') : (capabilities || ''));
      setMcpTimeout(timeout?.toString() || '');
      setMcpRegistrationTimeout(registrationTimeout?.toString() || '');
      setMcpRoutingWeight(routingWeight?.toString() || '');
      
      // Transport-specific fields
      setMcpServerPath(serverPath || '');
      setMcpHttpEndpoint(httpEndpoint || '');
      setMcpHeaders(headers ? Object.entries(headers).map(([key, value]) => ({ key, value: String(value) })) : []);
      setMcpCommand(command || '');
      setMcpArgs(Array.isArray(args) ? args : []);
      
      console.log('✅ Form fields have been set');
    } else {
      console.log('❌ Missing required data for form population');
      console.log('- mcpClientConfig exists:', !!mcpClientConfig);
      console.log('- editingMCPClient exists:', !!editingMCPClient);
    }
  }, [mcpClientConfig, editingMCPClient]);


  // Effect to populate workflow form when workflow config is loaded
  React.useEffect(() => {
    if (workflowConfig && editingWorkflow && !workflowFormPopulated) {
      console.log('🔄 Populating workflow form with config:', workflowConfig);
      
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
      console.log('✅ Workflow form populated successfully');
    } else if (editingWorkflow && editingWorkflow.type !== 'custom_workflow' && !workflowConfig && !workflowConfigLoading) {
      console.log('❌ Failed to load workflow config for:', editingWorkflow);
    }
  }, [workflowConfig, editingWorkflow, workflowConfigLoading, workflowFormPopulated]);

  // Effect to populate custom workflow form when custom workflow config is loaded
  React.useEffect(() => {
    if (customWorkflowConfig && editingWorkflow && !customWorkflowFormPopulated && editingWorkflow.type === 'custom_workflow') {
      console.log('🔄 Populating custom workflow form with config:', customWorkflowConfig);
      
      // Populate custom workflow form fields
      setWorkflowName(customWorkflowConfig.name || '');
      setWorkflowDescription(customWorkflowConfig.description || '');
      setCustomWorkflowModulePath(customWorkflowConfig.module_path || '');
      setCustomWorkflowClassName(customWorkflowConfig.class_name || '');
      
      // Mark form as populated to prevent re-population
      setCustomWorkflowFormPopulated(true);
      console.log('✅ Custom workflow form populated successfully');
    } else if (editingWorkflow && editingWorkflow.type === 'custom_workflow' && !customWorkflowConfig && !customWorkflowConfigLoading) {
      console.log('❌ Failed to load custom workflow config for:', editingWorkflow);
    }
  }, [customWorkflowConfig, editingWorkflow, customWorkflowConfigLoading, customWorkflowFormPopulated]);

  const renderAgentForm = () => (
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
          onClick={() => setShowAgentForm(false)}
          className="w-9 h-9"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-3xl font-bold text-primary">
          {editingAgent ? 'Edit Agent' : 'Build New Agent'}
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
        {configLoading && editingAgent && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading agent configuration...
          </div>
        )}

        {/* Agent Name */}
        <div className="space-y-2">
          <Label htmlFor="agent-form-name" className="text-sm font-medium text-foreground">Agent Name</Label>
          <Input
            id="agent-form-name"
            placeholder="e.g., Customer Support Agent"
            value={agentFormName}
            onChange={(e) => setAgentFormName(e.target.value)}
            className="text-base"
          />
        </div>

        {/* System Prompt */}
        <div className="space-y-2">
          <Label htmlFor="agent-system-prompt" className="text-sm font-medium text-foreground">System Prompt</Label>
          <Textarea
            id="agent-system-prompt"
            placeholder="e.g., You are a helpful assistant..."
            value={agentSystemPrompt}
            onChange={(e) => setAgentSystemPrompt(e.target.value)}
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
                  {selectedMCPServers.map((server) => (
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
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
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
              <Label className="text-sm font-medium text-foreground">Available MCP Servers</Label>
              <div className="space-y-2">
                {clients.map((client) => {
                  const isSelected = selectedMCPServers.includes(client.name);
                  const isConnected = client.status === 'connected';
                  
                  return (
                    <button
                      key={client.name}
                      type="button"
                      onClick={() => {
                        if (isConnected) {
                          if (isSelected) {
                            setSelectedMCPServers(selectedMCPServers.filter(s => s !== client.name));
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
                        <div className={`w-4 h-4 rounded border-2 flex items-center justify-center ${
                          isSelected
                            ? 'bg-primary border-primary'
                            : 'border-muted-foreground'
                        }`}>
                          {isSelected && (
                            <svg className="w-2.5 h-2.5 text-primary-foreground" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                        <span className="text-sm font-medium">{client.name}</span>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        isConnected
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}>
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
                {llms.map((config) => {
                  // Safely extract LLM config ID
                  const configId = typeof config.id === 'string' 
                    ? config.id 
                    : (config.id && typeof config.id === 'object' && 'name' in config.id)
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
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">Model</Label>
              <Input
                placeholder="e.g., gpt-4, claude-3-opus"
                value={inlineModel}
                onChange={(e) => setInlineModel(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">Temperature</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  placeholder="0.7"
                  value={inlineTemperature}
                  onChange={(e) => setInlineTemperature(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">Max Tokens</Label>
                <Input
                  type="number"
                  placeholder="2048"
                  value={inlineMaxTokens}
                  onChange={(e) => setInlineMaxTokens(e.target.value)}
                />
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
          <Label htmlFor="max-iterations" className="text-sm font-medium text-foreground">Max Iterations</Label>
          <Input
            id="max-iterations"
            type="number"
            value={maxIterations}
            onChange={(e) => setMaxIterations(e.target.value)}
            className="text-base"
          />
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
        {editingAgent && (
          <Button 
            variant="destructive"
            className="px-6"
            onClick={() => {
              setDeletingAgent({ name: editingAgent.name, configFile: editingAgent.configFile });
              setShowAgentDeleteConfirmation(true);
            }}
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
        {!editingAgent && <div />}
        
        <Button 
          className="px-8"
          onClick={() => {
            // Build the agent config object
            const agentConfig = {
              name: agentFormName,
              system_prompt: agentSystemPrompt,
              mcp_servers: selectedMCPServers,
              max_iterations: parseInt(maxIterations) || 10,
              ...(llmConfigOption === 'existing' && selectedLLMConfig ? {
                llm_config_id: selectedLLMConfig,
              } : {}),
              ...(llmConfigOption === 'inline' ? {
                model: inlineModel,
                temperature: inlineTemperature ? parseFloat(inlineTemperature) : undefined,
                max_tokens: inlineMaxTokens ? parseInt(inlineMaxTokens) : undefined,
              } : {})
            };

            console.log('💾 Saving agent config:', agentConfig);

            if (editingAgent && editingAgent.name) {
              // Edit mode - update existing agent using PUT method
              updateAgent.mutate({
                filename: editingAgent.name,
                config: agentConfig
              }, {
                onSuccess: () => {
                  console.log('✅ Agent config updated successfully');
                  setShowAgentForm(false);
                  setEditingAgent(null);
                },
                onError: (error) => {
                  console.error('❌ Failed to update agent config:', error);
                }
              });
            } else {
              // Create mode - create new agent using POST method
              createAgent.mutate(agentConfig, {
                onSuccess: () => {
                  console.log('✅ New agent config created successfully');
                  setShowAgentForm(false);
                  setEditingAgent(null);
                },
                onError: (error) => {
                  console.error('❌ Failed to create agent config:', error);
                }
              });
            }
          }}
          disabled={(updateAgent.isPending || createAgent.isPending) || !agentFormName}
        >
          {(updateAgent.isPending || createAgent.isPending) ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              {editingAgent ? 'Updating...' : 'Creating...'}
            </>
          ) : (
            editingAgent ? 'Update Agent Config' : 'Create Agent Config'
          )}
        </Button>
      </motion.div>
    </motion.div>
  );

  const renderAgentsContent = () => {
    if (showAgentForm) {
      return renderAgentForm();
    }

    return (
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-6xl mx-auto space-y-6"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">All Agents</h1>
            <p className="text-muted-foreground mt-1">Manage and execute your existing agents</p>
          </div>
          <Button className="gap-2" onClick={handleNewAgent}>
            <Plus className="h-4 w-4" />
            New Agent
          </Button>
        </div>

        {/* Loading State */}
        {agentsLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Empty State */}
        {!agentsLoading && agents.length === 0 && (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="bg-card border border-border rounded-lg p-12 text-center space-y-4"
          >
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
              <Users className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-medium text-foreground">No agents created yet</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Create your first AI agent to get started
              </p>
            </div>
            <Button className="gap-2" onClick={() => setShowAgentForm(true)}>
              <Plus className="h-4 w-4" />
              Create Your First Agent
            </Button>
          </motion.div>
        )}

        {/* Agents Grid */}
        {!agentsLoading && agents.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent, index) => {
              // Safely extract agent name from potentially complex object
              let agentName: string;
              if (typeof agent.name === 'string') {
                agentName = agent.name;
              } else if (agent.name && typeof agent.name === 'object' && 'name' in agent.name) {
                agentName = String((agent.name as any).name);
              } else if (agent.name) {
                agentName = String(agent.name);
              } else {
                agentName = 'Unknown Agent';
              }

              return (
                <motion.div
                  key={`${agentName}-${index}`}
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: index * 0.1 }}
                  className="gradient-card rounded-lg p-4 space-y-3 hover:shadow-md transition-all duration-200 gradient-glow"
                >
                  <div className="space-y-2">
                    <h3 className="font-semibold text-foreground">
                      {agentName}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {agent.configFile ? 'Configured and ready' : 'Configuration pending'}
                    </p>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="gap-1.5" 
                      onClick={() => handleEditAgent({ name: agentName, configFile: agent.configFile, fullConfig: agent })}
                    >
                      <Edit className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    <Button 
                      size="sm" 
                      className="gap-1.5"
                      onClick={() => {
                        // Convert agent to AgentConfig format for the execution interface
                        const agentConfig: AgentConfig = {
                          type: 'agent',
                          name: agentName,
                          description: (agent as any).fullConfig?.description || 'Agent configuration',
                          llm_config_id: (agent as any).fullConfig?.llm_config_id,
                          model: (agent as any).fullConfig?.model,
                          temperature: (agent as any).fullConfig?.temperature,
                          max_tokens: (agent as any).fullConfig?.max_tokens,
                          system_prompt: (agent as any).fullConfig?.system_prompt,
                          max_iterations: (agent as any).fullConfig?.max_iterations,
                          include_history: (agent as any).fullConfig?.include_history,
                          auto: (agent as any).fullConfig?.auto,
                          mcp_servers: (agent as any).fullConfig?.mcp_servers,
                          exclude_components: (agent as any).fullConfig?.exclude_components,
                          _source_file: agent.configFile,
                          _context_path: (agent as any).fullConfig?._context_path,
                          _context_level: (agent as any).fullConfig?._context_level,
                          _project_name: (agent as any).fullConfig?._project_name,
                          _workspace_name: (agent as any).fullConfig?._workspace_name
                        };
                        
                        setExecutionInterface({
                          isOpen: true,
                          agentName: agentName
                        });
                      }}
                      disabled={executeAgent.isAgentExecuting(agentName)}
                    >
                      {executeAgent.isAgentExecuting(agentName) ? (
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
    );
  };

  const renderCustomWorkflowForm = () => (
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
          onClick={() => setShowCustomWorkflowForm(false)}
          className="w-9 h-9"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-3xl font-bold text-primary">
          Edit Custom Workflow
        </h1>
      </div>

      {/* Loading State for Custom Workflow Config */}
      {customWorkflowConfigLoading && editingWorkflow && (
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
          {/* Module Path */}
          <div className="space-y-2">
            <Label htmlFor="module-path" className="text-sm font-medium text-foreground">Module Path *</Label>
            <Input
              id="module-path"
              placeholder="e.g., custom_workflows.data_processing"
              value={customWorkflowModulePath}
              onChange={(e) => setCustomWorkflowModulePath(e.target.value)}
              className="text-base"
            />
            <p className="text-xs text-muted-foreground">
              Python module path containing your workflow class
            </p>
          </div>

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
        {editingWorkflow && (
          <Button 
            variant="destructive"
            className="px-6"
            onClick={() => setShowWorkflowDeleteConfirmation(true)}
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
        {!editingWorkflow && <div />}
        
        <Button 
          className="px-8"
          onClick={() => {
            // Build the custom workflow config object from form state
            const customWorkflowConfig = {
              name: workflowName,
              type: "custom_workflow" as const,
              module_path: customWorkflowModulePath,
              class_name: customWorkflowClassName,
              description: workflowDescription || undefined
            };

            console.log('💾 Saving custom workflow config:', customWorkflowConfig);

            if (editingWorkflow && editingWorkflow.name) {
              // Edit mode - update existing custom workflow using PUT method
              updateCustomWorkflow.mutate({
                filename: editingWorkflow.name,
                config: customWorkflowConfig
              }, {
                onSuccess: () => {
                  console.log('✅ Custom workflow updated successfully');
                  
                  // Invalidate custom workflow config cache to force fresh data load
                  queryClient.invalidateQueries({ 
                    queryKey: ['custom-workflow-config-by-name', editingWorkflow.name] 
                  });
                  
                  // Reset form state
                  setWorkflowName('');
                  setWorkflowDescription('');
                  setCustomWorkflowModulePath('');
                  setCustomWorkflowClassName('');
                  setCustomWorkflowFormPopulated(false);
                  
                  // Close form and redirect to workflows page
                  setShowCustomWorkflowForm(false);
                  setEditingWorkflow(null);
                  setActiveTab('workflows');
                },
                onError: (error) => {
                  console.error('❌ Failed to update custom workflow:', error);
                }
              });
            }
          }}
          disabled={updateCustomWorkflow.isPending || !workflowName.trim() || !customWorkflowModulePath.trim() || !customWorkflowClassName.trim()}
        >
          {updateCustomWorkflow.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Updating...
            </>
          ) : (
            'Update Custom Workflow'
          )}
        </Button>
      </motion.div>
    </motion.div>
  );

  const renderWorkflowForm = () => (
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
          onClick={() => setShowWorkflowForm(false)}
          className="w-9 h-9"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-3xl font-bold text-primary">
          {editingWorkflow ? 'Edit Simple Workflow' : 'Build New Simple Workflow'}
        </h1>
      </div>

      {/* Workflow Details Card */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="bg-card border border-border rounded-lg p-6 space-y-6"
      >
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
                <SelectItem value="" disabled>
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Loading agents...
                  </div>
                </SelectItem>
              ) : agents.length === 0 ? (
                <SelectItem value="" disabled>
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
        {editingWorkflow && (
          <Button 
            variant="destructive"
            className="px-6"
            onClick={() => setShowWorkflowDeleteConfirmation(true)}
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
        {!editingWorkflow && <div />}
        
        <Button 
          className="px-8"
          onClick={() => {
            // Build the workflow config object from form state
            const workflowConfig = {
              name: workflowName,
              type: "simple_workflow" as const,
              steps: workflowSteps.map(step => step.agent), // Convert UI format to API format
              description: workflowDescription || undefined
            };

            console.log('💾 Saving workflow config:', workflowConfig);

            if (editingWorkflow && editingWorkflow.name) {
              // Edit mode - update existing workflow using PUT method
              updateWorkflow.mutate({
                filename: editingWorkflow.name,
                config: workflowConfig
              }, {
                onSuccess: () => {
                  console.log('✅ Workflow updated successfully');
                  
                  // Invalidate workflow config cache to force fresh data load
                  queryClient.invalidateQueries({ 
                    queryKey: ['workflow-config-by-name', editingWorkflow.name] 
                  });
                  
                  // Reset form state
                  setWorkflowName('');
                  setWorkflowDescription('');
                  setWorkflowSteps([]);
                  setSelectedAgentToAdd('');
                  setWorkflowFormPopulated(false);
                  
                  // Close form and redirect to workflows page
                  setShowWorkflowForm(false);
                  setEditingWorkflow(null);
                  setActiveTab('workflows');
                },
                onError: (error) => {
                  console.error('❌ Failed to update workflow:', error);
                }
              });
            } else {
              // Create mode - create new workflow using POST method
              createWorkflow.mutate(workflowConfig, {
                onSuccess: () => {
                  console.log('✅ New workflow created successfully');
                  // Reset form state
                  setWorkflowName('');
                  setWorkflowDescription('');
                  setWorkflowSteps([]);
                  setSelectedAgentToAdd('');
                  setWorkflowFormPopulated(false);
                  
                  // Close form and redirect to workflows page
                  setShowWorkflowForm(false);
                  setEditingWorkflow(null);
                  setActiveTab('workflows');
                },
                onError: (error) => {
                  console.error('❌ Failed to create workflow:', error);
                }
              });
            }
          }}
          disabled={(updateWorkflow.isPending || createWorkflow.isPending) || !workflowName.trim() || workflowSteps.length === 0}
        >
          {(updateWorkflow.isPending || createWorkflow.isPending) ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              {editingWorkflow ? 'Updating...' : 'Creating...'}
            </>
          ) : (
            editingWorkflow ? 'Update Simple Workflow' : 'Save Simple Workflow'
          )}
        </Button>
      </motion.div>
    </motion.div>
  );

  const renderWorkflowsContent = () => {
    if (showWorkflowForm) {
      return renderWorkflowForm();
    }

    if (showCustomWorkflowForm) {
      return renderCustomWorkflowForm();
    }

    const isLoading = workflowsLoading || customWorkflowsLoading;
    const allWorkflows = [...workflows, ...customWorkflows];

    return (
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
            <Button className="gap-2" onClick={() => setShowWorkflowForm(true)}>
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
              const badgeText = workflow.type === 'simple_workflow' ? 'Simple' : 'Custom';
              const badgeColor = workflow.type === 'simple_workflow' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' : 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400';
              
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
                      onClick={() => {
                        if (workflow.type === 'custom_workflow') {
                          // Reset custom workflow form state
                          setWorkflowName('');
                          setWorkflowDescription('');
                          setCustomWorkflowModulePath('');
                          setCustomWorkflowClassName('');
                          setCustomWorkflowFormPopulated(false);
                          
                          // Set editing workflow and show custom form
                          // For custom workflows, use the workflow name as the identifier since the API expects the component name
                          setEditingWorkflow({ name: workflowName, configFile: workflowName, type: 'custom_workflow' });
                          setShowCustomWorkflowForm(true);
                        } else {
                          // Reset simple workflow form state
                          setWorkflowName('');
                          setWorkflowDescription('');
                          setWorkflowSteps([]);
                          setWorkflowFormPopulated(false);
                          
                          // Set editing workflow and show simple form
                          setEditingWorkflow({ name: workflowName, configFile: workflow.configFile, type: 'simple_workflow' });
                          setShowWorkflowForm(true);
                        }
                      }}
                    >
                      <Edit className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    <Button 
                      size="sm" 
                      className="gap-1.5"
                      onClick={async () => {
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
                              type: 'simple_workflow',
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
                      }}
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
    );
  };

  const renderMCPForm = () => (
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
          onClick={() => setShowMCPForm(false)}
          className="w-9 h-9"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-3xl font-bold text-primary">
          {editingMCPClient ? 'Edit MCP Server' : 'Build New MCP Server'}
        </h1>
      </div>

      {/* Basic Configuration Card */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="bg-card border border-border rounded-lg p-6 space-y-6"
      >
        <h2 className="text-lg font-semibold text-primary">Basic Configuration</h2>
        
        {/* Server Name */}
        <div className="space-y-2">
          <Label htmlFor="server-name" className="text-sm font-medium text-foreground">Server Name *</Label>
          <Input
            id="server-name"
            placeholder="e.g., weather_server"
            value={mcpClientId}
            onChange={(e) => setMcpClientId(e.target.value)}
            className="text-base"
          />
        </div>

        {/* Description */}
        <div className="space-y-2">
          <Label htmlFor="description" className="text-sm font-medium text-foreground">Description</Label>
          <Textarea
            id="description"
            placeholder="Brief description of what this server provides"
            value={mcpDescription}
            onChange={(e) => setMcpDescription(e.target.value)}
            className="min-h-[80px] resize-none"
          />
        </div>

        {/* Capabilities */}
        <div className="space-y-2">
          <Label htmlFor="capabilities" className="text-sm font-medium text-foreground">Capabilities *</Label>
          <Input
            id="capabilities"
            placeholder="tools, prompts, resources (comma-separated)"
            value={mcpCapabilities}
            onChange={(e) => setMcpCapabilities(e.target.value)}
            className="text-base"
          />
          <p className="text-xs text-muted-foreground">Valid options: tools, prompts, resources</p>
        </div>
      </motion.div>

      {/* Transport Configuration Card */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="bg-card border border-border rounded-lg p-6 space-y-6"
      >
        <h2 className="text-lg font-semibold text-primary">Transport Configuration</h2>
        
        {/* Transport Type */}
        <div className="space-y-2">
          <Label className="text-sm font-medium text-foreground">Transport Type *</Label>
          <Select value={mcpTransportType} onValueChange={(value: 'stdio' | 'http_stream' | 'local') => setMcpTransportType(value)}>
            <SelectTrigger>
              <SelectValue placeholder="Select transport type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="stdio">Stdio (Python script)</SelectItem>
              <SelectItem value="http_stream">HTTP Stream (Web endpoint)</SelectItem>
              <SelectItem value="local">Local (Command execution)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Stdio Transport Fields */}
        {mcpTransportType === 'stdio' && (
          <div className="space-y-4 p-4 bg-muted/20 rounded-lg">
            <h3 className="text-sm font-medium text-foreground">Stdio Configuration</h3>
            <div className="space-y-2">
              <Label htmlFor="server-path" className="text-sm font-medium text-foreground">Server Path *</Label>
              <Input
                id="server-path"
                placeholder="e.g., src/packaged_servers/weather_server.py"
                value={mcpServerPath}
                onChange={(e) => setMcpServerPath(e.target.value)}
                className="text-base"
              />
            </div>
          </div>
        )}

        {/* HTTP Stream Transport Fields */}
        {mcpTransportType === 'http_stream' && (
          <div className="space-y-4 p-4 bg-muted/20 rounded-lg">
            <h3 className="text-sm font-medium text-foreground">HTTP Stream Configuration</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="http-endpoint" className="text-sm font-medium text-foreground">HTTP Endpoint *</Label>
                <Input
                  id="http-endpoint"
                  placeholder="e.g., https://api.example.com/mcp"
                  value={mcpHttpEndpoint}
                  onChange={(e) => setMcpHttpEndpoint(e.target.value)}
                  className="text-base"
                  type="url"
                />
              </div>
              
              {/* Headers */}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">Headers</Label>
                {mcpHeaders.map((header, index) => (
                  <div key={index} className="flex gap-2">
                    <Input
                      placeholder="Header name"
                      value={header.key}
                      onChange={(e) => {
                        const newHeaders = [...mcpHeaders];
                        newHeaders[index] = { ...header, key: e.target.value };
                        setMcpHeaders(newHeaders);
                      }}
                      className="flex-1"
                    />
                    <Input
                      placeholder="Header value"
                      value={header.value}
                      onChange={(e) => {
                        const newHeaders = [...mcpHeaders];
                        newHeaders[index] = { ...header, value: e.target.value };
                        setMcpHeaders(newHeaders);
                      }}
                      className="flex-1"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const newHeaders = mcpHeaders.filter((_, i) => i !== index);
                        setMcpHeaders(newHeaders);
                      }}
                    >
                      Remove
                    </Button>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setMcpHeaders([...mcpHeaders, { key: '', value: '' }]);
                  }}
                >
                  Add Header
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Local Transport Fields */}
        {mcpTransportType === 'local' && (
          <div className="space-y-4 p-4 bg-muted/20 rounded-lg">
            <h3 className="text-sm font-medium text-foreground">Local Command Configuration</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="command" className="text-sm font-medium text-foreground">Command *</Label>
                <Input
                  id="command"
                  placeholder="e.g., ./my-server"
                  value={mcpCommand}
                  onChange={(e) => setMcpCommand(e.target.value)}
                  className="text-base"
                />
              </div>
              
              {/* Arguments */}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">Arguments</Label>
                {mcpArgs.map((arg, index) => (
                  <div key={index} className="flex gap-2">
                    <Input
                      placeholder="Argument"
                      value={arg}
                      onChange={(e) => {
                        const newArgs = [...mcpArgs];
                        newArgs[index] = e.target.value;
                        setMcpArgs(newArgs);
                      }}
                      className="flex-1"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const newArgs = mcpArgs.filter((_, i) => i !== index);
                        setMcpArgs(newArgs);
                      }}
                    >
                      Remove
                    </Button>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setMcpArgs([...mcpArgs, '']);
                  }}
                >
                  Add Argument
                </Button>
              </div>
            </div>
          </div>
        )}
      </motion.div>

      {/* Advanced Settings Card */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="bg-card border border-border rounded-lg p-6 space-y-6"
      >
        <h2 className="text-lg font-semibold text-primary">Advanced Settings</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Timeout */}
          <div className="space-y-2">
            <Label htmlFor="timeout" className="text-sm font-medium text-foreground">Timeout (seconds)</Label>
            <Input
              id="timeout"
              placeholder="10.0"
              value={mcpTimeout}
              onChange={(e) => setMcpTimeout(e.target.value)}
              className="text-base"
              type="number"
              step="0.1"
            />
          </div>

          {/* Registration Timeout */}
          <div className="space-y-2">
            <Label htmlFor="registration-timeout" className="text-sm font-medium text-foreground">Registration Timeout (seconds)</Label>
            <Input
              id="registration-timeout"
              placeholder="30.0"
              value={mcpRegistrationTimeout}
              onChange={(e) => setMcpRegistrationTimeout(e.target.value)}
              className="text-base"
              type="number"
              step="0.1"
            />
          </div>

          {/* Routing Weight */}
          <div className="space-y-2">
            <Label htmlFor="routing-weight" className="text-sm font-medium text-foreground">Routing Weight</Label>
            <Input
              id="routing-weight"
              placeholder="1.0"
              value={mcpRoutingWeight}
              onChange={(e) => setMcpRoutingWeight(e.target.value)}
              className="text-base"
              type="number"
              step="0.1"
            />
          </div>
        </div>
      </motion.div>

      {/* Action Buttons */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="flex justify-between"
      >
        {/* Delete Button - Only show in edit mode */}
        {editingMCPClient && (
          <Button 
            variant="destructive"
            className="px-6"
            onClick={() => setShowMCPDeleteConfirmation(true)}
            disabled={deleteMCPClient.isPending}
          >
            {deleteMCPClient.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Deleting...
              </>
            ) : (
              'Delete MCP Server'
            )}
          </Button>
        )}
        
        {/* Spacer for alignment when no delete button */}
        {!editingMCPClient && <div />}
        
        <Button 
          className="px-8"
          onClick={() => {
            // Build the complete MCP server configuration
            const validCapabilities = mcpCapabilities
              .split(',')
              .map(c => c.trim())
              .filter(c => c && ['tools', 'prompts', 'resources'].includes(c));

            const mcpServerConfig: any = {
              name: mcpClientId,
              type: "mcp_server",
              capabilities: validCapabilities,
              transport_type: mcpTransportType,
            };

            // Add optional fields
            if (mcpDescription) mcpServerConfig.description = mcpDescription;
            if (mcpTimeout) mcpServerConfig.timeout = parseFloat(mcpTimeout);
            if (mcpRegistrationTimeout) mcpServerConfig.registration_timeout = parseFloat(mcpRegistrationTimeout);
            if (mcpRoutingWeight) mcpServerConfig.routing_weight = parseFloat(mcpRoutingWeight);

            // Add transport-specific fields
            if (mcpTransportType === 'stdio' && mcpServerPath) {
              mcpServerConfig.server_path = mcpServerPath;
            } else if (mcpTransportType === 'http_stream' && mcpHttpEndpoint) {
              mcpServerConfig.http_endpoint = mcpHttpEndpoint;
              if (mcpHeaders.length > 0) {
                const headersObj: Record<string, string> = {};
                mcpHeaders.forEach(header => {
                  if (header.key && header.value) {
                    headersObj[header.key] = header.value;
                  }
                });
                if (Object.keys(headersObj).length > 0) {
                  mcpServerConfig.headers = headersObj;
                }
              }
            } else if (mcpTransportType === 'local' && mcpCommand) {
              mcpServerConfig.command = mcpCommand;
              if (mcpArgs.length > 0 && mcpArgs.some(arg => arg.trim())) {
                mcpServerConfig.args = mcpArgs.filter(arg => arg.trim());
              }
            }

            // Reset form fields function
            const resetFormFields = () => {
              setMcpClientId('');
              setMcpDescription('');
              setMcpTransportType('stdio');
              setMcpCapabilities('');
              setMcpTimeout('');
              setMcpRegistrationTimeout('');
              setMcpRoutingWeight('');
              setMcpServerPath('');
              setMcpHttpEndpoint('');
              setMcpHeaders([]);
              setMcpCommand('');
              setMcpArgs([]);
            };

            if (editingMCPClient && editingMCPClient.configFile) {
              // Edit mode - update existing MCP server
              updateMCPClient.mutate({
                filename: editingMCPClient.configFile,
                config: mcpServerConfig
              }, {
                onSuccess: () => {
                  setShowMCPForm(false);
                  setEditingMCPClient(null);
                  resetFormFields();
                }
              });
            } else {
              // Create mode - create new MCP server
              createMCPServer.mutate({
                name: mcpClientId,
                config: mcpServerConfig
              }, {
                onSuccess: () => {
                  setShowMCPForm(false);
                  setEditingMCPClient(null);
                  resetFormFields();
                }
              });
            }
          }}
          disabled={(updateMCPClient.isPending || createMCPServer.isPending) || !mcpClientId || !mcpCapabilities || 
            (mcpTransportType === 'stdio' && !mcpServerPath) ||
            (mcpTransportType === 'http_stream' && !mcpHttpEndpoint) ||
            (mcpTransportType === 'local' && !mcpCommand)
          }
        >
          {(updateMCPClient.isPending || createMCPServer.isPending) ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              {editingMCPClient ? 'Updating...' : 'Creating...'}
            </>
          ) : (
            editingMCPClient ? 'Update MCP Server' : 'Save MCP Server'
          )}
        </Button>
      </motion.div>
    </motion.div>
  );

  const renderMCPClientsContent = () => {
    if (showMCPForm) {
      return renderMCPForm();
    }

    return (
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-6xl mx-auto space-y-6"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">MCP Clients</h1>
            <p className="text-muted-foreground mt-1">Manage and configure your MCP client connections</p>
          </div>
          <Button className="gap-2" onClick={() => {
            // Reset form state for create mode
            setMcpClientId('');
            setMcpServerPath('');
            setMcpCapabilities('');
            setMcpTimeout('');
            setMcpRoutingWeight('');
            
            // Clear editing state to ensure we're in create mode
            setEditingMCPClient(null);
            
            // Show form
            setShowMCPForm(true);
          }}>
            <Plus className="h-4 w-4" />
            New MCP Client
          </Button>
        </div>

        {/* Loading State */}
        {clientsLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Empty State */}
        {!clientsLoading && clients.length === 0 && (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="bg-card border border-border rounded-lg p-12 text-center space-y-4"
          >
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
              <Database className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-medium text-foreground">No MCP clients configured yet</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Configure your first MCP client to enable additional capabilities
              </p>
            </div>
            <Button className="gap-2" onClick={() => setShowMCPForm(true)}>
              <Plus className="h-4 w-4" />
              Configure Your First Client
            </Button>
          </motion.div>
        )}

        {/* MCP Clients Grid */}
        {!clientsLoading && clients.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {clients.map((client, index) => (
              <MCPClientCard
                key={client.name}
                client={client}
                index={index}
                onConfigure={(clientName) => {
                  // Reset ALL MCP form state first
                  setMcpClientId('');
                  setMcpDescription('');
                  setMcpTransportType('stdio');
                  setMcpCapabilities('');
                  setMcpTimeout('');
                  setMcpRegistrationTimeout('');
                  setMcpRoutingWeight('');
                  setMcpServerPath('');
                  setMcpHttpEndpoint('');
                  setMcpHeaders([]);
                  setMcpCommand('');
                  setMcpArgs([]);
                  
                  // Set editing MCP client and show form
                  setEditingMCPClient({ name: clientName, configFile: clientName });
                  setShowMCPForm(true);
                }}
              />
            ))}
          </div>
        )}
      </motion.div>
    );
  };

  const renderLLMForm = () => (
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
          onClick={() => setShowLLMForm(false)}
          className="w-9 h-9"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-3xl font-bold text-primary">
          {editingLLM ? 'Edit LLM Configuration' : 'Build New LLM Configuration'}
        </h1>
      </div>

      {/* LLM Configuration Card */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="bg-card border border-border rounded-lg p-6 space-y-6"
      >
        {/* LLM Name */}
        <div className="space-y-2">
          <Label htmlFor="llm-name" className="text-sm font-medium text-foreground">LLM Name</Label>
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
        {editingLLM && (
          <Button 
            variant="destructive"
            className="px-6"
            onClick={() => setShowDeleteConfirmation(true)}
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
        {!editingLLM && <div />}
        
        <Button 
          className="px-8"
          onClick={() => {
            if (editingLLM && editingLLM.id) {
              // Edit mode - update existing LLM configuration
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

              updateLLM.mutate({
                filename: editingLLM.id, // Using ID as filename
                config: llmConfig
              }, {
                onSuccess: () => {
                  setShowLLMForm(false);
                  setShowLLMEditForm(false);
                  setEditingLLM(null);
                  setIsCreatingLLM(false);
                  // Reset form fields
                  setLlmId('');
                  setLlmProvider('');
                  setLlmModelName('');
                  setLlmTemperature('');
                  setLlmMaxTokens('');
                  setLlmSystemPrompt('');
                  setLlmApiKeyEnvVar('');
                }
              });
            } else {
              // Create mode - create new LLM configuration
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

              createLLM.mutate(llmConfig, {
                onSuccess: () => {
                  setShowLLMForm(false);
                  setShowLLMEditForm(false);
                  setEditingLLM(null);
                  setIsCreatingLLM(false);
                  // Reset form fields
                  setLlmId('');
                  setLlmProvider('');
                  setLlmModelName('');
                  setLlmTemperature('');
                  setLlmMaxTokens('');
                  setLlmSystemPrompt('');
                  setLlmApiKeyEnvVar('');
                }
              });
            }
          }}
          disabled={(updateLLM.isPending || createLLM.isPending) || !llmId}
        >
          {(updateLLM.isPending || createLLM.isPending) ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              {editingLLM ? 'Updating...' : 'Creating...'}
            </>
          ) : (
            editingLLM ? 'Update LLM Config' : 'Create LLM Config'
          )}
        </Button>
      </motion.div>
    </motion.div>
  );

  const renderLLMConfigsContent = () => {
    if (showLLMForm) {
      return renderLLMForm();
    }

    return (
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-6xl mx-auto space-y-6"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">LLM Configs</h1>
            <p className="text-muted-foreground mt-1">Manage and configure your language model settings</p>
          </div>
          <Button className="gap-2" onClick={() => {
            // Reset form state for create mode
            setLlmId('');
            setLlmProvider('');
            setLlmModelName('');
            setLlmTemperature('');
            setLlmMaxTokens('');
            setLlmSystemPrompt('');
            setLlmApiKeyEnvVar('');
            
            // Clear editing state
            setEditingLLM(null);
            setShowLLMEditForm(false);
            setIsCreatingLLM(true);
            
            // Show form
            setShowLLMForm(true);
          }}>
            <Plus className="h-4 w-4" />
            New LLM Config
          </Button>
        </div>

        {/* Loading State */}
        {llmsLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Empty State */}
        {!llmsLoading && llms.length === 0 && (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="bg-card border border-border rounded-lg p-12 text-center space-y-4"
          >
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
              <Cloud className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-medium text-foreground">No LLM configurations yet</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Configure your first language model to enable AI capabilities
              </p>
            </div>
            <Button className="gap-2" onClick={() => setShowLLMForm(true)}>
              <Plus className="h-4 w-4" />
              Configure Your First LLM
            </Button>
          </motion.div>
        )}

        {/* LLM Configs Grid */}
        {!llmsLoading && llms.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {llms.map((llm, index) => {
              const llmId = typeof llm.id === 'string' ? llm.id : (llm.id as any)?.name || 'unknown_llm';
              return (
                <motion.div
                  key={llmId}
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: index * 0.1 }}
                  className="gradient-card rounded-lg p-4 space-y-3 hover:shadow-md transition-all duration-200 gradient-glow"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-foreground">{llmId}</h3>
                      <div className={`w-2 h-2 rounded-full ${llm.status === 'active' ? 'bg-green-500' : 'bg-gray-500'}`} />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {llm.configFile ? 'Configured' : 'Configuration pending'}
                    </p>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span className="capitalize">Status: {llm.status}</span>
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="gap-1.5" 
                      onClick={() => {
                        // Reset LLM form state
                        setLlmId('');
                        setLlmProvider('');
                        setLlmModelName('');
                        setLlmTemperature('');
                        setLlmMaxTokens('');
                        setLlmSystemPrompt('');
                        setLlmApiKeyEnvVar('');
                        
                        // Set editing LLM and show edit form
                        setEditingLLM({ id: llmId, configFile: llm.configFile });
                        setShowLLMEditForm(true);
                        setShowLLMForm(true);
                      }}
                    >
                      <Edit className="h-3.5 w-3.5" />
                      Configure
                    </Button>
                    <Button size="sm" className="gap-1.5">
                      <Play className="h-3.5 w-3.5" />
                      {llm.status === 'active' ? 'Deactivate' : 'Activate'}
                    </Button>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </motion.div>
    );
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'agents':
        return renderAgentsContent();
      case 'workflows':
        return renderWorkflowsContent();
      case 'mcp':
        return renderMCPClientsContent();
      case 'llm':
        return renderLLMConfigsContent();
      default:
        return renderHomeContent();
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Sidebar */}
      <motion.div 
        initial={{ x: -80 }}
        animate={{ 
          x: 0,
          width: sidebarHovered ? 250 : 80
        }}
        transition={{ duration: 0.3 }}
        onMouseEnter={() => setSidebarHovered(true)}
        onMouseLeave={() => setSidebarHovered(false)}
        className={`${sidebarHovered ? 'w-64' : 'w-20'} gradient-sidebar border-r border-border flex flex-col py-6 relative`}
      >
        {/* Logo */}
        <div className={`mb-12 ${sidebarHovered ? 'px-6' : 'flex justify-center'}`}>
          {sidebarHovered ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="flex items-center gap-3"
            >
              <Logo className="w-10 h-10" />
              <h1 className="text-xl font-bold text-foreground">Agent Studio</h1>
            </motion.div>
          ) : (
            <Logo className="w-10 h-10" />
          )}
        </div>

        {/* Navigation */}
        <nav className={`flex flex-col space-y-3 ${sidebarHovered ? 'px-4' : 'items-center'}`}>
          {sidebarItems.map((item, index) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="group relative"
            >
              <Button
                variant={activeTab === item.id ? "default" : "ghost"}
                onClick={() => {
                  setActiveTab(item.id);
                  setShowWorkflowForm(false);
                  setShowMCPForm(false);
                  setShowLLMForm(false);
                  setShowAgentForm(false);
                }}
                className={`${sidebarHovered ? 'w-full justify-start gap-3 h-11' : 'w-12 h-12'} rounded-xl`}
              >
                <item.icon className="h-5 w-5" />
                {sidebarHovered && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    {item.label}
                  </motion.span>
                )}
              </Button>
              {/* Tooltip for collapsed state */}
              {!sidebarHovered && (
                <div className="absolute left-16 top-1/2 -translate-y-1/2 bg-popover text-popover-foreground px-2 py-1 rounded-md text-sm opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                  {item.label}
                </div>
              )}
            </motion.div>
          ))}

          <div className={`${sidebarHovered ? 'w-full h-px' : 'w-8 h-px'} bg-border my-6 ${!sidebarHovered && 'mx-auto'}`} />

          {sidebarHovered && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4 px-3"
            >
              AI Component Configuration
            </motion.div>
          )}

          {configItems.map((item, index) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: (sidebarItems.length + index) * 0.1 }}
              className="group relative"
            >
              <Button
                variant="ghost"
                onClick={() => setActiveTab(item.id)}
                className={`${sidebarHovered ? 'w-full justify-start gap-3 h-11' : 'w-12 h-12'} rounded-xl`}
              >
                <item.icon className="h-5 w-5" />
                {sidebarHovered && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    {item.label}
                  </motion.span>
                )}
              </Button>
              {/* Tooltip for collapsed state */}
              {!sidebarHovered && (
                <div className="absolute left-16 top-1/2 -translate-y-1/2 bg-popover text-popover-foreground px-2 py-1 rounded-md text-sm opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                  {item.label}
                </div>
              )}
            </motion.div>
          ))}
        </nav>

        {/* Connection Status - Fixed at bottom */}
        <div className={`mt-auto ${sidebarHovered ? 'px-4' : 'flex justify-center'} pb-2`}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
            className="w-full justify-center flex"
          >
            <ConnectionStatus isExpanded={sidebarHovered} />
          </motion.div>
        </div>
      </motion.div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative">
        {/* Theme Toggle - Absolute positioned */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="absolute top-4 right-4 w-9 h-9 rounded-lg z-10"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        {/* Main Content Area */}
        <main className={`flex-1 ${activeTab === 'home' ? 'flex items-center justify-center' : 'flex flex-col'} px-6 ${activeTab === 'home' ? 'pb-8' : 'pt-12 pb-8'}`}>
          {renderContent()}
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
                  onClick={() => {
                    if (editingLLM && editingLLM.id) {
                      deleteLLM.mutate(editingLLM.id, {
                        onSuccess: () => {
                          setShowDeleteConfirmation(false);
                          setShowLLMForm(false);
                          setShowLLMEditForm(false);
                          setEditingLLM(null);
                          // Reset form fields
                          setLlmId('');
                          setLlmProvider('');
                          setLlmModelName('');
                          setLlmTemperature('');
                          setLlmMaxTokens('');
                          setLlmSystemPrompt('');
                          setLlmApiKeyEnvVar('');
                        }
                      });
                    }
                  }}
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

      {/* MCP Delete Confirmation Dialog */}
      <AnimatePresence>
        {showMCPDeleteConfirmation && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowMCPDeleteConfirmation(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border rounded-lg p-6 max-w-md mx-4 space-y-4"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-foreground">
                Delete MCP Server
              </h3>
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete the MCP server "{mcpClientId}"? This action cannot be undone.
              </p>
              <div className="flex gap-3 justify-end">
                <Button
                  variant="outline"
                  onClick={() => setShowMCPDeleteConfirmation(false)}
                  disabled={deleteMCPClient.isPending}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => {
                    if (editingMCPClient && editingMCPClient.configFile) {
                      deleteMCPClient.mutate(editingMCPClient.configFile, {
                        onSuccess: () => {
                          setShowMCPDeleteConfirmation(false);
                          setShowMCPForm(false);
                          setEditingMCPClient(null);
                          // Reset form fields
                          setMcpClientId('');
                          setMcpDescription('');
                          setMcpTransportType('stdio');
                          setMcpCapabilities('');
                          setMcpTimeout('');
                          setMcpRegistrationTimeout('');
                          setMcpRoutingWeight('');
                          setMcpServerPath('');
                          setMcpHttpEndpoint('');
                          setMcpHeaders([]);
                          setMcpCommand('');
                          setMcpArgs([]);
                        }
                      });
                    }
                  }}
                  disabled={deleteMCPClient.isPending}
                >
                  {deleteMCPClient.isPending ? (
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

      {/* Agent Delete Confirmation Dialog */}
      <AnimatePresence>
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
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-foreground">
                Delete Agent
              </h3>
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete the agent "{deletingAgent?.name}"? This action cannot be undone.
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
                  onClick={() => {
                    if (deletingAgent && deletingAgent.name) {
                      deleteAgent.mutate(deletingAgent.name, {
                        onSuccess: () => {
                          setShowAgentDeleteConfirmation(false);
                          setDeletingAgent(null);
                          setShowAgentForm(false);
                          setEditingAgent(null);
                          setActiveTab('agents');
                        }
                      });
                    }
                  }}
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
      </AnimatePresence>

      {/* Workflow Delete Confirmation Dialog */}
      <AnimatePresence>
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
                  onClick={() => {
                    if (editingWorkflow && editingWorkflow.name) {
                      // Use the correct delete hook based on workflow type
                      if (editingWorkflow.type === 'custom_workflow') {
                        deleteCustomWorkflow.mutate(editingWorkflow.name, {
                          onSuccess: () => {
                            setShowWorkflowDeleteConfirmation(false);
                            setShowCustomWorkflowForm(false);
                            setEditingWorkflow(null);
                            setActiveTab('workflows');
                            // Reset custom workflow form state
                            setWorkflowName('');
                            setWorkflowDescription('');
                            setCustomWorkflowModulePath('');
                            setCustomWorkflowClassName('');
                            setCustomWorkflowFormPopulated(false);
                          }
                        });
                      } else {
                        deleteWorkflow.mutate(editingWorkflow.name, {
                          onSuccess: () => {
                            setShowWorkflowDeleteConfirmation(false);
                            setShowWorkflowForm(false);
                            setEditingWorkflow(null);
                            setActiveTab('workflows');
                            // Reset simple workflow form state
                            setWorkflowName('');
                            setWorkflowDescription('');
                            setWorkflowSteps([]);
                            setSelectedAgentToAdd('');
                            setWorkflowFormPopulated(false);
                          }
                        });
                      }
                    }
                  }}
                  disabled={deleteWorkflow.isPending || deleteCustomWorkflow.isPending}
                >
                  {(deleteWorkflow.isPending || deleteCustomWorkflow.isPending) ? (
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

      {/* Unified Execution Interface */}
      <UnifiedExecutionInterface
        agentName={executionInterface.agentName}
        isOpen={executionInterface.isOpen}
        onClose={() => setExecutionInterface({ isOpen: false, agentName: null })}
      />

      {/* Unified Workflow Execution Interface */}
      <UnifiedWorkflowExecutionInterface
        workflow={workflowExecutionInterface.workflow}
        isOpen={workflowExecutionInterface.isOpen}
        onClose={() => setWorkflowExecutionInterface({ isOpen: false, workflow: null })}
      />
    </div>
  );
}

export default App;
