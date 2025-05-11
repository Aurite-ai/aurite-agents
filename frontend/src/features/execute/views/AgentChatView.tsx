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
import StreamingMessageContentView from '../../../components/common/StreamingMessageContentView';

import {
  getSpecificComponentConfig,
  registerLlmConfigAPI,
  registerAgentAPI,
  executeAgentAPI
} from '../../../lib/apiClient';
import useAuthStore from '../../../store/authStore';

import type {
  AgentConfig,
  LLMConfig,
  AgentExecutionResult,
  AgentOutputContentBlock,
} from '../../../types/projectManagement';

interface AgentChatViewProps {
  agentName: string;
  onClose: () => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'error' | 'system';
  content?: string | JSX.Element;
  contentBlocks?: AgentOutputContentBlock[];
  isStreaming?: boolean;
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
  const eventSourceRef = useRef<EventSource | null>(null);
  const [isInitializing, setIsInitializing] = useState<boolean>(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const addMessage = (
    role: ChatMessage['role'],
    contentOrId: string | JSX.Element,
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
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      try {
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
    addMessage('user', userMessageContent);
    setIsLoading(true);
    setChatError(null);

    const assistantMessageId = Date.now().toString() + '-stream';
    addMessage('assistant', assistantMessageId, true, []);

    const queryParams = new URLSearchParams({
      user_message: userMessageContent,
    });
    const agentConfigFromStore: AgentConfig | undefined = (await getSpecificComponentConfig("agents", agentName));
    if (agentConfigFromStore?.system_prompt) {
        queryParams.append('system_prompt', agentConfigFromStore.system_prompt);
    }


    const { apiKey } = useAuthStore.getState();
    if (apiKey) {
      queryParams.append('api_key', apiKey);
    } else {
      console.warn('API key is missing. Streaming call might fail if auth is required via query param.');
    }

    const url = `/api/agents/${agentName}/execute-stream?${queryParams.toString()}`;

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('SSE connection opened.');
    };

    eventSource.onmessage = (event) => {
      console.log('SSE generic message received:', event);
      try {
        const parsedData = JSON.parse(event.data);
        console.log('SSE generic message data (parsed):', parsedData);
      } catch (e) {
        console.error('Error parsing generic SSE message data:', e, event.data);
      }
    };

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
        const { index, text_chunk } = eventData;
        if (typeof index === 'number' && typeof text_chunk === 'string') {
          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            if (index < newBlocks.length && newBlocks[index] && newBlocks[index].type === 'text') {
              newBlocks[index] = {
                ...newBlocks[index],
                text: (newBlocks[index].text || '') + text_chunk,
              };
            } else {
              while (newBlocks.length <= index) {
                newBlocks.push({ type: 'placeholder', text: '' });
              }
              newBlocks[index] = { type: 'text', text: text_chunk };
            }
            return newBlocks.filter(b => b.type !== 'placeholder');
          });
        }
      } catch (e) {
        console.error('Error parsing text_delta event:', e, event.data);
      }
    });

    eventSource.addEventListener('tool_use_start', (event) => {
      try {
        const eventData = JSON.parse(event.data as string);
        const { index, tool_name, tool_id } = eventData;
        if (typeof index === 'number' && tool_name && tool_id) {
          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            while (newBlocks.length <= index) {
              newBlocks.push({ type: 'placeholder', text: '' });
            }
            newBlocks[index] = {
              type: 'tool_use',
              id: tool_id,
              name: tool_name,
              input: {},
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
        const { index, json_chunk } = eventData;
        if (typeof index === 'number' && typeof json_chunk === 'string') {
          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            if (index < newBlocks.length && newBlocks[index] && newBlocks[index].type === 'tool_use') {
              const currentBlock = newBlocks[index] as any;
              const existingRawInput = currentBlock._accumulatedJsonInput || '';
              newBlocks[index] = {
                ...currentBlock,
                input: { ...(currentBlock.input || {}), _partialInput: ((currentBlock.input as any)?._partialInput || "") + json_chunk },
                _accumulatedJsonInput: existingRawInput + json_chunk,
              } as AgentOutputContentBlock;
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
        const { index } = eventData;
        if (typeof index === 'number') {
          updateStreamingMessageBlocks(blocks => {
            let newBlocks = [...blocks];
            if (index < newBlocks.length && newBlocks[index]) {
              const currentBlock = newBlocks[index];

              if (currentBlock.type === 'tool_use') {
                const toolBlock = currentBlock as any;
                if (toolBlock._accumulatedJsonInput) {
                  try {
                    const parsedInput = JSON.parse(toolBlock._accumulatedJsonInput);
                    newBlocks[index] = {
                      ...toolBlock,
                      input: parsedInput,
                    };
                    delete (newBlocks[index] as any)._accumulatedJsonInput;
                    if ((newBlocks[index] as any).input?._partialInput) {
                      delete (newBlocks[index] as any).input._partialInput;
                    }
                    if (Object.keys((newBlocks[index] as any).input).length === 0) {
                       newBlocks[index].input = {};
                    }
                  } catch (e) {
                    console.error('Failed to parse accumulated JSON for tool input:', toolBlock._accumulatedJsonInput, e);
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
              } else if (currentBlock.type === 'text' && currentBlock.text) {
                const textContent = currentBlock.text;
                const thinkingRegex = /<thinking>([\s\S]*?)<\/thinking>/;
                const thinkingMatch = textContent.match(thinkingRegex);

                let extractedThinkingText: string | undefined = undefined;
                let textForJsonParsing = textContent;

                if (thinkingMatch && thinkingMatch[1]) {
                  extractedThinkingText = thinkingMatch[1].trim();
                  textForJsonParsing = textContent.replace(thinkingRegex, '').trim();
                }

                let jsonParsedSuccessfully = false;
                let parsedJsonData: Record<string, any> | undefined = undefined;

                if (textForJsonParsing) {
                  try {
                    parsedJsonData = JSON.parse(textForJsonParsing);
                    jsonParsedSuccessfully = true;
                  } catch (jsonError) {
                    // Not valid JSON, or empty string after thinking tags
                  }
                }

                if (extractedThinkingText && jsonParsedSuccessfully && parsedJsonData) {
                  // Scenario 1: Both thinking and valid JSON found.
                  // Update current block to be ONLY thinking text.
                  newBlocks[index] = {
                    ...currentBlock,
                    id: currentBlock.id || `thinking-${Date.now()}`, // Ensure ID
                    type: 'text',
                    text: `<thinking>${extractedThinkingText}</thinking>`,
                  };
                  // Create a NEW block for final_response_data and PUSH it.
                  const finalResponseBlock: AgentOutputContentBlock = {
                    type: 'final_response_data',
                    id: `final-response-${Date.now()}`,
                    parsedJson: parsedJsonData,
                    thinkingText: undefined, // Thinking is separate
                    text: textForJsonParsing,
                  };
                  newBlocks.push(finalResponseBlock);
                } else if (jsonParsedSuccessfully && parsedJsonData) {
                  // Scenario 2: Only JSON found (no preceding thinking in this block).
                  newBlocks[index] = {
                    ...currentBlock,
                    id: currentBlock.id || `final-response-idx-${Date.now()}`, // Ensure ID
                    type: 'final_response_data',
                    parsedJson: parsedJsonData,
                    thinkingText: undefined,
                    text: textForJsonParsing,
                  };
                } else if (extractedThinkingText) {
                  // Scenario 3: Only thinking text found (rest wasn't valid JSON).
                  newBlocks[index] = {
                    ...currentBlock,
                    id: currentBlock.id || `thinking-only-${Date.now()}`, // Ensure ID
                    type: 'text',
                    // Keep original non-JSON text if any, after the thinking part
                    text: `<thinking>${extractedThinkingText}</thinking>` + (textForJsonParsing ? ` ${textForJsonParsing}` : ''),
                  };
                }
                // Scenario 4: Plain text, no thinking, not JSON - block remains as is from text_delta.
              }
            }
            return newBlocks.filter(b => b.type !== 'placeholder');
          });
        }
      } catch (e) {
        console.error('Error parsing content_block_stop event:', e, event.data);
      }
    });

    eventSource.addEventListener('tool_result', (event) => {
      try {
        const eventData = JSON.parse(event.data as string);
        const { tool_use_id, output, is_error, name } = eventData; // Removed index from destructuring
        if (tool_use_id && output !== undefined) {
          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            let resultBlockContent: string | AgentOutputContentBlock[] | Record<string, any>;
            if (typeof output === 'string') {
                resultBlockContent = output;
            } else if (Array.isArray(output) || typeof output === 'object' && output !== null) {
                resultBlockContent = output;
            } else {
                resultBlockContent = String(output);
            }
            const toolCallBlockIndex = newBlocks.findIndex(b => b.type === 'tool_use' && b.id === tool_use_id);

            const newToolResultBlock: AgentOutputContentBlock = {
              type: 'tool_result',
              id: `tool_result_for_${tool_use_id}_${Date.now()}`, // More robust unique ID
              tool_use_id: tool_use_id,
              content: resultBlockContent as any,
              is_error: is_error || false,
              name: name,
            };

            if (toolCallBlockIndex !== -1) {
              newBlocks.splice(toolCallBlockIndex + 1, 0, newToolResultBlock);
            } else {
              console.warn(`Tool call with id ${tool_use_id} not found for tool result. Appending result as fallback.`);
              newBlocks.push(newToolResultBlock);
            }
            // It's good practice to still filter placeholders if they could somehow be re-introduced,
            // though with splice and targeted insertion, it's less likely for this specific operation.
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
        const { tool_use_id, error_message, tool_name } = eventData; // Removed index
        if (tool_use_id && error_message) {
          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            const toolCallBlockIndex = newBlocks.findIndex(b => b.type === 'tool_use' && b.id === tool_use_id);

            const newToolErrorBlock: AgentOutputContentBlock = {
              type: 'tool_result', // Representing an error as a type of tool result
              id: `tool_error_for_${tool_use_id}_${Date.now()}`, // Unique ID
              tool_use_id: tool_use_id,
              content: error_message || "Unknown tool execution error",
              is_error: true,
              name: tool_name,
            };

            if (toolCallBlockIndex !== -1) {
              newBlocks.splice(toolCallBlockIndex + 1, 0, newToolErrorBlock);
            } else {
              console.warn(`Tool call with id ${tool_use_id} not found for tool execution error. Appending error as fallback.`);
              newBlocks.push(newToolErrorBlock);
            }
            return newBlocks.filter(b => b.type !== 'placeholder');
          });
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
                        message: msg.content as string,
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
                  } else if (msg.content) {
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
                      } else {
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
                  } else if (msg.isStreaming) {
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
                return null;
              })}
            </MessageList>
            <MessageInput
              placeholder="Type message here..."
              onSend={handleSend}
              attachButton={false}
              disabled={isInitializing || isLoading}
              sendDisabled={isInitializing || isLoading}
            />
          </ChatContainer>
        </MainContainer>
      </div>
      {chatError && !messages.some(m => m.role === 'error') &&
        <p className="text-sm text-dracula-red p-2 text-center">{chatError}</p>}
    </div>
  );
};

export default AgentChatView;
