import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AgentConfig, ExecutionState, ExecutionRequest } from '@/types/execution';
import { useAgentConfig, useExecuteAgent, useExecuteAgentStream } from '@/hooks/useAgents';
import { InputPanel } from './InputPanel';
import { ExecutionPanel } from './ExecutionPanel';

interface UnifiedExecutionInterfaceProps {
  agentName: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export const UnifiedExecutionInterface: React.FC<UnifiedExecutionInterfaceProps> = ({
  agentName,
  isOpen,
  onClose
}) => {
  const [executionState, setExecutionState] = useState<ExecutionState>({
    status: 'idle',
    progress: 0,
    toolCalls: [],
    streamEvents: [],
    currentResponse: ''
  });

  // Fetch the real agent configuration
  const { data: agentConfig, isLoading: configLoading, error: configError } = useAgentConfig(
    agentName || '',
    !!agentName && isOpen
  );

  // Get the execute agent hooks
  const executeAgent = useExecuteAgent();
  const executeAgentStream = useExecuteAgentStream();

  const handleExecute = async (request: ExecutionRequest) => {
    if (!agentName) {
      console.error('❌ No agent name provided for execution');
      return;
    }

    console.log('🚀 Executing agent with request:', request);
    
    // Update execution state to show we're starting
    setExecutionState(prev => ({
      ...prev,
      status: 'starting',
      startTime: new Date(),
      userMessage: request.user_message,
      progress: 10,
      currentResponse: '', // Clear previous response
      streamEvents: [], // Clear previous stream events
      toolCalls: [], // Clear previous tool calls
      debugMode: request.debug_mode, // Track debug mode
      error: undefined, // Clear previous errors
      result: undefined // Clear previous results
    }));

    const apiRequest = {
      user_message: request.user_message,
      system_prompt: request.system_prompt
    };

    if (request.stream) {
      // Use streaming execution
      console.log('📡 Using streaming execution');
      
      await executeAgentStream.executeStream(
        agentName,
        apiRequest,
        // onStreamEvent
        (event) => {
          console.log('📨 Stream event:', event);
          
          // Extract text content from the stream event
          let newText = '';
          
          // Handle different event structures
          if (event.data && typeof event.data === 'object') {
            // Check for content in data object
            if (event.data.content) {
              newText = event.data.content;
            } else if (event.data.text) {
              newText = event.data.text;
            } else if (event.data.delta && event.data.delta.content) {
              newText = event.data.delta.content;
            }
          } else if (typeof event.data === 'string') {
            newText = event.data;
          } else if (event.content) {
            newText = event.content;
          } else if (event.text) {
            newText = event.text;
          }
          
          // Handle tool call events
          if (event.type === 'tool_call') {
            console.log('🔧 Tool call detected:', event);
            
            // Create a tool call from the event data
            const toolCall = {
              id: event.data.id || `tool_${Date.now()}`,
              name: event.data.name || event.data.function?.name || 'unknown_tool',
              parameters: event.data.parameters || event.data.function?.arguments || {},
              status: 'executing' as const,
              start_time: new Date()
            };
            
            setExecutionState(prev => ({
              ...prev,
              toolCalls: [...prev.toolCalls, toolCall],
              streamEvents: [...prev.streamEvents, {
                type: event.type,
                data: event,
                timestamp: new Date(),
                execution_id: 'stream'
              }]
            }));
            return;
          }
          
          // Handle tool output events
          if (event.type === 'tool_output') {
            console.log('🔧 Tool output detected:', event);
            
            setExecutionState(prev => ({
              ...prev,
              toolCalls: prev.toolCalls.map(toolCall => 
                toolCall.id === event.data.tool_call_id || toolCall.name === event.data.name
                  ? {
                      ...toolCall,
                      status: 'completed' as const,
                      end_time: new Date(),
                      duration_ms: toolCall.start_time ? Date.now() - toolCall.start_time.getTime() : 0,
                      result: event.data.result || event.data.output
                    }
                  : toolCall
              ),
              streamEvents: [...prev.streamEvents, {
                type: event.type,
                data: event,
                timestamp: new Date(),
                execution_id: 'stream'
              }]
            }));
            return;
          }
          
          // Check if this is a completion event
          if (event.type === 'llm_response_stop' || event.type === 'complete' || event.event === 'complete') {
            console.log('🏁 Stream completion detected:', event);
            
            // Handle completion immediately
            setExecutionState(prev => ({
              ...prev,
              status: 'completed',
              progress: 100,
              endTime: new Date(),
              streamEvents: [...prev.streamEvents, {
                type: event.type || 'completion',
                data: event,
                timestamp: new Date(),
                execution_id: 'stream'
              }],
              result: {
                execution_id: 'stream',
                session_id: 'stream-session',
                status: 'completed',
                final_response: {
                  role: 'assistant',
                  content: [{ type: 'text', text: prev.currentResponse }]
                },
                tool_calls: prev.toolCalls,
                metadata: {
                  start_time: prev.startTime?.toISOString() || new Date().toISOString(),
                  end_time: new Date().toISOString(),
                  duration_ms: prev.startTime ? Date.now() - prev.startTime.getTime() : 0,
                  token_usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0 },
                  tool_count: prev.toolCalls.length
                },
                history: []
              }
            }));
            return; // Don't process as regular stream event
          }
          
          // Update execution state with stream event
          setExecutionState(prev => ({
            ...prev,
            status: 'executing',
            progress: Math.min(prev.progress + 2, 90), // Gradually increase progress
            streamEvents: [...prev.streamEvents, {
              type: event.type || 'llm_response',
              data: event,
              timestamp: new Date(),
              execution_id: 'stream'
            }],
            // Accumulate streaming text
            currentResponse: newText ? prev.currentResponse + newText : prev.currentResponse
          }));
        },
        // onComplete
        (result) => {
          console.log('✅ Streaming execution completed:', result);
          
          setExecutionState(prev => ({
            ...prev,
            status: 'completed',
            progress: 100,
            endTime: new Date(),
            result: {
              execution_id: 'stream',
              session_id: request.session_id || 'unknown',
              status: 'completed',
              final_response: result.final_response,
              tool_calls: [],
              metadata: {
                start_time: prev.startTime?.toISOString() || new Date().toISOString(),
                end_time: new Date().toISOString(),
                duration_ms: prev.startTime ? Date.now() - prev.startTime.getTime() : 0,
                token_usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0 }
              },
              history: result.history || []
            },
            currentResponse: result.final_response?.content?.[0]?.text || result.final_response?.content || 'Execution completed'
          }));
        },
        // onError
        (error) => {
          console.error('❌ Streaming execution failed:', error);
          
          setExecutionState(prev => ({
            ...prev,
            status: 'failed',
            progress: 0,
            endTime: new Date(),
            error
          }));
        }
      );
    } else {
      // Use non-streaming execution
      console.log('📄 Using non-streaming execution');
      
      try {
        const result = await executeAgent.mutateAsync({
          agentName,
          request: apiRequest
        });

        console.log('✅ Non-streaming execution completed:', result);

        // Update execution state with completion
        setExecutionState(prev => ({
          ...prev,
          status: 'completed',
          progress: 100,
          endTime: new Date(),
          result: {
            execution_id: 'non-stream',
            session_id: request.session_id || 'unknown',
            status: 'completed',
            final_response: result.final_response,
            tool_calls: [],
            metadata: {
              start_time: prev.startTime?.toISOString() || new Date().toISOString(),
              end_time: new Date().toISOString(),
              duration_ms: prev.startTime ? Date.now() - prev.startTime.getTime() : 0,
              token_usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0 }
            },
            history: result.history || []
          },
          currentResponse: result.final_response?.content?.[0]?.text || result.final_response?.content || 'Execution completed'
        }));

      } catch (error) {
        console.error('❌ Non-streaming execution failed:', error);
        
        setExecutionState(prev => ({
          ...prev,
          status: 'failed',
          progress: 0,
          endTime: new Date(),
          error: error instanceof Error ? error.message : 'Unknown error occurred'
        }));
      }
    }
  };

  const handleClose = () => {
    // Reset execution state when closing
    setExecutionState({
      status: 'idle',
      progress: 0,
      toolCalls: [],
      streamEvents: [],
      currentResponse: ''
    });
    onClose();
  };

  if (!agentName || !isOpen) return null;

  // Convert the fetched agent config to our AgentConfig format
  const agent: AgentConfig | null = agentConfig ? {
    type: 'agent',
    name: agentConfig.name || agentName,
    description: agentConfig.description || agentConfig.system_prompt || 'No description available',
    llm_config_id: agentConfig.llm_config_id,
    model: agentConfig.model,
    temperature: agentConfig.temperature,
    max_tokens: agentConfig.max_tokens,
    system_prompt: agentConfig.system_prompt,
    max_iterations: agentConfig.max_iterations,
    include_history: agentConfig.include_history,
    auto: agentConfig.auto,
    mcp_servers: agentConfig.mcp_servers,
    exclude_components: agentConfig.exclude_components,
    _source_file: agentConfig._source_file,
    _context_path: agentConfig._context_path,
    _context_level: agentConfig._context_level,
    _project_name: agentConfig._project_name,
    _workspace_name: agentConfig._workspace_name
  } : null;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={handleClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-card border border-border rounded-lg w-[95vw] h-[90vh] max-w-7xl flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h2 className="text-xl font-semibold text-foreground">
                🤖 Execute Agent: {agentName}
              </h2>
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={handleClose}
                className="h-8 w-8"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            {/* Loading State */}
            {configLoading && (
              <div className="flex-1 flex items-center justify-center">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Loading agent configuration...
                </div>
              </div>
            )}

            {/* Error State */}
            {configError && (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center space-y-2">
                  <p className="text-destructive">Failed to load agent configuration</p>
                  <p className="text-sm text-muted-foreground">
                    {configError instanceof Error ? configError.message : 'Unknown error'}
                  </p>
                </div>
              </div>
            )}
            
            {/* Main Content - Side by Side */}
            {agent && !configLoading && !configError && (
              <div className="flex-1 flex overflow-hidden">
                {/* Left Panel - Input (40%) */}
                <div className="w-2/5 border-r border-border overflow-y-auto">
                  <InputPanel 
                    agent={agent}
                    onExecute={handleExecute}
                    disabled={executionState.status !== 'idle' && executionState.status !== 'completed' && executionState.status !== 'failed'}
                  />
                </div>
                
                {/* Right Panel - Execution (60%) */}
                <div className="flex-1 flex flex-col">
                  <ExecutionPanel
                    agent={agent}
                    executionState={executionState}
                    onStateChange={setExecutionState}
                  />
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
