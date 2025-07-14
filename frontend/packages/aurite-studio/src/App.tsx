import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Home, Users, Workflow, Database, Cloud, Sparkles, Link, Wand2, Sun, Moon, Plus, Edit, Play, ArrowLeft, Loader2 } from 'lucide-react';
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
import { useTheme } from '@/contexts/ThemeContext';
import { Logo } from '@/components/Logo';
import { useAgentsWithConfigs, useExecuteAgent, useAgentConfig, useUpdateAgent } from '@/hooks/useAgents';
import { useWorkflowsWithConfigs, useCustomWorkflowsWithConfigs } from '@/hooks/useWorkflows';
import { useClientsWithStatus } from '@/hooks/useClients';
import { useLLMsWithConfigs } from '@/hooks/useLLMs';

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
  const [showMCPForm, setShowMCPForm] = useState(false);
  const [mcpClientId, setMcpClientId] = useState('');
  const [mcpServerPath, setMcpServerPath] = useState('');
  const [mcpCapabilities, setMcpCapabilities] = useState('');
  const [mcpTimeout, setMcpTimeout] = useState('');
  const [mcpRoutingWeight, setMcpRoutingWeight] = useState('');
  const [showLLMForm, setShowLLMForm] = useState(false);
  const [llmId, setLlmId] = useState('');
  const [llmProvider, setLlmProvider] = useState('');
  const [llmModelName, setLlmModelName] = useState('');
  const [llmTemperature, setLlmTemperature] = useState('');
  const [llmMaxTokens, setLlmMaxTokens] = useState('');
  const [llmSystemPrompt, setLlmSystemPrompt] = useState('');
  const [showAgentForm, setShowAgentForm] = useState(false);
  const [editingAgent, setEditingAgent] = useState<any>(null);
  const [agentFormName, setAgentFormName] = useState('');
  const [agentSystemPrompt, setAgentSystemPrompt] = useState('');
  const [llmConfigOption, setLlmConfigOption] = useState('existing');
  const [selectedLLMConfig, setSelectedLLMConfig] = useState('');
  const [maxIterations, setMaxIterations] = useState('10');
  const [selectedMCPServers, setSelectedMCPServers] = useState<string[]>([]);
  const [agentConfigLoading, setAgentConfigLoading] = useState(false);
  const [inlineTemperature, setInlineTemperature] = useState('');
  const [inlineMaxTokens, setInlineMaxTokens] = useState('');
  const [inlineModel, setInlineModel] = useState('');
  const { theme, toggleTheme } = useTheme();

  // API Hooks - must be at component level
  const { data: agents = [], isLoading: agentsLoading } = useAgentsWithConfigs();
  const executeAgent = useExecuteAgent();
  const updateAgent = useUpdateAgent();
  const { data: clients = [], isLoading: clientsLoading } = useClientsWithStatus();
  const { data: llms = [], isLoading: llmsLoading } = useLLMsWithConfigs();
  const { data: workflows = [], isLoading: workflowsLoading } = useWorkflowsWithConfigs();
  const { data: customWorkflows = [], isLoading: customWorkflowsLoading } = useCustomWorkflowsWithConfigs();
  
  // Hook for fetching agent config - only enabled when we have a configFile
  const { data: agentConfig, isLoading: configLoading } = useAgentConfig(
    editingAgent?.configFile || '',
    !!editingAgent?.configFile && showAgentForm
  );

  // Show advanced options when user starts typing description
  React.useEffect(() => {
    if (description.trim().length > 10 && !showAdvancedOptions) {
      setShowAdvancedOptions(true);
    }
  }, [description, showAdvancedOptions]);

  const addWorkflowStep = () => {
    setWorkflowSteps([...workflowSteps, { id: Date.now(), agent: 'Filtering Test Agent' }]);
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
                        <SelectItem value="gpt-4">GPT-4</SelectItem>
                        <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                        <SelectItem value="claude-3">Claude 3</SelectItem>
                        <SelectItem value="llama-2">Llama 2</SelectItem>
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
                    <div className="p-2.5 border border-border rounded-md bg-muted/20 h-9 flex items-center">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <div className="w-1 h-1 bg-primary rounded-full"></div>
                        <span>{mcpClients.length} clients</span>
                      </div>
                    </div>
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
                    disabled={!description.trim()}
                  >
                    <Sparkles className="h-3.5 w-3.5 mr-2" />
                    Create Agent
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
    
    // Set editing agent and show form
    setEditingAgent(agent);
    setShowAgentForm(true);
  };

  // Effect to populate form when agent config is loaded
  React.useEffect(() => {
    if (agentConfig && editingAgent) {
      setAgentFormName(agentConfig.name);
      setAgentSystemPrompt(agentConfig.system_prompt || '');
      setSelectedMCPServers(agentConfig.mcp_servers || []);
      setMaxIterations(agentConfig.max_iterations?.toString() || '10');
      
      // Check if agent has inline LLM config or uses existing
      if (agentConfig.model || agentConfig.temperature !== undefined || agentConfig.max_tokens !== undefined) {
        setLlmConfigOption('inline');
        setInlineModel(agentConfig.model || '');
        setInlineTemperature(agentConfig.temperature?.toString() || '');
        setInlineMaxTokens(agentConfig.max_tokens?.toString() || '');
      } else {
        setLlmConfigOption('existing');
        // Try to find matching LLM config
        const matchingLLM = llms.find(llm => llm.id === agentConfig.model);
        if (matchingLLM) {
          setSelectedLLMConfig(matchingLLM.id);
        }
      }
    }
  }, [agentConfig, editingAgent, llms]);

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
        ) : selectedMCPServers.length > 0 ? (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Selected servers:</p>
            <div className="flex flex-wrap gap-2">
              {selectedMCPServers.map((server) => (
                <span key={server} className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm">
                  {server}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">None selected.</p>
        )}
        
        <div className="space-y-2">
          <Label className="text-sm font-medium text-foreground">Available MCP Servers</Label>
          <div className="space-y-2">
            {clients.map((client) => (
              <label key={client.name} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={selectedMCPServers.includes(client.name)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedMCPServers([...selectedMCPServers, client.name]);
                    } else {
                      setSelectedMCPServers(selectedMCPServers.filter(s => s !== client.name));
                    }
                  }}
                  className="w-4 h-4 text-primary"
                />
                <span className="text-sm">{client.name}</span>
                <span className={`text-xs ${client.status === 'connected' ? 'text-green-500' : 'text-red-500'}`}>
                  ({client.status})
                </span>
              </label>
            ))}
          </div>
        </div>
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
          <div className="flex items-center space-x-2">
            <input
              type="radio"
              id="existing-config"
              name="llm-config"
              value="existing"
              checked={llmConfigOption === 'existing'}
              onChange={(e) => setLlmConfigOption(e.target.value)}
              className="w-4 h-4 text-primary"
            />
            <Label htmlFor="existing-config" className="text-sm font-medium text-foreground">
              Use Existing LLM Config
            </Label>
          </div>
          
          <div className="flex items-center space-x-2">
            <input
              type="radio"
              id="inline-config"
              name="llm-config"
              value="inline"
              checked={llmConfigOption === 'inline'}
              onChange={(e) => setLlmConfigOption(e.target.value)}
              className="w-4 h-4 text-primary"
            />
            <Label htmlFor="inline-config" className="text-sm font-medium text-foreground">
              Define Inline LLM Parameters
            </Label>
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
                {llms.map((config) => (
                  <SelectItem key={config.id} value={config.id}>
                    {config.id}
                  </SelectItem>
                ))}
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

      {/* Save Button */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="flex justify-end"
      >
        <Button 
          className="px-8"
          onClick={() => {
            if (editingAgent && editingAgent.configFile) {
              // Build the agent config object
              const agentConfig = {
                name: agentFormName,
                system_prompt: agentSystemPrompt,
                mcp_servers: selectedMCPServers,
                max_iterations: parseInt(maxIterations) || 10,
                ...(llmConfigOption === 'inline' ? {
                  model: inlineModel,
                  temperature: inlineTemperature ? parseFloat(inlineTemperature) : undefined,
                  max_tokens: inlineMaxTokens ? parseInt(inlineMaxTokens) : undefined,
                } : {})
              };

              // Update the agent configuration
              updateAgent.mutate({
                filename: editingAgent.configFile,
                config: agentConfig
              }, {
                onSuccess: () => {
                  setShowAgentForm(false);
                  setEditingAgent(null);
                }
              });
            }
          }}
          disabled={updateAgent.isPending || !agentFormName || !editingAgent?.configFile}
        >
          {updateAgent.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Saving...
            </>
          ) : (
            'Save Agent Config'
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
          <Button className="gap-2" onClick={() => setShowAgentForm(true)}>
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
              const agentName = typeof agent.name === 'string' ? agent.name : (agent.name as any)?.name || 'Unknown Agent';
              return (
                <motion.div
                  key={agentName}
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
                      onClick={() => handleEditAgent({ name: agentName, configFile: agent.configFile })}
                    >
                      <Edit className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    <Button 
                      size="sm" 
                      className="gap-1.5"
                      onClick={() => {
                        const userMessage = prompt(`Enter message for ${agentName}:`);
                        if (userMessage) {
                          executeAgent.mutate({
                            agentName: agentName,
                            request: { user_message: userMessage }
                          });
                        }
                      }}
                      disabled={executeAgent.isExecuting}
                    >
                      {executeAgent.isExecuting ? (
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
        <h1 className="text-3xl font-bold text-primary">Build New Simple Workflow</h1>
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
              <div key={step.id} className="flex items-center gap-2 p-2 bg-muted/20 rounded-md">
                <span className="text-sm">{index + 1}. {step.agent}</span>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <Select>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Filtering Test Agent" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="filtering-test">Filtering Test Agent</SelectItem>
              <SelectItem value="weather-assistant">Weather Assistant</SelectItem>
              <SelectItem value="research-agent">Research Agent</SelectItem>
              <SelectItem value="data-analyst">Data Analyst</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={addWorkflowStep} variant="outline">
            Add Step
          </Button>
        </div>
      </motion.div>

      {/* Save Button */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="flex justify-end"
      >
        <Button className="px-8">
          Save Simple Workflow
        </Button>
      </motion.div>
    </motion.div>
  );

  const renderWorkflowsContent = () => {
    if (showWorkflowForm) {
      return renderWorkflowForm();
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
          <Button className="gap-2" onClick={() => setShowWorkflowForm(true)}>
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
              return (
                <motion.div
                  key={workflowName}
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: index * 0.1 }}
                  className="gradient-card rounded-lg p-4 space-y-3 hover:shadow-md transition-all duration-200 gradient-glow"
                >
                  <div className="space-y-2">
                    <h3 className="font-semibold text-foreground">{workflowName}</h3>
                    <p className="text-sm text-muted-foreground">
                      {workflow.configFile ? 'Configured and ready' : 'Configuration pending'}
                    </p>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="gap-1.5" 
                      onClick={() => {
                        setEditingAgent({ name: workflowName, configFile: workflow.configFile });
                        setShowWorkflowForm(true);
                      }}
                    >
                      <Edit className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    <Button size="sm" className="gap-1.5">
                      <Play className="h-3.5 w-3.5" />
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
        <h1 className="text-3xl font-bold text-primary">Build New Client</h1>
      </div>

      {/* MCP Client Configuration Card */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="bg-card border border-border rounded-lg p-6 space-y-6"
      >
        {/* Client ID */}
        <div className="space-y-2">
          <Label htmlFor="client-id" className="text-sm font-medium text-foreground">Client ID</Label>
          <Input
            id="client-id"
            placeholder="e.g., my_custom_client"
            value={mcpClientId}
            onChange={(e) => setMcpClientId(e.target.value)}
            className="text-base"
          />
        </div>

        {/* Server Path */}
        <div className="space-y-2">
          <Label htmlFor="server-path" className="text-sm font-medium text-foreground">Server Path</Label>
          <Input
            id="server-path"
            placeholder="e.g., src/packaged_servers/my_server.py"
            value={mcpServerPath}
            onChange={(e) => setMcpServerPath(e.target.value)}
            className="text-base"
          />
        </div>

        {/* Capabilities */}
        <div className="space-y-2">
          <Label htmlFor="capabilities" className="text-sm font-medium text-foreground">Capabilities (comma-separated)</Label>
          <Input
            id="capabilities"
            placeholder="e.g., tools, prompts, resources"
            value={mcpCapabilities}
            onChange={(e) => setMcpCapabilities(e.target.value)}
            className="text-base"
          />
        </div>

        {/* Timeout */}
        <div className="space-y-2">
          <Label htmlFor="timeout" className="text-sm font-medium text-foreground">Timeout (seconds, optional)</Label>
          <Input
            id="timeout"
            placeholder="e.g., 15"
            value={mcpTimeout}
            onChange={(e) => setMcpTimeout(e.target.value)}
            className="text-base"
            type="number"
          />
        </div>

        {/* Routing Weight */}
        <div className="space-y-2">
          <Label htmlFor="routing-weight" className="text-sm font-medium text-foreground">Routing Weight (optional)</Label>
          <Input
            id="routing-weight"
            placeholder="e.g., 1.0"
            value={mcpRoutingWeight}
            onChange={(e) => setMcpRoutingWeight(e.target.value)}
            className="text-base"
            type="number"
            step="0.1"
          />
        </div>
      </motion.div>

      {/* Save Button */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="flex justify-end"
      >
        <Button className="px-8">
          Save Client Config
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
          <Button className="gap-2" onClick={() => setShowMCPForm(true)}>
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
            {clients.map((client, index) => {
              const clientName = typeof client.name === 'string' ? client.name : (client.name as any)?.name || 'Unknown Client';
              return (
                <motion.div
                  key={clientName}
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: index * 0.1 }}
                  className="gradient-card rounded-lg p-4 space-y-3 hover:shadow-md transition-all duration-200 gradient-glow"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-foreground">{clientName}</h3>
                      <div className={`w-2 h-2 rounded-full ${client.status === 'connected' ? 'bg-green-500' : 'bg-red-500'}`} />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {client.configFile ? 'Configured' : 'Configuration pending'}
                    </p>
                    <p className="text-xs text-muted-foreground capitalize">Status: {client.status}</p>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="gap-1.5" 
                      onClick={() => {
                        setEditingAgent({ name: clientName, configFile: client.configFile });
                        setShowMCPForm(true);
                      }}
                    >
                      <Edit className="h-3.5 w-3.5" />
                      Configure
                    </Button>
                    <Button size="sm" className="gap-1.5">
                      <Play className="h-3.5 w-3.5" />
                      {client.status === 'connected' ? 'Disconnect' : 'Connect'}
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
        <h1 className="text-3xl font-bold text-primary">Build New LLM Configuration</h1>
      </div>

      {/* LLM Configuration Card */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="bg-card border border-border rounded-lg p-6 space-y-6"
      >
        {/* LLM ID */}
        <div className="space-y-2">
          <Label htmlFor="llm-id" className="text-sm font-medium text-foreground">LLM ID</Label>
          <Input
            id="llm-id"
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

      {/* Save Button */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="flex justify-end"
      >
        <Button className="px-8">
          Save LLM Config
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
          <Button className="gap-2" onClick={() => setShowLLMForm(true)}>
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
              const llmId = typeof llm.id === 'string' ? llm.id : (llm.id as any)?.name || 'Unknown LLM';
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
                        setEditingAgent({ id: llmId, configFile: llm.configFile });
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
    </div>
  );
}

export default App;
