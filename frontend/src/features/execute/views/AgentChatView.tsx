import React, { useState, useEffect, useRef, type JSX } from 'react';
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
} from '@chatscope/chat-ui-kit-react';
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';
import StructuredResponseView from '../../../components/common/StructuredResponseView';
import ToolCallView from '../../../components/common/ToolCallView';
import ToolResultView from '../../../components/common/ToolResultView';
import StreamingMessageContentView from '../../../components/common/StreamingMessageContentView'; // Added for streaming

import {
  getSpecificComponentConfig,
  registerLlmConfigAPI,
  registerAgentAPI,
  executeAgentAPI
} from '../../../lib/apiClient';
import useAuthStore from '../../../store/authStore'; // Added for API key access

import type {
  AgentConfig,
  LLMConfig,
  AgentExecutionResult,
  AgentOutputContentBlock, // Added for streaming
} from '../../../types/projectManagement';

interface AgentChatViewProps {
  agentName: string;
  onClose: () => void;
}

// Updated ChatMessage interface for streaming
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'error' | 'system';
  content?: string | JSX.Element; // Optional for assistant messages that use contentBlocks
  contentBlocks?: AgentOutputContentBlock[]; // For assistant messages, built incrementally
  isStreaming?: boolean; // Indicates if the assistant message is actively streaming
  timestamp: Date;
}

const performPreExecutionRegistration = async (
  agentName: string,
  addSystemMessage: (text: string) => void,
  silent: boolean = false
): Promise<void> => {
  if (!silent) addSystemMessage(`Fetching configuration for agent: ${agentName}...`);
  const agentConfig: AgentConfig = await getSpecificComponentConfig("agents", agentName);
  if (!silent) addSystemMessage(`Agent configuration for ${agentName} fetched.`);

  if (agentConfig && agentConfig.llm_config_id) {
    if (!silent) addSystemMessage(`Fetching LLM configuration: ${agentConfig.llm_config_id}...`);
    const llmConfig: LLMConfig = await getSpecificComponentConfig("llms", agentConfig.llm_config_id);
    if (!silent) addSystemMessage(`LLM configuration ${agentConfig.llm_config_id} fetched. Registering...`);
    await registerLlmConfigAPI(llmConfig);
    if (!silent) addSystemMessage(`LLM configuration ${agentConfig.llm_config_id} registered/updated.`);
  } else if (agentConfig && !agentConfig.llm_config_id) {
    if (!silent) addSystemMessage(`Agent ${agentName} does not have an LLM configuration specified. Skipping LLM registration.`);
  }

  if (!silent) addSystemMessage(`Registering/updating agent: ${agentName}...`);
  await registerAgentAPI(agentConfig);
  if (!silent) addSystemMessage(`Agent ${agentName} registered/updated.`);
};

const AgentChatView: React.FC<AgentChatViewProps> = ({ agentName, onClose }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const eventSourceRef = useRef<EventSource | null>(null); // Added for EventSource management
  const [isInitializing, setIsInitializing] = useState<boolean>(false);
  const [chatError, setChatError] = useState<string | null>(null);

  // Updated addMessage function
  const addMessage = (
    role: ChatMessage['role'],
    contentOrId: string | JSX.Element, // ID for streaming assistant, content for others
    isStreamingOp: boolean = false,
    initialBlocksOp?: AgentOutputContentBlock[]
  ): string => {
    const id = (role === 'assistant' && isStreamingOp) ? contentOrId as string : Date.now().toString();
    const newMessage: ChatMessage = {
      id,
      role,
      timestamp: new Date(),
      isStreaming: role === 'assistant' ? isStreamingOp : false,
    };
    if (role === 'assistant' && isStreamingOp) {
      newMessage.contentBlocks = initialBlocksOp || [];
      // For streaming messages, content might be initially undefined or a placeholder
      // The actual rendering will be driven by contentBlocks via StreamingMessageContentView
    } else {
      newMessage.content = contentOrId as string | JSX.Element;
    }
    setMessages(prev => [...prev, newMessage]);
    return id;
  };

  useEffect(() => {
    const setupAgentSession = async () => {
      if (!agentName) return;
      setIsInitializing(true);
      setMessages([]);
      setChatError(null);
      // Ensure eventSource is closed if an agent switch occurs mid-stream
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      try {
        // System messages from registration are now silent by default
        await performPreExecutionRegistration(agentName, (msgText) => addMessage('system', msgText), true);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to initialize agent session.';
        addMessage('error', `Initialization Error: ${errorMessage}`);
        setChatError(errorMessage);
        console.error(`Error initializing agent ${agentName}:`, err);
      } finally {
        setIsInitializing(false);
      }
    };
    setupAgentSession();
  }, [agentName]);

  // Effect for cleaning up EventSource on component unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        console.log('EventSource closed on component unmount.');
      }
    };
  }, []);

  const handleSend = async (text: string) => {
    if (!text.trim() || isInitializing || isLoading) return;
    const userMessageContent = text;
    addMessage('user', userMessageContent); // Standard user message
    setIsLoading(true);
    setChatError(null);

    const assistantMessageId = Date.now().toString() + '-stream';
    addMessage('assistant', assistantMessageId, true, []); // Add placeholder for streaming

    // TODO: Retrieve system_prompt from agentConfig if available
    // const agentConfig: AgentConfig = await getSpecificComponentConfig("agents", agentName);
    // const systemPrompt = agentConfig?.system_prompt;
    // For now, system_prompt is not passed, adapt if backend requires/supports it for streaming endpoint

    const queryParams = new URLSearchParams({
      user_message: userMessageContent,
    });
    // if (systemPrompt) queryParams.append('system_prompt', systemPrompt);

    const { apiKey } = useAuthStore.getState();
    if (apiKey) {
      queryParams.append('api_key', apiKey);
    } else {
      // Handle missing API key - perhaps show an error or prevent the call
      // For now, this will result in a 401 if the backend strictly requires it and it's not in a cookie
      console.warn('API key is missing. Streaming call might fail if auth is required via query param.');
    }

    const url = `/api/agents/${agentName}/execute-stream?${queryParams.toString()}`;

    if (eventSourceRef.current) {
      eventSourceRef.current.close(); // Close any existing connection
    }

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('SSE connection opened.');
    };

    // Helper to update contentBlocks for the current streaming message
    const updateStreamingMessageBlocks = (updater: (blocks: AgentOutputContentBlock[]) => AgentOutputContentBlock[]) => {
      setMessages(prevMessages =>
        prevMessages.map(msg =>
          msg.id === assistantMessageId
            ? { ...msg, contentBlocks: updater(msg.contentBlocks || []) }
            : msg
        )
      );
    };

    eventSource.addEventListener('text_delta', (event) => {
      try {
        const eventData = JSON.parse(event.data as string);
        if (eventData.event_type === 'text_delta') {
          const { index, text_chunk } = eventData;
          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            if (index < newBlocks.length && newBlocks[index] && newBlocks[index].type === 'text') {
              // Append to existing text block
              newBlocks[index] = {
                ...newBlocks[index],
                text: (newBlocks[index].text || '') + text_chunk,
              };
            } else {
              // Create new text block or replace if type mismatch (should ideally not happen if backend sends consistent indices)
              // Ensure array is long enough
              while (newBlocks.length <= index) {
                newBlocks.push({ type: 'placeholder', text: '' }); // Should be replaced
              }
              newBlocks[index] = { type: 'text', text: text_chunk };
            }
            return newBlocks.filter(b => b.type !== 'placeholder'); // Clean up placeholders if any
          });
        }
      } catch (e) {
        console.error('Error parsing text_delta event:', e, event.data);
      }
    });

    eventSource.addEventListener('tool_use_start', (event) => {
      try {
        const eventData = JSON.parse(event.data as string);
        if (eventData.event_type === 'tool_use_start') {
          const { index, tool_name, tool_id } = eventData;
          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            // Ensure array is long enough
            while (newBlocks.length <= index) {
              newBlocks.push({ type: 'placeholder', text: '' }); // Should be replaced
            }
            newBlocks[index] = {
              type: 'tool_use',
              id: tool_id,
              name: tool_name,
              input: {}, // Initialize input as an empty object, to be filled by input_delta
            };
            return newBlocks.filter(b => b.type !== 'placeholder');
          });
        }
      } catch (e) {
        console.error('Error parsing tool_use_start event:', e, event.data);
      }
    });

    eventSource.addEventListener('tool_use_input_delta', (event) => {
      try {
        const eventData = JSON.parse(event.data as string);
        if (eventData.event_type === 'tool_use_input_delta') {
          const { index, json_chunk } = eventData;
          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            if (index < newBlocks.length && newBlocks[index] && newBlocks[index].type === 'tool_use') {
              const currentBlock = newBlocks[index] as any; // Cast for temporary field access
              // Ensure _accumulatedJsonInput is initialized
              const existingRawInput = currentBlock._accumulatedJsonInput || '';
              newBlocks[index] = {
                ...currentBlock,
                // Temporarily store accumulating JSON string.
                // ToolCallView will need to be aware of this or we parse on content_block_stop
                input: { ...(currentBlock.input || {}), _partialInput: ((currentBlock.input as any)?._partialInput || "") + json_chunk },
                _accumulatedJsonInput: existingRawInput + json_chunk,
              } as AgentOutputContentBlock; // Cast back to the original type
            } else {
              console.warn(`Received tool_use_input_delta for block at index ${index} which is not a tool_use block or doesn't exist.`);
            }
            return newBlocks;
          });
        }
      } catch (e) {
        console.error('Error parsing tool_use_input_delta event:', e, event.data);
      }
    });

    eventSource.addEventListener('content_block_stop', (event) => {
      try {
        const eventData = JSON.parse(event.data as string);
        if (eventData.event_type === 'content_block_stop') {
          const { index } = eventData;
          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            if (index < newBlocks.length && newBlocks[index] && newBlocks[index].type === 'tool_use') {
              const toolBlock = newBlocks[index] as any; // Cast for temporary field access
              if (toolBlock._accumulatedJsonInput) {
                try {
                  const parsedInput = JSON.parse(toolBlock._accumulatedJsonInput);
                  newBlocks[index] = {
                    ...toolBlock,
                    input: parsedInput, // Set the final parsed input
                  };
                  // Clean up temporary fields
                  delete (newBlocks[index] as any)._accumulatedJsonInput;
                  if ((newBlocks[index] as any).input?._partialInput) {
                    delete (newBlocks[index] as any).input._partialInput;
                  }
                  // If input was just {} and _partialInput was the only thing, clean that too.
                  if (Object.keys((newBlocks[index] as any).input).length === 0) {
                     delete (newBlocks[index] as any).input; // Or set to undefined, if ToolCallView handles it
                     // For now, let's ensure input is at least an empty object if it was meant to be an object
                     newBlocks[index].input = newBlocks[index].input || {};
                  }


                } catch (e) {
                  console.error('Failed to parse accumulated JSON for tool input:', toolBlock._accumulatedJsonInput, e);
                  // Keep the raw input or set an error state? For now, keep raw if parse fails.
                  newBlocks[index] = {
                    ...toolBlock,
                    input: { error: "Failed to parse tool input JSON", raw: toolBlock._accumulatedJsonInput },
                  };
                   delete (newBlocks[index]as any)._accumulatedJsonInput;
                   if ((newBlocks[index] as any).input?._partialInput) {
                    delete (newBlocks[index] as any).input._partialInput;
                  }
                }
              }
            }
            // Potentially handle other block types if needed, e.g., marking a text block as "complete"
            return newBlocks;
          });
        }
      } catch (e) {
        console.error('Error parsing content_block_stop event:', e, event.data);
      }
    });

    eventSource.addEventListener('tool_result', (event) => {
      try {
        const eventData = JSON.parse(event.data as string);
        if (eventData.event_type === 'tool_result') {
          // Assuming eventData structure: { index: number, tool_use_id: string, content: any, is_error: boolean, name?: string }
          const { index, tool_use_id, content, is_error, name } = eventData;
          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            // Ensure array is long enough for the new tool_result block
            while (newBlocks.length <= index) {
              newBlocks.push({ type: 'placeholder', text: '' }); // Should be replaced
            }
            newBlocks[index] = {
              type: 'tool_result',
              id: `tool_result_for_${tool_use_id}_${index}`, // Create a unique ID for the block itself
              tool_use_id: tool_use_id,
              content: content, // Content can be string or AgentOutputContentBlock[]
              is_error: is_error || false,
              name: name, // Optional name of the tool that produced result
            };
            return newBlocks.filter(b => b.type !== 'placeholder');
          });
        }
      } catch (e) {
        console.error('Error parsing tool_result event:', e, event.data);
      }
    });

    eventSource.addEventListener('tool_execution_error', (event) => {
      try {
        const eventData = JSON.parse(event.data as string);
        if (eventData.event_type === 'tool_execution_error') {
          // Assuming eventData: { index: number, tool_use_id: string, error_message: string, tool_name?: string }
          const { index, tool_use_id, error_message, tool_name } = eventData;
          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            // Ensure array is long enough
            while (newBlocks.length <= index) {
              newBlocks.push({ type: 'placeholder', text: '' });
            }
            // We can represent this as a tool_result block with is_error = true
            newBlocks[index] = {
              type: 'tool_result', // Use tool_result type for consistency with ToolResultView
              id: `tool_error_for_${tool_use_id}_${index}`, // Unique ID for the error block
              tool_use_id: tool_use_id,
              content: error_message || "Unknown tool execution error", // Error message as content
              is_error: true,
              name: tool_name, // Optional name of the tool that failed
            };
            return newBlocks.filter(b => b.type !== 'placeholder');
          });
          // Optionally, also add a general error message to the chat via addMessage('error', ...)
          // For now, relying on the block being rendered as an error.
        }
      } catch (e) {
        console.error('Error parsing tool_execution_error event:', e, event.data);
      }
    });

    eventSource.addEventListener('stream_end', (event) => {
      console.log('SSE stream_end:', event.data);
      setMessages(prevMessages =>
        prevMessages.map(msg =>
          msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
        )
      );
      setIsLoading(false);
      eventSourceRef.current?.close();
    });

    eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      addMessage('error', 'Streaming connection error.');
      setChatError('Streaming connection error. Check console for details.');
      setIsLoading(false);
      eventSourceRef.current?.close();
    };

    // Fallback for non-streaming API (to be removed once streaming is fully implemented and stable)
    // try {
    //   const executionResult: AgentExecutionResult = await executeAgentAPI(agentName, userMessageContent);
    //   // ... existing non-streaming logic ...
    // } catch (err) {
    //   // ... existing error handling ...
    // } finally {
    //   // setIsLoading(false); // This will be handled by stream_end or onerror
    // }
  };

  const mapRoleToDirection = (role: ChatMessage['role']): "incoming" | "outgoing" => {
    return role === 'user' ? 'outgoing' : 'incoming';
  };

  return (
    <div className="flex flex-col h-[calc(100vh-15rem)] bg-dracula-background p-0 rounded-lg shadow-md border border-dracula-current-line max-w-6xl mx-auto">
      <div className="flex justify-between items-center p-3 border-b border-dracula-comment bg-dracula-current-line rounded-t-lg">
        <h3 className="text-xl font-semibold text-dracula-cyan">Chat with: {agentName}</h3>
        <button
          onClick={onClose}
          className="text-sm bg-dracula-purple hover:bg-opacity-80 text-dracula-background py-1 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-dracula-pink"
        >
          Back to List
        </button>
      </div>
      <div style={{ position: "relative", flexGrow: 1, overflow: "hidden" }} className="bg-dracula-background">
        <MainContainer responsive className="h-full">
          <ChatContainer className="h-full">
            <MessageList className="bg-dracula-background">
              {messages.map((msg) => {
                if (msg.role === 'error') {
                  return (
                    <Message
                      key={msg.id}
                      model={{ sentTime: msg.timestamp.toISOString(), sender: msg.role, direction: "incoming", position: "single" }}
                    >
                      <Message.CustomContent>
                        <div className="p-2 rounded-md text-xs bg-dracula-red bg-opacity-70 text-white">
                          <strong>{msg.role.toUpperCase()}:</strong> {typeof msg.content === 'string' ? msg.content : 'Error content'}
                          <div className="text-xs opacity-80 mt-1">{msg.timestamp.toLocaleTimeString()}</div>
                        </div>
                      </Message.CustomContent>
                    </Message>
                  );
                }
                if (msg.role === 'user') {
                  return (
                    <Message
                      key={msg.id}
                      model={{
                        message: msg.content as string, // User content is always string for now
                        sentTime: msg.timestamp.toISOString(),
                        sender: msg.role,
                        direction: mapRoleToDirection(msg.role),
                        position: "single"
                      }}
                    />
                  );
                }
                if (msg.role === 'assistant') {
                  if (msg.contentBlocks && msg.contentBlocks.length > 0) {
                    // Streaming or streamed message with content blocks
                    return (
                      <Message
                        key={msg.id}
                        model={{ sentTime: msg.timestamp.toISOString(), sender: msg.role, direction: "incoming", position: "single" }}
                      >
                        <Message.CustomContent>
                          <StreamingMessageContentView blocks={msg.contentBlocks} />
                          {msg.isStreaming && <span className="text-xs text-dracula-comment italic"> (streaming...)</span>}
                        </Message.CustomContent>
                      </Message>
                    );
                  } else if (msg.content) { // Non-streaming assistant message with JSX or string content
                     if (typeof msg.content === 'string') {
                        return (
                          <Message
                            key={msg.id}
                            model={{
                              message: msg.content,
                              sentTime: msg.timestamp.toISOString(),
                              sender: msg.role,
                              direction: mapRoleToDirection(msg.role),
                              position: "single"
                            }}
                          />
                        );
                      } else { // msg.content is JSX.Element
                        return (
                          <Message
                            key={msg.id}
                            model={{ sentTime: msg.timestamp.toISOString(), sender: msg.role, direction: "incoming", position: "single" }}
                          >
                            <Message.CustomContent>
                              {msg.content}
                            </Message.CustomContent>
                          </Message>
                        );
                      }
                  } else if (msg.isStreaming) { // Placeholder for a streaming message that hasn't received content yet
                     return (
                      <Message
                        key={msg.id}
                        model={{ sentTime: msg.timestamp.toISOString(), sender: msg.role, direction: "incoming", position: "single" }}
                      >
                        <Message.CustomContent>
                           <span className="text-xs text-dracula-comment italic">Assistant is thinking...</span>
                        </Message.CustomContent>
                      </Message>
                    );
                  }
                }
                // System messages are silent
                return null;
              })}
            </MessageList>
            <MessageInput
              placeholder="Type message here..."
              onSend={handleSend}
              attachButton={false}
              disabled={isInitializing || isLoading}
              sendDisabled={isInitializing || isLoading}
              // className prop removed to let index.css handle all MessageInput styling
            />
          </ChatContainer>
        </MainContainer>
      </div>
      {chatError && !messages.some(m => m.role === 'error') && /* Show general chatError if not already shown as a message */
        <p className="text-sm text-dracula-red p-2 text-center">{chatError}</p>}
    </div>
  );
};

export default AgentChatView;
