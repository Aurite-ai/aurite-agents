import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Bug, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ToolCall, StreamEvent } from '@/types/execution';
import { ToolCallIndicator } from './ToolCallIndicator';

interface DebugSectionProps {
  toolCalls: ToolCall[];
  streamEvents: StreamEvent[];
  isVisible: boolean;
}

export const DebugSection: React.FC<DebugSectionProps> = ({
  toolCalls,
  streamEvents,
  isVisible
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'tools' | 'events'>('tools');

  if (!isVisible || (toolCalls.length === 0 && streamEvents.length === 0)) {
    return null;
  }

  const toolCallEvents = streamEvents.filter(event => 
    event.type === 'tool_call' || event.type === 'tool_output'
  );

  const handleCopyDebugData = () => {
    const debugData = {
      toolCalls,
      toolCallEvents,
      timestamp: new Date().toISOString()
    };
    navigator.clipboard.writeText(JSON.stringify(debugData, null, 2));
  };

  return (
    <div className="border border-orange-200 bg-orange-50 dark:border-orange-800 dark:bg-orange-900/20 rounded-lg">
      {/* Debug Header */}
      <div className="flex items-center justify-between p-3 border-b border-orange-200 dark:border-orange-800">
        <div className="flex items-center gap-2">
          <Bug className="h-4 w-4 text-orange-600 dark:text-orange-400" />
          <span className="font-medium text-sm text-orange-800 dark:text-orange-200">
            Debug Information
          </span>
          <span className="text-xs text-orange-600 dark:text-orange-400 bg-orange-100 dark:bg-orange-900/40 px-2 py-0.5 rounded">
            {toolCalls.length} tool calls • {toolCallEvents.length} events
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopyDebugData}
            className="h-6 px-2 text-xs border-orange-300 text-orange-700 hover:bg-orange-100 dark:border-orange-700 dark:text-orange-300 dark:hover:bg-orange-900/40"
          >
            <Copy className="h-3 w-3 mr-1" />
            Copy Debug Data
          </Button>
          
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-6 w-6 p-0 text-orange-700 hover:bg-orange-100 dark:text-orange-300 dark:hover:bg-orange-900/40"
          >
            {isExpanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </Button>
        </div>
      </div>

      {/* Debug Content */}
      {isExpanded && (
        <div className="p-3 space-y-3">
          {/* Tab Navigation */}
          <div className="flex gap-1 bg-orange-100 dark:bg-orange-900/40 p-1 rounded">
            <button
              onClick={() => setActiveTab('tools')}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                activeTab === 'tools'
                  ? 'bg-white dark:bg-orange-800 text-orange-800 dark:text-orange-200 shadow-sm'
                  : 'text-orange-600 dark:text-orange-400 hover:text-orange-800 dark:hover:text-orange-200'
              }`}
            >
              Tool Calls ({toolCalls.length})
            </button>
            <button
              onClick={() => setActiveTab('events')}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                activeTab === 'events'
                  ? 'bg-white dark:bg-orange-800 text-orange-800 dark:text-orange-200 shadow-sm'
                  : 'text-orange-600 dark:text-orange-400 hover:text-orange-800 dark:hover:text-orange-200'
              }`}
            >
              Stream Events ({toolCallEvents.length})
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'tools' && (
            <div className="space-y-2">
              {toolCalls.length > 0 ? (
                toolCalls.map((toolCall) => (
                  <ToolCallIndicator
                    key={toolCall.id}
                    toolCall={toolCall}
                    showDetails={true}
                  />
                ))
              ) : (
                <div className="text-xs text-orange-600 dark:text-orange-400 italic p-2 bg-orange-100 dark:bg-orange-900/40 rounded">
                  No tool calls detected in this execution
                </div>
              )}
            </div>
          )}

          {activeTab === 'events' && (
            <div className="space-y-2">
              {toolCallEvents.length > 0 ? (
                toolCallEvents.map((event, index) => (
                  <div
                    key={index}
                    className="bg-white dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded p-2"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-orange-800 dark:text-orange-200">
                          {event.type}
                        </span>
                        <span className="text-xs text-orange-600 dark:text-orange-400">
                          {event.timestamp.toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                    <pre className="text-xs bg-orange-50 dark:bg-orange-900/40 p-2 rounded overflow-x-auto text-orange-800 dark:text-orange-200 whitespace-pre-wrap break-words">
                      {JSON.stringify(event.data, null, 2)}
                    </pre>
                  </div>
                ))
              ) : (
                <div className="text-xs text-orange-600 dark:text-orange-400 italic p-2 bg-orange-100 dark:bg-orange-900/40 rounded">
                  No tool call events detected in this execution
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
