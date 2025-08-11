import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Link as LinkIcon, Wand2, Loader2, Plus } from 'lucide-react';
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
import { useCreateAgent } from '@/hooks/useAgents';
import { useClientsWithStatus } from '@/hooks/useClients';
import { useLLMsWithConfigs } from '@/hooks/useLLMs';
import { SuccessResponse } from '@/types';
import LLMConfigForm from '@/components/forms/LLMConfigForm';
import MCPClientForm from '@/components/forms/MCPClientForm';

const quickActions = [
  'Build a data analysis agent',
  'Create a customer service bot',
  'Make a content generation assistant',
  'Build a code review agent'
];

export default function HomePage() {
  const navigate = useNavigate();
  const [agentName, setAgentName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [selectedLandingMCPServers, setSelectedLandingMCPServers] = useState<string[]>([]);
  const [showLLMModal, setShowLLMModal] = useState(false);
  const [showMCPModal, setShowMCPModal] = useState(false);

  // API Hooks
  const createAgent = useCreateAgent();
  const { data: clients = [], isLoading: clientsLoading } = useClientsWithStatus();
  const { data: llms = [], isLoading: llmsLoading } = useLLMsWithConfigs();

  // Show advanced options when user starts typing description
  React.useEffect(() => {
    if (description.trim().length > 10 && !showAdvancedOptions) {
      setShowAdvancedOptions(true);
    }
  }, [description, showAdvancedOptions]);

  const handleCreateAgent = () => {
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
      onSuccess: (data: { configFile: string; registration: SuccessResponse }) => {
        console.log('✅ Agent created successfully:', data);
        
        // Reset form fields
        setDescription('');
        setAgentName('');
        setSelectedModel('');
        setSelectedLandingMCPServers([]);
        setShowAdvancedOptions(false);
        
        // Navigate to agents page using React Router
        navigate('/agents');
      },
      onError: (error) => {
        console.error('❌ Failed to create agent:', error);
      }
    });
  };

  return (
    <div className="w-full h-full flex flex-col">
      {/* Main Content - Centered */}
      <motion.div
        initial={{ y: 50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="flex-1 flex items-center justify-center"
      >
        <div className="w-full max-w-2xl mx-auto text-center space-y-6 md:space-y-8">
          {/* Announcement Banner - Positioned close to main content */}
          <motion.div
            initial={{ y: -36, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.5 }}
            className="flex justify-center pb-9"
          >
            <motion.div
              whileHover={{ scale: 1.02 }}
              className="relative overflow-hidden bg-gradient-to-r from-purple-600/20 via-pink-600/20 to-purple-600/20 border border-purple-500/30 rounded-full px-3 py-1.5 md:px-4 md:py-2 cursor-pointer group"
            >
              {/* Sparkle Animation Background */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 ease-out" />
              
              {/* Content */}
              <div className="relative flex items-center justify-center gap-2 text-sm font-medium">
                <motion.span
                  animate={{ rotate: [0, 10, -10, 0] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                  className="text-base"
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

          {/* Main Heading */}
          <div className="space-y-3">
            <motion.h1 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-3xl lg:text-5xl font-bold tracking-tight"
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
              className="min-h-[100px] md:min-h-[136px] text-base p-4 border border-border focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background focus:border-primary transition-all duration-200 rounded-lg resize-none gradient-card gradient-glow"
            />
            <div className="absolute bottom-3 left-3 flex items-center gap-2 text-muted-foreground">
              <LinkIcon className="h-3.5 w-3.5" />
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
                    <Select value={selectedModel} onValueChange={(value) => {
                      if (value === '__create_new__') {
                        setShowLLMModal(true);
                      } else {
                        setSelectedModel(value);
                      }
                    }}>
                      <SelectTrigger className="h-9 text-sm">
                        <SelectValue placeholder="Select model...">
                          {selectedModel && selectedModel !== '__create_new__' ? selectedModel : undefined}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {llmsLoading ? (
                          <SelectItem value="__loading__" disabled>
                            <div className="flex items-center gap-2">
                              <Loader2 className="h-3 w-3 animate-spin" />
                              Loading configurations...
                            </div>
                          </SelectItem>
                        ) : llms.length === 0 ? (
                          <SelectItem value="__no_llms__" disabled>
                            No LLM configurations available
                          </SelectItem>
                        ) : (
                          <>
                            {llms.map((config) => {
                              // Handle null config entries
                              if (!config) {
                                return null;
                              }
                              
                              // Safely extract LLM config ID
                              const configId = config && typeof config.id === 'string' 
                                ? config.id 
                                : (config?.id && typeof config.id === 'object' && 'name' in config.id)
                                  ? String((config.id as any).name)
                                  : String(config.id || 'unknown_config');
                              
                              // Check validation status
                              const isValidated = config.validated_at != null;
                              
                              return (
                                <SelectItem key={configId} value={configId}>
                                  <div className="flex items-center justify-between w-full">
                                    <span>{configId}</span>
                                    <span className={`px-2 py-1 text-xs rounded-full font-medium ${
                                      isValidated 
                                        ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-300'
                                        : 'bg-orange-50 text-orange-600 dark:bg-orange-950/50 dark:text-orange-300'
                                    }`}>
                                      {isValidated ? 'Ready' : 'Not Ready'}
                                    </span>
                                  </div>
                                </SelectItem>
                              );
                            })}
                            
                            {/* Separator */}
                            <div className="border-t border-border my-1" />
                            
                            {/* Create New LLM Option */}
                            <SelectItem value="__create_new__">
                              <div className="flex items-center gap-2 text-primary">
                                <Plus className="h-3.5 w-3.5" />
                                <span>Create New LLM Config</span>
                              </div>
                            </SelectItem>
                          </>
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
                          <div className="p-2 space-y-1">
                            {clients.map((client) => {
                              const isSelected = selectedLandingMCPServers.includes(client.name);
                              const isConnected = client.status === 'connected';
                              
                              return (
                                <button
                                  key={client.name}
                                  type="button"
                                  onClick={() => {
                                    if (isConnected) {
                                      if (isSelected) {
                                        setSelectedLandingMCPServers(selectedLandingMCPServers.filter(s => s !== client.name));
                                      } else {
                                        setSelectedLandingMCPServers([...selectedLandingMCPServers, client.name]);
                                      }
                                    }
                                  }}
                                  disabled={!isConnected}
                                  className={`w-full flex items-center gap-2 p-2 rounded-md transition-all duration-200 text-left ${
                                    isConnected
                                      ? 'hover:bg-accent cursor-pointer'
                                      : 'opacity-60 cursor-not-allowed'
                                  }`}
                                >
                                  <Checkbox 
                                    checked={isSelected}
                                    disabled={!isConnected}
                                    className="pointer-events-none"
                                  />
                                  <span className="text-sm pointer-events-none">{client.name}</span>
                                  <span className={`text-xs px-1 py-0.5 rounded pointer-events-none ml-auto ${
                                    client.status === 'connected' 
                                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                                      : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                  }`}>
                                    {client.status}
                                  </span>
                                </button>
                              );
                            })}
                            
                            {/* Separator */}
                            <div className="border-t border-border my-1" />
                            
                            {/* Create New MCP Client Option */}
                            <button
                              type="button"
                              onClick={() => setShowMCPModal(true)}
                              className="w-full flex items-center gap-2 p-2 rounded-md transition-all duration-200 text-left hover:bg-accent cursor-pointer text-primary"
                            >
                              <Plus className="h-3.5 w-3.5" />
                              <span className="text-sm">Create New MCP Client</span>
                            </button>
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
                    onClick={handleCreateAgent}
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

      {/* LLM Creation Modal */}
      <AnimatePresence>
        {showLLMModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowLLMModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold text-primary">Create New LLM Configuration</h2>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowLLMModal(false)}
                    className="w-8 h-8"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </Button>
                </div>
                
                {/* Embed LLMConfigForm without navigation */}
                <div className="space-y-6">
                  <LLMConfigForm 
                    editMode={false} 
                    hideHeader={true}
                    onSuccess={() => setShowLLMModal(false)}
                  />
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* MCP Creation Modal */}
      <AnimatePresence>
        {showMCPModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowMCPModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold text-primary">Create New MCP Client</h2>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowMCPModal(false)}
                    className="w-8 h-8"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </Button>
                </div>
                
                {/* Embed MCPClientForm without navigation */}
                <div className="space-y-6">
                  <MCPClientForm 
                    editMode={false}
                    hideHeader={true}
                    onSuccess={() => setShowMCPModal(false)}
                  />
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
