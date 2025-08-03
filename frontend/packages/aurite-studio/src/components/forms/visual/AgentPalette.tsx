import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Loader2, Bot } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface Agent {
  name: string;
  description?: string;
  [key: string]: any;
}

interface AgentPaletteProps {
  agents: Agent[];
  isLoading: boolean;
  onAgentDrop: (agentName: string, position: { x: number; y: number }) => void;
}

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

const AgentCard: React.FC<{ agent: Agent; onDragStart: (agentName: string) => void }> = ({ 
  agent, 
  onDragStart 
}) => {
  const agentName = extractAgentName(agent);
  
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('application/json', JSON.stringify({ agentName }));
    e.dataTransfer.effectAllowed = 'copy';
    onDragStart(agentName);
  };

  return (
    <div
      className="flex items-center gap-3 p-3 bg-muted/20 rounded-md border border-border hover:bg-muted/30 transition-colors cursor-grab active:cursor-grabbing"
      draggable
      onDragStart={handleDragStart}
      style={{
        opacity: 1,
        transform: 'translateY(0px)',
      }}
    >
      <div className="w-8 h-8 bg-primary/10 rounded-md flex items-center justify-center flex-shrink-0">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-foreground truncate">
          {agentName}
        </div>
        {agent.description && (
          <div className="text-xs text-muted-foreground truncate">
            {agent.description}
          </div>
        )}
      </div>
    </div>
  );
};

export default function AgentPalette({ agents, isLoading, onAgentDrop }: AgentPaletteProps): React.ReactElement {
  const [searchTerm, setSearchTerm] = useState('');
  const [draggedAgent, setDraggedAgent] = useState<string | null>(null);

  // Filter agents based on search term
  const filteredAgents = agents.filter(agent => {
    const agentName = extractAgentName(agent);
    const searchLower = searchTerm.toLowerCase();
    return (
      agentName.toLowerCase().includes(searchLower) ||
      (agent.description && agent.description.toLowerCase().includes(searchLower))
    );
  });

  const handleDragStart = (agentName: string) => {
    setDraggedAgent(agentName);
  };

  // Handle drop on the canvas (this will be called by the parent)
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const data = e.dataTransfer.getData('application/json');
    
    if (data) {
      try {
        const { agentName } = JSON.parse(data);
        const rect = e.currentTarget.getBoundingClientRect();
        const position = {
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
        };
        onAgentDrop(agentName, position);
        setDraggedAgent(null);
      } catch (error) {
        console.error('Error parsing drag data:', error);
      }
    }
  };

  const handleDragEnd = () => {
    setDraggedAgent(null);
  };

  return (
    <div className="w-80 bg-card border-r border-border flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="space-y-2">
          <h2 className="text-lg font-semibold text-primary">Available Agents</h2>
          <p className="text-sm text-muted-foreground">
            Drag agents to the canvas to build your workflow
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="p-6 border-b border-border">
        <div className="space-y-2">
          <Label htmlFor="agent-search" className="text-sm font-medium text-foreground">
            Search Agents
          </Label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              id="agent-search"
              placeholder="Search for agents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
      </div>

      {/* Agent List */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading agents...
            </div>
          </div>
        ) : filteredAgents.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-12 h-12 bg-muted/20 rounded-lg flex items-center justify-center mx-auto mb-3">
              <Bot className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">
              {searchTerm ? 'No agents found matching your search' : 'No agents available'}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredAgents.map((agent, index) => {
              const agentName = extractAgentName(agent);
              return (
                <motion.div
                  key={`${agentName}-${index}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <AgentCard
                    agent={agent}
                    onDragStart={handleDragStart}
                  />
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="p-6 border-t border-border">
        <div className="bg-muted/20 rounded-md p-3">
          <p className="text-xs text-muted-foreground">
            💡 <strong>Tips:</strong><br/>
            • Drag agents onto the canvas to add them<br/>
            • Connect: drag from bottom to top blue dots<br/>
            • Delete: hover over agent/connection and click ❌
          </p>
        </div>
      </div>
    </div>
  );
}