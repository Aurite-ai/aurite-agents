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
    console.log('[handleSend] Invoked with text:', text, 'Timestamp:', Date.now());
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
          updateStreamingMessageBlocks(currentBlocks => { // currentBlocks is AgentOutputContentBlock[]
            const newBlocks = [...currentBlocks]; // Work with a copy
            let blockAtIndex = newBlocks[index];

            // Ensure block exists at index, initialize as 'text' if placeholder or new
            if (!blockAtIndex || blockAtIndex.type === 'placeholder') {
              while (newBlocks.length <= index) {
                // Push placeholders if needed to fill gaps, ensuring they have unique IDs
                newBlocks.push({ type: 'placeholder', text: '', id: `placeholder-${newBlocks.length}-${Date.now()}` });
              }
              newBlocks[index] = { type: 'text', text: '', id: `text-idx-${index}-${Date.now()}` };
              blockAtIndex = newBlocks[index];
            }

            // text_delta ensures the block is 'text' and appends the chunk immutably.
            const newText = (blockAtIndex.text || '') + text_chunk;
            const updatedBlockAtIndex = {
              ...blockAtIndex, // Spread existing properties
              type: 'text' as const, // Ensure type is 'text'
              text: newText,
              id: blockAtIndex.id || `text-idx-${index}-${Date.now()}`, // Ensure ID
            };
            newBlocks[index] = updatedBlockAtIndex; // Replace the old block with the new one

            console.log(`[text_delta] index: ${index}, chunk: "${text_chunk}"`);
            console.log('[text_delta] updatedBlockAtIndex:', JSON.stringify(updatedBlockAtIndex, null, 2));
            // console.log('[text_delta] newBlocks state before filter:', JSON.stringify(newBlocks, null, 2));

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
          updateStreamingMessageBlocks((currentContentBlocks: AgentOutputContentBlock[]) => {
            // Use flatMap to replace the block at 'index' with potentially multiple new blocks
            return currentContentBlocks.flatMap((block, i) => {
              if (i === index) {
                console.log(`[content_block_stop] Processing block at index: ${index}`, JSON.stringify(block, null, 2));
                const blockToProcess = block;
                const processedSubBlocks: AgentOutputContentBlock[] = [];

                if (blockToProcess.type === 'tool_use') {
                  const toolBlock = blockToProcess as any; // Cast for internal props
                  let finalizedInput = toolBlock.input;
                  if (toolBlock._accumulatedJsonInput) {
                    try {
                      finalizedInput = JSON.parse(toolBlock._accumulatedJsonInput);
                    } catch (e) {
                      console.error('Failed to parse accumulated JSON for tool input:', toolBlock._accumulatedJsonInput, e);
                      finalizedInput = { error: "Failed to parse tool input JSON", raw: toolBlock._accumulatedJsonInput };
                    }
                  }
                  // Return an array with the single finalized tool_use block
                  return [{
                    ...toolBlock,
                    input: finalizedInput,
                    _accumulatedJsonInput: undefined,
                    _partialInput: undefined,
                  }];
                } else if (blockToProcess.type === 'text' && blockToProcess.text) {
                  const rawText = blockToProcess.text;
                  const thinkingRegex = /<thinking>([\s\S]*?)<\/thinking>/;
                  const thinkingMatch = rawText.match(thinkingRegex);
                  let remainingText = rawText;

                  if (thinkingMatch && thinkingMatch[1]) {
                    const thinkingContent = thinkingMatch[1].trim();
                    if (thinkingContent) { // Only add if there's actual thinking content
                      processedSubBlocks.push({
                        type: 'thinking_finalized',
                        text: thinkingContent,
                        id: `${blockToProcess.id || 'block'}-${index}-thinking-${Date.now()}`,
                      });
                    }
                    remainingText = rawText.substring(thinkingMatch[0].length).trim();
                  }

                  if (remainingText) {
                    try {
                      const parsedJson = JSON.parse(remainingText);
                      processedSubBlocks.push({
                        type: 'final_response_data',
                        parsedJson: parsedJson,
                        text: remainingText, // Keep raw JSON string
                        id: `${blockToProcess.id || 'block'}-${index}-json-${Date.now()}`,
                      });
                    } catch (e) {
                      if (remainingText.trim()) { // Only add if non-empty, non-JSON
                        processedSubBlocks.push({
                          type: 'text',
                          text: remainingText.trim(),
                          id: `${blockToProcess.id || 'block'}-${index}-plaintext-${Date.now()}`,
                        });
                      }
                    }
                  }
                  // If processedSubBlocks is empty, it means the original text block was effectively empty
                  // (e.g., just "<thinking></thinking>" or whitespace). Returning an empty array removes it.
                  console.log(`[content_block_stop] index: ${index}, generated subBlocks:`, JSON.stringify(processedSubBlocks, null, 2));
                  return processedSubBlocks;
                }
                // If not 'tool_use' or processable 'text', return the original block in an array
                console.log(`[content_block_stop] index: ${index}, block not processed (kept as is):`, JSON.stringify(blockToProcess, null, 2));
                return [blockToProcess];
              }
              // Not the block at 'index', return as is in an array for flatMap
              return [block];
            }).filter(b => {
              const keep = b && b.type !== 'placeholder';
              // if (!keep) console.log('[content_block_stop] Filtering out block:', JSON.stringify(b, null, 2));
              return keep;
            }); // Ensure no null/undefined from flatMap and filter placeholders
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
      // content_block_stop is now responsible for all parsing and type conversion.
      // stream_end just marks the message as no longer streaming.
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
