import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Edit, Play, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  useClientConfigComplete,
  useRegisterMCPServer,
  useUnregisterMCPServer,
} from '@/hooks/useClients';

interface MCPClientCardProps {
  client: {
    name: string;
    configFile?: string;
    status: string;
    isActive: boolean;
  };
  index: number;
  onConfigure: (clientName: string) => void;
}

export const MCPClientCard: React.FC<MCPClientCardProps> = ({ client, index, onConfigure }) => {
  const clientName =
    typeof client.name === 'string' ? client.name : (client.name as any)?.name || 'Unknown Client';

  // Check if configuration is complete
  const { data: configStatus, isLoading: configLoading } = useClientConfigComplete(clientName);
  const isConfigComplete = configStatus?.isComplete || false;

  // Use the actual React Query mutations for proper state management
  const registerMutation = useRegisterMCPServer();
  const unregisterMutation = useUnregisterMCPServer();

  // State to maintain minimum orange dot duration
  const [showConnecting, setShowConnecting] = useState(false);

  // Check if this specific server is in a loading state
  const isConnecting = registerMutation.isPending && registerMutation.variables === clientName;
  const isDisconnecting =
    unregisterMutation.isPending && unregisterMutation.variables === clientName;

  // Handle connecting state with minimum duration
  useEffect(() => {
    if (isConnecting) {
      setShowConnecting(true);
    } else if (showConnecting) {
      // Keep orange dot visible for minimum 800ms
      const timer = setTimeout(() => {
        setShowConnecting(false);
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [isConnecting, showConnecting, clientName]);

  // Determine connection status for dot color
  const getStatusDotColor = () => {
    if (showConnecting || isConnecting) {
      return 'bg-orange-500';
    } else if (isDisconnecting) {
      return 'bg-orange-500';
    } else if (client.status === 'connected') {
      return 'bg-green-500';
    }
    return 'bg-red-500';
  };

  // Handle connect using the mutation
  const handleConnect = () => {
    registerMutation.mutate(clientName);
  };

  // Handle disconnect using the mutation
  const handleDisconnect = () => {
    unregisterMutation.mutate(clientName);
  };

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
          <div
            className={`w-2 h-2 rounded-full transition-colors duration-200 ${getStatusDotColor()}`}
          />
        </div>
        <p className="text-sm text-muted-foreground">
          {client.configFile ? 'Configured' : 'Configuration pending'}
        </p>
        <p className="text-xs text-muted-foreground capitalize">
          Status:{' '}
          {isConnecting ? 'connecting...' : isDisconnecting ? 'disconnecting...' : client.status}
        </p>
      </div>

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={() => onConfigure(clientName)}
        >
          <Edit className="h-3.5 w-3.5" />
          Configure
        </Button>

        {/* Show Connect/Disconnect only for complete configurations */}
        {configLoading ? (
          <Button size="sm" variant="secondary" className="gap-1.5" disabled>
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Checking...
          </Button>
        ) : isConfigComplete ? (
          <Button
            size="sm"
            className="gap-1.5"
            onClick={() => {
              if (client.status === 'connected') {
                handleDisconnect();
              } else {
                handleConnect();
              }
            }}
            disabled={isConnecting || isDisconnecting}
          >
            {isConnecting || isDisconnecting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            {isConnecting
              ? 'Connecting...'
              : isDisconnecting
                ? 'Disconnecting...'
                : client.status === 'connected'
                  ? 'Disconnect'
                  : 'Connect'}
          </Button>
        ) : (
          <Button size="sm" variant="secondary" className="gap-1.5" disabled>
            <Edit className="h-3.5 w-3.5" />
            Configure First
          </Button>
        )}
      </div>
    </motion.div>
  );
};
