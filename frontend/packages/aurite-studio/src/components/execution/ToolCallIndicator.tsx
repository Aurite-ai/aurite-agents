import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ToolCallIndicatorProps } from '@/types/execution';

export const ToolCallIndicator: React.FC<ToolCallIndicatorProps> = ({
  toolCall,
  onRetry,
  onViewDetails,
  showDetails = true
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getStatusIcon = () => {
    switch (toolCall.status) {
      case 'queued':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'executing':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = () => {
    switch (toolCall.status) {
      case 'queued':
        return 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20';
      case 'executing':
        return 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20';
      case 'completed':
        return 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20';
      case 'failed':
        return 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20';
      default:
        return 'border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-900/20';
    }
  };

  const formatDuration = (duration?: number): string => {
    if (!duration) return '';
    if (duration < 1000) return `${duration}ms`;
    return `${(duration / 1000).toFixed(1)}s`;
  };

  return (
    <div className={`border rounded-lg p-3 ${getStatusColor()}`}>
      {/* Tool Call Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="font-medium text-sm">🔧 {toolCall.name}</span>
          {toolCall.duration_ms && (
            <span className="text-xs text-muted-foreground">
              ({formatDuration(toolCall.duration_ms)})
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {toolCall.status === 'failed' && onRetry && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onRetry(toolCall)}
              className="h-6 px-2 text-xs"
            >
              Retry
            </Button>
          )}
          
          {showDetails && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsExpanded(!isExpanded)}
              className="h-6 w-6 p-0"
            >
              {isExpanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Tool Call Status */}
      <div className="mt-2 text-xs text-muted-foreground">
        Status: <span className="capitalize">{toolCall.status}</span>
        {toolCall.start_time && (
          <span className="ml-2">
            Started: {toolCall.start_time.toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Error Message */}
      {toolCall.status === 'failed' && toolCall.error && (
        <div className="mt-2 p-2 bg-red-100 dark:bg-red-900/30 rounded text-xs text-red-700 dark:text-red-300">
          Error: {toolCall.error}
        </div>
      )}

      {/* Expanded Details */}
      {isExpanded && showDetails && (
        <div className="mt-3 space-y-3 border-t pt-3">
          {/* Parameters */}
          {Object.keys(toolCall.parameters).length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground mb-1">Parameters:</h4>
              <pre className="text-xs bg-muted p-2 rounded overflow-x-auto whitespace-pre-wrap break-words">
                {JSON.stringify(toolCall.parameters, null, 2)}
              </pre>
            </div>
          )}

          {/* Result */}
          {toolCall.result && toolCall.status === 'completed' && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground mb-1">Result:</h4>
              <pre className="text-xs bg-muted p-2 rounded overflow-x-auto whitespace-pre-wrap break-words">
                {typeof toolCall.result === 'string' 
                  ? toolCall.result 
                  : JSON.stringify(toolCall.result, null, 2)
                }
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
