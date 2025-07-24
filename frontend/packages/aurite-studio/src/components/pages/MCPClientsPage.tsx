import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Database, Plus, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useClientsWithStatus } from '@/hooks/useClients';
import { MCPClientCard } from '@/components/MCPClientCard';

export default function MCPClientsPage() {
  const navigate = useNavigate();
  
  // API Hooks
  const { data: clients = [], isLoading: clientsLoading } = useClientsWithStatus();

  const handleNewMCPClient = () => {
    // Navigate to new MCP client form
    navigate('/mcp-clients/new');
  };

  const handleConfigureMCPClient = (clientName: string) => {
    // Navigate to edit form
    navigate(`/mcp-clients/${encodeURIComponent(clientName)}/edit`);
  };

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
        <Button className="gap-2" onClick={handleNewMCPClient}>
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
          <Button className="gap-2" onClick={handleNewMCPClient}>
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
              onConfigure={handleConfigureMCPClient}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
