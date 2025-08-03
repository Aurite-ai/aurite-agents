import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Settings, 
  Bot, 
  Brain, 
  Server, 
  MessageSquare, 
  Clock, 
  History,
  Zap,
  Shield
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AgentConfig } from '@/types/api.generated';

interface AgentConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: AgentConfig) => void;
  initialConfig?: Partial<AgentConfig>;
  agentName: string;
  availableLLMConfigs?: (string | { name: string; [key: string]: any })[];
  availableMCPServers?: (string | { name: string; [key: string]: any })[];
}

// Simple Switch component using checkbox
const Switch = ({ checked, onCheckedChange, id }: { checked: boolean; onCheckedChange: (checked: boolean) => void; id?: string }) => (
  <label className="relative inline-flex items-center cursor-pointer">
    <input
      type="checkbox"
      id={id}
      checked={checked}
      onChange={(e) => onCheckedChange(e.target.checked)}
      className="sr-only"
    />
    <div className={`relative w-11 h-6 rounded-full transition-colors ${checked ? 'bg-primary' : 'bg-gray-200'}`}>
      <div className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
    </div>
  </label>
);

// Simple Badge component
const Badge = ({ children, variant = 'default', className = '', onClick }: { children: React.ReactNode; variant?: 'default' | 'secondary' | 'destructive'; className?: string; onClick?: () => void }) => {
  const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
  const variantClasses = {
    default: 'bg-primary text-primary-foreground',
    secondary: 'bg-secondary text-secondary-foreground',
    destructive: 'bg-destructive text-destructive-foreground'
  };
  
  return (
    <span 
      className={`${baseClasses} ${variantClasses[variant]} ${className} ${onClick ? 'cursor-pointer hover:opacity-80' : ''}`}
      onClick={onClick}
    >
      {children}
    </span>
  );
};

// Simple Separator component
const Separator = () => <hr className="border-t border-border my-4" />;

export default function AgentConfigModal({
  isOpen,
  onClose,
  onSave,
  initialConfig = {},
  agentName,
  availableLLMConfigs = [],
  availableMCPServers = []
}: AgentConfigModalProps) {
  const [activeTab, setActiveTab] = useState('basic');
  
  // Form state
  const [config, setConfig] = useState<Partial<AgentConfig>>({
    type: 'agent',
    name: agentName,
    description: '',
    llm_config_id: '',
    model: '',
    temperature: 0.7,
    max_tokens: 4096,
    system_prompt: '',
    max_iterations: 10,
    include_history: false,
    auto: false,
    mcp_servers: [],
    exclude_components: [],
    ...initialConfig
  });

  // Update config when initialConfig changes
  useEffect(() => {
    setConfig({
      type: 'agent',
      name: agentName,
      description: '',
      llm_config_id: '',
      model: '',
      temperature: 0.7,
      max_tokens: 4096,
      system_prompt: '',
      max_iterations: 10,
      include_history: false,
      auto: false,
      mcp_servers: [],
      exclude_components: [],
      ...initialConfig
    });
  }, [initialConfig, agentName]);

  const handleSave = () => {
    // Clean up the config - remove empty values and ensure proper types
    const cleanConfig: AgentConfig = {
      type: 'agent',
      name: config.name || agentName,
      ...(config.description && { description: config.description }),
      ...(config.llm_config_id && { llm_config_id: config.llm_config_id }),
      ...(config.model && { model: config.model }),
      ...(config.temperature !== undefined && { temperature: Number(config.temperature) }),
      ...(config.max_tokens !== undefined && { max_tokens: Number(config.max_tokens) }),
      ...(config.system_prompt && { system_prompt: config.system_prompt }),
      ...(config.max_iterations !== undefined && { max_iterations: Number(config.max_iterations) }),
      ...(config.include_history !== undefined && { include_history: config.include_history }),
      ...(config.auto !== undefined && { auto: config.auto }),
      ...(config.mcp_servers && config.mcp_servers.length > 0 && { mcp_servers: config.mcp_servers }),
      ...(config.exclude_components && config.exclude_components.length > 0 && { exclude_components: config.exclude_components })
    };

    onSave(cleanConfig);
    onClose();
  };

  const handleMCPServerToggle = (serverName: string) => {
    setConfig(prev => ({
      ...prev,
      mcp_servers: prev.mcp_servers?.includes(serverName)
        ? prev.mcp_servers.filter(name => name !== serverName)
        : [...(prev.mcp_servers || []), serverName]
    }));
  };

  const handleExcludeComponentAdd = (component: string) => {
    if (component.trim() && !config.exclude_components?.includes(component.trim())) {
      setConfig(prev => ({
        ...prev,
        exclude_components: [...(prev.exclude_components || []), component.trim()]
      }));
    }
  };

  const handleExcludeComponentRemove = (component: string) => {
    setConfig(prev => ({
      ...prev,
      exclude_components: prev.exclude_components?.filter(c => c !== component) || []
    }));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      
      {/* Modal */}
      <div className="relative bg-card border border-border rounded-lg shadow-lg max-w-4xl w-full max-h-[90vh] mx-4 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                <Settings className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h2 className="text-xl font-semibold">Configure Agent</h2>
                <p className="text-sm text-muted-foreground">
                  Customize the behavior and capabilities of "{agentName}"
                </p>
              </div>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="px-6 py-3 border-b border-border">
          <div className="flex space-x-1">
            {[
              { id: 'basic', label: 'Basic', icon: Bot },
              { id: 'llm', label: 'LLM', icon: Brain },
              { id: 'behavior', label: 'Behavior', icon: Zap },
              { id: 'capabilities', label: 'Capabilities', icon: Server },
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'basic' && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <Bot className="h-4 w-4" />
                    Agent Identity
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="agent-name">Agent Name</Label>
                      <Input
                        id="agent-name"
                        value={config.name || ''}
                        onChange={(e) => setConfig(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="e.g., Data Processing Agent"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="agent-description">Description</Label>
                      <Input
                        id="agent-description"
                        value={config.description || ''}
                        onChange={(e) => setConfig(prev => ({ ...prev, description: e.target.value }))}
                        placeholder="Brief description of agent's purpose"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="system-prompt">System Prompt</Label>
                    <Textarea
                      id="system-prompt"
                      value={config.system_prompt || ''}
                      onChange={(e) => setConfig(prev => ({ ...prev, system_prompt: e.target.value }))}
                      placeholder="Define the agent's role, personality, and instructions..."
                      rows={6}
                      className="resize-none"
                    />
                    <p className="text-xs text-muted-foreground">
                      This prompt defines the agent's identity and behavior. Be specific about what the agent should do.
                    </p>
                  </div>
                </div>
          )}

          {activeTab === 'llm' && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <Brain className="h-4 w-4" />
                    Language Model Configuration
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="llm-config">LLM Configuration</Label>
                    <Select 
                      value={config.llm_config_id || ''} 
                      onValueChange={(value) => setConfig(prev => ({ ...prev, llm_config_id: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select an LLM configuration" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableLLMConfigs.map((llmConfig, index) => {
                          // Handle both string names and full config objects
                          const configName = typeof llmConfig === 'string' ? llmConfig : llmConfig.name;
                          const configKey = typeof llmConfig === 'string' ? llmConfig : `${llmConfig.name}-${index}`;
                          
                          return (
                            <SelectItem key={configKey} value={configName}>
                              {configName}
                            </SelectItem>
                          );
                        })}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Choose a predefined LLM configuration or use overrides below
                    </p>
                  </div>

                  <Separator />

                  <div className="space-y-4">
                    <h4 className="text-sm font-medium">LLM Overrides</h4>
                    <p className="text-xs text-muted-foreground">
                      These settings will override the selected LLM configuration above
                    </p>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="model-override">Model Override</Label>
                        <Input
                          id="model-override"
                          value={config.model || ''}
                          onChange={(e) => setConfig(prev => ({ ...prev, model: e.target.value }))}
                          placeholder="e.g., gpt-4, claude-3-opus"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="max-tokens">Max Tokens</Label>
                        <Input
                          id="max-tokens"
                          type="number"
                          min="1"
                          max="32768"
                          value={config.max_tokens || ''}
                          onChange={(e) => setConfig(prev => ({ ...prev, max_tokens: parseInt(e.target.value) || 4096 }))}
                          placeholder="4096"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="temperature">Temperature: {config.temperature}</Label>
                      <input
                        id="temperature"
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={config.temperature || 0.7}
                        onChange={(e) => setConfig(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
                      />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>Focused (0.0)</span>
                        <span>Balanced (1.0)</span>
                        <span>Creative (2.0)</span>
                      </div>
                    </div>
                  </div>
                </div>
          )}

          {activeTab === 'behavior' && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <Zap className="h-4 w-4" />
                    Agent Behavior Settings
                  </div>

                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="max-iterations">Max Iterations</Label>
                      <Input
                        id="max-iterations"
                        type="number"
                        min="1"
                        max="100"
                        value={config.max_iterations || ''}
                        onChange={(e) => setConfig(prev => ({ ...prev, max_iterations: parseInt(e.target.value) || 10 }))}
                        placeholder="10"
                      />
                      <p className="text-xs text-muted-foreground">
                        Maximum number of conversation turns before the agent stops automatically
                      </p>
                    </div>

                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <History className="h-4 w-4" />
                            <Label htmlFor="include-history">Include History</Label>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            Include entire conversation history in each turn
                          </p>
                        </div>
                        <Switch
                          id="include-history"
                          checked={config.include_history || false}
                          onCheckedChange={(checked) => setConfig(prev => ({ ...prev, include_history: checked }))}
                        />
                      </div>

                      <div className="flex items-center justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <Zap className="h-4 w-4" />
                            <Label htmlFor="auto-mode">Auto Mode</Label>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            Let LLM dynamically select capabilities at runtime
                          </p>
                        </div>
                        <Switch
                          id="auto-mode"
                          checked={config.auto || false}
                          onCheckedChange={(checked) => setConfig(prev => ({ ...prev, auto: checked }))}
                        />
                      </div>
                    </div>
                  </div>
                </div>
          )}

          {activeTab === 'capabilities' && (
                <div className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                      <Server className="h-4 w-4" />
                      MCP Servers
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Select which MCP servers this agent can use to access tools and resources
                    </p>

                    {availableMCPServers.length > 0 ? (
                      <div className="grid grid-cols-2 gap-2">
                        {availableMCPServers.map((server, index) => {
                          // Handle both string names and full server objects
                          const serverName = typeof server === 'string' ? server : server.name;
                          const serverKey = typeof server === 'string' ? server : `${server.name}-${index}`;
                          
                          return (
                            <div key={serverKey} className="flex items-center space-x-2">
                              <input
                                type="checkbox"
                                id={`mcp-${serverName}`}
                                checked={config.mcp_servers?.includes(serverName) || false}
                                onChange={() => handleMCPServerToggle(serverName)}
                                className="rounded"
                              />
                              <label htmlFor={`mcp-${serverName}`} className="text-sm">
                                {serverName}
                              </label>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="text-center py-4 text-muted-foreground">
                        <Server className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No MCP servers available</p>
                      </div>
                    )}

                    {config.mcp_servers && config.mcp_servers.length > 0 && (
                      <div className="space-y-2">
                        <Label>Selected Servers:</Label>
                        <div className="flex flex-wrap gap-1">
                          {config.mcp_servers.map((server) => (
                            <Badge key={server} variant="secondary" className="text-xs">
                              {server}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <Separator />

                  <div className="space-y-4">
                    <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                      <Shield className="h-4 w-4" />
                      Exclude Components
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Specific tools, prompts, or resources to exclude from this agent
                    </p>

                    <div className="space-y-2">
                      <div className="flex gap-2">
                        <Input
                          placeholder="Enter component name to exclude"
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleExcludeComponentAdd(e.currentTarget.value);
                              e.currentTarget.value = '';
                            }
                          }}
                        />
                        <Button 
                          type="button" 
                          variant="outline"
                          onClick={(e) => {
                            const input = e.currentTarget.parentElement?.querySelector('input');
                            if (input) {
                              handleExcludeComponentAdd(input.value);
                              input.value = '';
                            }
                          }}
                        >
                          Add
                        </Button>
                      </div>

                      {config.exclude_components && config.exclude_components.length > 0 && (
                        <div className="space-y-2">
                          <Label>Excluded Components:</Label>
                          <div className="flex flex-wrap gap-1">
                            {config.exclude_components.map((component) => (
                              <Badge 
                                key={component} 
                                variant="destructive" 
                                className="text-xs cursor-pointer"
                                onClick={() => handleExcludeComponentRemove(component)}
                              >
                                {component} ×
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-border flex justify-between">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} className="min-w-[100px]">
            Save Configuration
          </Button>
        </div>
      </div>
    </div>
  );
}