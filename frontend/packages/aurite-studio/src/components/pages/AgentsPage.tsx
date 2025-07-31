import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Users, Plus, Edit, Play, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAgentsWithConfigs, useExecuteAgent } from '@/hooks/useAgents';
import { UnifiedExecutionInterface } from '@/components/execution/UnifiedExecutionInterface';

export default function AgentsPage() {
  const navigate = useNavigate();
  
  // API Hooks
  const { data: agents = [], isLoading: agentsLoading } = useAgentsWithConfigs();
  const executeAgent = useExecuteAgent();
  
  // Execution Interface State
  const [executionInterface, setExecutionInterface] = useState<{
    isOpen: boolean;
    agentName: string | null;
  }>({ isOpen: false, agentName: null });

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

  const handleEditAgent = (agent: any) => {
    // Extract the actual name from the agent object
    const agentName = extractAgentName(agent);
    
    // Navigate to edit form
    navigate(`/agents/${encodeURIComponent(agentName)}/edit`);
  };

  const handleNewAgent = () => {
    // Navigate to new agent form
    navigate('/agents/new');
  };

  const handleRunAgent = (agent: any) => {
    const agentName = extractAgentName(agent);
    
    setExecutionInterface({
      isOpen: true,
      agentName: agentName
    });
  };

  return (
    <>
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
            <Button className="gap-2" onClick={handleNewAgent}>
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
              const agentName = extractAgentName(agent);

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
                      onClick={() => handleEditAgent(agent)}
                    >
                      <Edit className="h-3.5 w-3.5" />
                      Edit
                    </Button>
                    <Button 
                      size="sm" 
                      className="gap-1.5"
                      onClick={() => handleRunAgent(agent)}
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

      {/* Unified Execution Interface */}
      <UnifiedExecutionInterface
        agentName={executionInterface.agentName}
        isOpen={executionInterface.isOpen}
        onClose={() => setExecutionInterface({ isOpen: false, agentName: null })}
      />
    </>
  );
}
