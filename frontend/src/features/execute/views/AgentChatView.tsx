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
  const currentStreamingTextInfoRef = useRef<{ blockId: string | null, llmMessageIndex: number | null }>({ blockId: null, llmMessageIndex: null });

  const generateUniqueBlockId = (typeHint: string = 'block'): string => {
    return `${typeHint}-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
  };

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
    console.log('[handleSend] Invoked with text:', text, 'Timestamp:', Date.now());
    if (!text.trim() || isInitializing || isLoading) return;
    const userMessageContent = text;
    addMessage('user', userMessageContent);
    setIsLoading(true);
    setChatError(null);

    const assistantMessageId = Date.now().toString() + '-stream';
    addMessage('assistant', assistantMessageId, true, []);

    // Reset current streaming text info at the beginning of a new send
    currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };

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
        const { index: llmMessageIndex, text_chunk } = eventData;

        if (typeof llmMessageIndex === 'number' && typeof text_chunk === 'string') {
          updateStreamingMessageBlocks(currentBlocks => {
            let newBlocks = [...currentBlocks];
            if (currentStreamingTextInfoRef.current.blockId && currentStreamingTextInfoRef.current.llmMessageIndex === llmMessageIndex) {
              const blockToUpdateId = currentStreamingTextInfoRef.current.blockId;
              let blockFoundAndUpdated = false;
              newBlocks = newBlocks.map(b => {
                if (b.id === blockToUpdateId && b.type === 'text' && !b._finalized) {
                  blockFoundAndUpdated = true;
                  return { ...b, text: (b.text || '') + text_chunk };
                }
                return b;
              });
              // If the blockId was set but not found (e.g., already finalized and replaced), start a new block
              if (!blockFoundAndUpdated) {
                const newBlockId = generateUniqueBlockId(`text-cont-${llmMessageIndex}`);
                const newTextBlock: AgentOutputContentBlock = {
                  type: 'text',
                  text: text_chunk,
                  id: newBlockId,
                  _originalIndex: llmMessageIndex,
                };
                newBlocks.push(newTextBlock);
                currentStreamingTextInfoRef.current = { blockId: newBlockId, llmMessageIndex };
              }
            } else {
              const newBlockId = generateUniqueBlockId(`text-new-${llmMessageIndex}`);
              const newTextBlock: AgentOutputContentBlock = {
                type: 'text',
                text: text_chunk,
                id: newBlockId,
                _originalIndex: llmMessageIndex,
              };
              newBlocks.push(newTextBlock);
              currentStreamingTextInfoRef.current = { blockId: newBlockId, llmMessageIndex };
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
        const { index: llmMessageIndex, tool_name, tool_id } = eventData;
        if (typeof llmMessageIndex === 'number' && tool_name && tool_id) {
          currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };

          updateStreamingMessageBlocks(blocks => {
            const newToolUseBlock: AgentOutputContentBlock = {
              type: 'tool_use',
              id: tool_id,
              name: tool_name,
              input: {},
              _originalIndex: llmMessageIndex,
            };
            return [...blocks.filter(b => b.type !== 'placeholder'), newToolUseBlock];
          });
        }
      } catch (e) {
        console.error('Error parsing tool_use_start event:', e, event.data);
      }
    });

    eventSource.addEventListener('tool_use_input_delta', (event) => {
      try {
        const eventData = JSON.parse(event.data as string);
        const { tool_id, json_chunk, index: llmMessageIndex } = eventData;

        if (tool_id && typeof json_chunk === 'string') {
          updateStreamingMessageBlocks(blocks =>
            blocks.map(b => {
              if (b.type === 'tool_use' && b.id === tool_id && !b._inputFinalized) {
                const currentBlock = b as any;
                const existingRawInput = currentBlock._accumulatedJsonInput || '';
                return {
                  ...currentBlock,
                  _accumulatedJsonInput: existingRawInput + json_chunk,
                };
              }
              return b;
            })
          );
        } else if (typeof llmMessageIndex === 'number' && typeof json_chunk === 'string') {
            console.warn(`[tool_use_input_delta] Received event with llmMessageIndex (${llmMessageIndex}) but no tool_id. Attempting to update based on _originalIndex.`);
            updateStreamingMessageBlocks(blocks => {
                return blocks.map(b => {
                    if (b.type === 'tool_use' && (b as any)._originalIndex === llmMessageIndex && !(b as any)._inputFinalized) {
                        const currentBlock = b as any;
                        const existingRawInput = currentBlock._accumulatedJsonInput || '';
                        return {
                            ...currentBlock,
                            _accumulatedJsonInput: existingRawInput + json_chunk,
                        };
                    }
                    return b;
                });
            });
        }
      } catch (e) {
        console.error('Error parsing tool_use_input_delta event:', e, event.data);
      }
    });

    eventSource.addEventListener('content_block_stop', (event) => {
      try {
        const eventData = JSON.parse(event.data as string);
        const { index: llmMessageIndex, content_type, tool_id: stopped_tool_id } = eventData;

        if (typeof llmMessageIndex === 'number') {
          const streamingTextInfo = { ...currentStreamingTextInfoRef.current };
          // Reset ref for the next text stream only if the stopped block was the one being streamed
          if (content_type === 'text' && streamingTextInfo.blockId && streamingTextInfo.llmMessageIndex === llmMessageIndex) {
            currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };
          }

          updateStreamingMessageBlocks(currentBlocks => {
            return currentBlocks.flatMap(block => {
              // Case 1: Finalizing a text block that was being streamed
              if (content_type === 'text' && streamingTextInfo.blockId && block.id === streamingTextInfo.blockId && block.type === 'text' && !block._finalized) {
                const processedSubBlocks: AgentOutputContentBlock[] = [];
                if (block.text) {
                  const rawText = block.text;
                  const thinkingRegex = /<thinking>([\s\S]*?)<\/thinking>/gi;
                  let lastIndex = 0;
                  let match;
                  while ((match = thinkingRegex.exec(rawText)) !== null) {
                    const textBefore = rawText.substring(lastIndex, match.index).trim();
                    if (textBefore) {
                      processedSubBlocks.push({ type: 'text', text: textBefore, id: generateUniqueBlockId('text-pre-thinking'), _finalized: true, _originalIndex: block._originalIndex });
                    }
                    const thinkingContent = match[1].trim();
                    if (thinkingContent) {
                      processedSubBlocks.push({ type: 'thinking_finalized', text: thinkingContent, id: generateUniqueBlockId('thinking'), _finalized: true, _originalIndex: block._originalIndex });
                    }
                    lastIndex = thinkingRegex.lastIndex;
                  }
                  const remainingText = rawText.substring(lastIndex).trim();
                  if (remainingText) {
                    try {
                      const parsedJson = JSON.parse(remainingText);
                      processedSubBlocks.push({ type: 'final_response_data', parsedJson, text: remainingText, id: generateUniqueBlockId('final-json'), _finalized: true, _originalIndex: block._originalIndex });
                    } catch (e) {
                      processedSubBlocks.push({ type: 'text', text: remainingText, id: generateUniqueBlockId('final-text'), _finalized: true, _originalIndex: block._originalIndex });
                    }
                  }
                }
                // If processedSubBlocks is empty (e.g. original text was only <thinking></thinking> or whitespace), return empty array to remove original block.
                return processedSubBlocks;
              }
              // Case 2: Finalizing a tool_use block's input
              else if (content_type === 'tool_use' && block.type === 'tool_use' && block.id === stopped_tool_id && !block._inputFinalized) {
                const toolBlock = block as any;
                let finalizedInput = toolBlock.input;
                if (toolBlock._accumulatedJsonInput) {
                  try {
                    finalizedInput = JSON.parse(toolBlock._accumulatedJsonInput);
                  } catch (e) {
                    console.error('Failed to parse accumulated JSON for tool input:', toolBlock._accumulatedJsonInput, e);
                    finalizedInput = { error: "Failed to parse tool input JSON", raw: toolBlock._accumulatedJsonInput };
                  }
                }
                return [{
                  ...toolBlock,
                  input: finalizedInput,
                  _accumulatedJsonInput: undefined,
                  _inputFinalized: true, // Mark as finalized
                }];
              }
              // Otherwise, keep the block as is
              return [block];
            }).filter(b => b.type !== 'placeholder');
          });
        }
      } catch (e) {
        console.error('Error parsing content_block_stop event:', e, event.data);
      }
    });

    eventSource.addEventListener('tool_result', (event) => {
      try {
        const eventData = JSON.parse(event.data as string);
        const { tool_use_id, output, is_error, name } = eventData;
        if (tool_use_id && output !== undefined) {
          currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };

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
              id: generateUniqueBlockId(`tool-result-${tool_use_id}`),
              tool_use_id: tool_use_id,
              content: resultBlockContent as any,
              is_error: is_error || false,
              name: name,
              _finalized: true,
            };

            if (toolCallBlockIndex !== -1) {
              newBlocks.splice(toolCallBlockIndex + 1, 0, newToolResultBlock);
            } else {
              console.warn(`Tool call with id ${tool_use_id} not found for tool result. Appending result as fallback.`);
              newBlocks.push(newToolResultBlock);
            }
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
        const { tool_use_id, error_message, tool_name } = eventData;
        if (tool_use_id && error_message) {
          currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };

          updateStreamingMessageBlocks(blocks => {
            const newBlocks = [...blocks];
            const toolCallBlockIndex = newBlocks.findIndex(b => b.type === 'tool_use' && b.id === tool_use_id);

            const newToolErrorBlock: AgentOutputContentBlock = {
              type: 'tool_result',
              id: generateUniqueBlockId(`tool-error-${tool_use_id}`),
              tool_use_id: tool_use_id,
              content: error_message || "Unknown tool execution error",
              is_error: true,
              name: tool_name,
              _finalized: true,
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
      currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };

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
