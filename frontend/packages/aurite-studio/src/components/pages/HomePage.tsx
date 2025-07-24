import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Link as LinkIcon, Wand2, Loader2 } from 'lucide-react';
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
      onSuccess: (data) => {
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
    </div>
  );
}
