import React from 'react';
import { motion } from 'framer-motion';
import { Wifi, WifiOff, Loader2 } from 'lucide-react';
import { useApiConnection, ConnectionStatus as Status } from '@/hooks/useApiConnection';

interface ConnectionStatusProps {
  isExpanded: boolean;
}

export function ConnectionStatus({ isExpanded }: ConnectionStatusProps) {
  const { status, lastChecked, checkConnection } = useApiConnection();

  const getStatusConfig = (status: Status) => {
    switch (status) {
      case 'connected':
        return {
          color: 'text-green-500',
          bgColor: 'bg-green-500',
          icon: Wifi,
          text: 'API Connected',
        };
      case 'disconnected':
        return {
          color: 'text-red-500',
          bgColor: 'bg-red-500',
          icon: WifiOff,
          text: 'API Disconnected',
        };
      case 'checking':
        return {
          color: 'text-yellow-500',
          bgColor: 'bg-yellow-500',
          icon: Loader2,
          text: 'Checking...',
        };
    }
  };

  const config = getStatusConfig(status);
  const StatusIcon = config.icon;

  const formatLastChecked = (date: Date | null) => {
    if (!date) return '';
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    
    if (minutes < 1) return 'Just now';
    if (minutes === 1) return '1 minute ago';
    return `${minutes} minutes ago`;
  };

  return (
    <div className="group relative">
      <motion.button
        onClick={checkConnection}
        className={`${
          isExpanded ? 'w-full justify-start gap-3 h-11 px-4' : 'w-12 h-12'
        } rounded-xl flex items-center justify-center transition-all duration-200 hover:bg-accent/50 cursor-pointer`}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        {/* Status dot and icon */}
        <div className="relative flex items-center justify-center">
          <div className={`w-2 h-2 rounded-full ${config.bgColor} absolute -top-1 -right-1 z-10`} />
          <StatusIcon 
            className={`h-5 w-5 ${config.color} ${status === 'checking' ? 'animate-spin' : ''}`} 
          />
        </div>

        {/* Text for expanded state */}
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="flex flex-col items-start"
          >
            <span className={`text-sm font-medium ${config.color}`}>
              {config.text}
            </span>
            {lastChecked && status !== 'checking' && (
              <span className="text-xs text-muted-foreground">
                {formatLastChecked(lastChecked)}
              </span>
            )}
          </motion.div>
        )}
      </motion.button>

      {/* Tooltip for collapsed state */}
      {!isExpanded && (
        <div className="absolute left-16 top-1/2 -translate-y-1/2 bg-popover text-popover-foreground px-3 py-2 rounded-md text-sm opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 border border-border shadow-md">
          <div className="flex flex-col gap-1">
            <span className={`font-medium ${config.color}`}>
              {config.text}
            </span>
            {lastChecked && status !== 'checking' && (
              <span className="text-xs text-muted-foreground">
                Last checked: {formatLastChecked(lastChecked)}
              </span>
            )}
            <span className="text-xs text-muted-foreground">
              Click to refresh
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
