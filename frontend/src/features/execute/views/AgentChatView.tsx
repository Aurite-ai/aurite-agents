import React, { useState, useEffect, useRef, type JSX } from 'react';
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
} from '@chatscope/chat-ui-kit-react';
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';
// import StructuredResponseView from '../../../components/common/StructuredResponseView';
// import ToolCallView from '../../../components/common/ToolCallView';
// import ToolResultView from '../../../components/common/ToolResultView';
import StreamingMessageContentView from '../../../components/common/StreamingMessageContentView'; // Simplified version

import {
  getSpecificComponentConfig,
  registerLlmConfigAPI,
  registerAgentAPI,
  streamAgentExecution, // Import the function
} from '../../../lib/apiClient';

import type {
  AgentConfig,
  LLMConfig,
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
    const id = (role === 'assistant' && isStreamingOp) ? contentOrId as string : generateUniqueBlockId(`msg-${role}`);
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
      }
    };
  }, []);

  const handleSend = async (text: string) => {
    console.log('%cAGENT CHAT VIEW: handleSend CALLED', 'color: lime; font-weight: bold; font-size: 1.2em;');
    if (!text.trim() || isInitializing || isLoading) return;
    addMessage('user', text);
    setIsLoading(true);
    setChatError(null);

    const assistantMessageId = generateUniqueBlockId('assistant-msg');
    addMessage('assistant', assistantMessageId, true, []);
    currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };

    const queryParams = new URLSearchParams({ user_message: text });
    const agentConfig: AgentConfig | undefined = await getSpecificComponentConfig("agents", agentName);
    if (agentConfig?.system_prompt) {
      queryParams.append('system_prompt', agentConfig.system_prompt);
    }
    // const { apiKey } = useAuthStore.getState(); // apiKey is handled by streamAgentExecution
    // if (apiKey) queryParams.append('api_key', apiKey); // Handled by streamAgentExecution

    // const url = `/api/agents/${agentName}/execute-stream?${queryParams.toString()}`; // OLD direct URL construction
    if (eventSourceRef.current) eventSourceRef.current.close();

    // Use the imported streamAgentExecution function
    // It will use VITE_API_BASE_URL and handle apiKey internally
    const agentConfigForPrompt: AgentConfig | undefined = await getSpecificComponentConfig("agents", agentName); // Fetch for system_prompt
    const system_prompt_for_stream = agentConfigForPrompt?.system_prompt;

    const eventSource = streamAgentExecution(agentName, text, system_prompt_for_stream);
    eventSourceRef.current = eventSource;

    const updateStreamingMessageBlocks = (eventName: string, updater: (blocks: AgentOutputContentBlock[]) => AgentOutputContentBlock[]) => {
      setMessages(prevMessages =>
        prevMessages.map(msg => {
          if (msg.id === assistantMessageId) {
            const currentBlocks = msg.contentBlocks || [];
            console.log(`%c[${eventName}] BEFORE update for ${assistantMessageId}`, 'color: orange;', JSON.parse(JSON.stringify(currentBlocks)));
            const updatedBlocks = updater(currentBlocks);
            console.log(`%c[${eventName}] AFTER update for ${assistantMessageId}`, 'color: lightgreen;', JSON.parse(JSON.stringify(updatedBlocks)));
            return { ...msg, contentBlocks: updatedBlocks };
          }
          return msg;
        })
      );
    };

    eventSource.onopen = () => console.log('SSE connection opened.');
    eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      addMessage('error', 'Streaming connection error.');
      setChatError('Streaming connection error.');
      setIsLoading(false);
      eventSourceRef.current?.close();
    };

    eventSource.addEventListener('text_delta', (event) => {
      console.log('%cTEXT_DELTA event received', 'color: cyan', event.data);
      try {
        const eventData = JSON.parse(event.data as string);
        const { index: llmMessageIndex, text_chunk } = eventData;

        if (typeof llmMessageIndex !== 'number' || typeof text_chunk !== 'string') {
          console.error('[text_delta] Invalid eventData:', eventData);
          return;
        }
        console.log(`%c[text_delta] Processing: index=${llmMessageIndex}, chunk="${text_chunk}"`, 'color: cyan');

        updateStreamingMessageBlocks('text_delta', currentBlocks => {
          let newBlocks = [...currentBlocks];
          let blockProcessed = false;

          console.log(`%c[text_delta] currentStreamingTextInfoRef at START:`, 'color: blue', JSON.parse(JSON.stringify(currentStreamingTextInfoRef.current)));

          // If a blockId is already stored in the ref for this llmMessageIndex, try to update it.
          if (currentStreamingTextInfoRef.current.blockId && currentStreamingTextInfoRef.current.llmMessageIndex === llmMessageIndex) {
            const targetBlock = newBlocks.find(b => b.id === currentStreamingTextInfoRef.current.blockId);
            if (targetBlock && targetBlock.type === 'text' && !targetBlock._finalized) {
              console.log(`%c[text_delta] Updating block VIA REF: ${targetBlock.id}`, 'color: green; font-weight: bold;');
              targetBlock.text = (targetBlock.text || '') + text_chunk;
              blockProcessed = true;
            } else if (targetBlock) {
              // Ref points to a block that's wrong type or finalized. This shouldn't happen if logic is correct.
              console.warn(`%c[text_delta] Ref block ${targetBlock.id} is not a valid target (type: ${targetBlock.type}, finalized: ${targetBlock._finalized}). Clearing ref.`, 'color: orange');
              currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };
            } else {
              // The block ID in the ref wasn't found in currentBlocks.
              // This can happen if setMessages hasn't updated the closure's currentBlocks yet.
              // In this case, we *don't* create a new block, assuming the ref is correct and the block will appear.
              console.log(`%c[text_delta] Ref block ${currentStreamingTextInfoRef.current.blockId} NOT FOUND in currentBlocks snapshot. Assuming it will appear. Skipping new block creation for this chunk.`, 'color: purple');
              blockProcessed = true; // Mark as processed to prevent creating a new block for this specific chunk.
            }
          }

          // If the ref wasn't set for this llmMessageIndex, or was cleared, try to find/create.
          if (!blockProcessed) {
            let existingBlock = newBlocks.find(
              b => b.type === 'text' && b._originalIndex === llmMessageIndex && !b._finalized
            );

            if (existingBlock) {
              console.log(`%c[text_delta] Found and updating OTHER existing block: ${existingBlock.id}. Setting ref.`, 'color: green;');
              existingBlock.text = (existingBlock.text || '') + text_chunk;
              currentStreamingTextInfoRef.current = { blockId: existingBlock.id!, llmMessageIndex };
            } else {
              console.log(`%c[text_delta] No block found via ref or existing search. Creating NEW text block for index ${llmMessageIndex}`, 'color: yellow; font-weight: bold;');
              const newBlockId = generateUniqueBlockId(`text-idx${llmMessageIndex}`);
              const newTextBlock: AgentOutputContentBlock = {
                type: 'text',
                text: text_chunk,
                id: newBlockId,
                _originalIndex: llmMessageIndex,
                _finalized: false,
              };
              newBlocks.push(newTextBlock);
              currentStreamingTextInfoRef.current = { blockId: newBlockId, llmMessageIndex };
            }
          }

          console.log(`%c[text_delta] currentStreamingTextInfoRef at END:`, 'color: blue', JSON.parse(JSON.stringify(currentStreamingTextInfoRef.current)));
          console.log('%c[text_delta] END processing event', 'color: cyan');
          return newBlocks.filter(b => b.type !== 'placeholder');
        });
      } catch (e) { console.error('Error in text_delta handler:', e, event.data); }
    });

    eventSource.addEventListener('tool_use_start', (event) => {
      console.log('%cTOOL_USE_START event received', 'color: magenta', event.data);
      try {
        const eventData = JSON.parse(event.data as string);
        const { index: llmMessageIndex, tool_name, tool_id } = eventData;
        if (typeof llmMessageIndex !== 'number' || !tool_name || !tool_id) {
          console.error('[tool_use_start] Invalid eventData:', eventData);
          return;
        }
        console.log(`%c[tool_use_start] Processing: index=${llmMessageIndex}, tool_name=${tool_name}, tool_id=${tool_id}`, 'color: magenta');
        currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };

        updateStreamingMessageBlocks('tool_use_start', blocks => [
          ...blocks.filter(b => b.type !== 'placeholder'),
          {
            type: 'tool_use',
            id: tool_id,
            name: tool_name,
            input: {},
            _originalIndex: llmMessageIndex,
            _inputFinalized: false,
          }
        ]);
      } catch (e) { console.error('Error in tool_use_start handler:', e, event.data); }
    });

    eventSource.addEventListener('content_block_stop', (event) => {
      console.log('%cCONTENT_BLOCK_STOP event received', 'color: red; font-weight: bold;', event.data);
      try {
        const eventData = JSON.parse(event.data as string);
        const { index: llmMessageIndex, content_type, tool_id: event_tool_id, full_tool_input } = eventData;

        if (typeof llmMessageIndex !== 'number' && !event_tool_id) { // Allow if event_tool_id is present, index might not be for tool_use
          console.error('[content_block_stop] Invalid eventData - missing llmMessageIndex (and not a tool_use with tool_id):', eventData);
          return;
        }

        console.log(`%c[content_block_stop] Processing: content_type=${content_type}, index=${llmMessageIndex}, event_tool_id=${event_tool_id}, has_full_tool_input=${!!full_tool_input}`, 'color: red; font-weight: bold;');

        updateStreamingMessageBlocks('content_block_stop', currentBlocks => {
          let newBlocks = [...currentBlocks];
          let processedThisEvent = false;

          for (let i = 0; i < newBlocks.length; i++) {
            if (processedThisEvent) break; // Only process one block per event
            const block = newBlocks[i];

            // Handle TOOL_USE stop (now explicit with full_tool_input)
            if (content_type === 'tool_use' && event_tool_id && block.type === 'tool_use' && block.id === event_tool_id && !block._inputFinalized) {
              console.log(`%c[content_block_stop TOOL_USE (explicit)] Matched tool block by tool_id: ${event_tool_id}`, 'color: red; font-weight: bold;');
              const toolBlock = block as any; // To modify input and _inputFinalized
              if (typeof full_tool_input === 'string') {
                try {
                  toolBlock.input = JSON.parse(full_tool_input);
                  console.log(`%c[content_block_stop TOOL_USE (explicit)] Parsed full_tool_input for ${event_tool_id}:`, 'color: red;', JSON.parse(JSON.stringify(toolBlock.input)));
                } catch (e) {
                  console.error('Failed to parse full_tool_input JSON:', e, full_tool_input);
                  toolBlock.input = { error: "Failed to parse full_tool_input JSON", raw: full_tool_input };
                }
              } else {
                console.warn(`%c[content_block_stop TOOL_USE (explicit)] full_tool_input is not a string for ${event_tool_id}. Setting input to empty.`, 'color: orange', full_tool_input);
                toolBlock.input = {};
              }
              toolBlock._inputFinalized = true;
              // delete toolBlock._accumulatedJsonInput; // No longer used
              newBlocks[i] = toolBlock;
              processedThisEvent = true;
              break;
            }
            // Handle TEXT stop
            // Ensure this only runs if it's a text block and the event is for this specific block's index
            // And it wasn't already processed as a tool_use stop.
            else if (block.type === 'text' && block._originalIndex === llmMessageIndex && !block._finalized && content_type !== 'tool_use') {
              console.log(`%c[content_block_stop TEXT] Matched block: id=${block.id}, text="${block.text}"`, 'color: red; font-weight: bold;');
              if (currentStreamingTextInfoRef.current.blockId === block.id) {
                console.log(`%c[content_block_stop TEXT] Clearing currentStreamingTextInfoRef for block ${block.id}`, 'color: red;');
                currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };
              }

              const processedSubBlocks: AgentOutputContentBlock[] = [];
              if (block.text) {
                const rawText = block.text;
                console.log(`%c[content_block_stop TEXT] Raw text to process: "${rawText}"`, 'color: red;');
                const thinkingRegex = /<thinking>([\s\S]*?)<\/thinking>/gi;
                let lastIndex = 0;
                let match;
                while ((match = thinkingRegex.exec(rawText)) !== null) {
                  const textBefore = rawText.substring(lastIndex, match.index).trim();
                  if (textBefore) processedSubBlocks.push({ type: 'text', text: textBefore, id: generateUniqueBlockId('txt-seg'), _finalized: true, _originalIndex: block._originalIndex });
                  const thinkingContent = match[1].trim();
                  if (thinkingContent) processedSubBlocks.push({ type: 'thinking_finalized', text: thinkingContent, id: generateUniqueBlockId('thk-fin'), _finalized: true, _originalIndex: block._originalIndex });
                  lastIndex = thinkingRegex.lastIndex;
                }
                const remainingText = rawText.substring(lastIndex).trim();
                if (remainingText) {
                  try {
                    const parsedJson = JSON.parse(remainingText);
                    processedSubBlocks.push({ type: 'final_response_data', parsedJson, text: remainingText, id: generateUniqueBlockId('json-fin'), _finalized: true, _originalIndex: block._originalIndex });
                  } catch (e) {
                    processedSubBlocks.push({ type: 'text', text: remainingText, id: generateUniqueBlockId('txt-fin'), _finalized: true, _originalIndex: block._originalIndex });
                  }
                }
                console.log('%c[content_block_stop TEXT] Processed sub-blocks:', 'color: red;', JSON.parse(JSON.stringify(processedSubBlocks)));
              }

              if (processedSubBlocks.length > 0) {
                console.log(`%c[content_block_stop TEXT] Splicing ${processedSubBlocks.length} sub-blocks for original block ${block.id}`, 'color: red; font-weight: bold;');
                newBlocks.splice(i, 1, ...processedSubBlocks);
                i += processedSubBlocks.length - 1; // Adjust loop index
              } else {
                console.log(`%c[content_block_stop TEXT] No sub-blocks after parsing block ${block.id}. Removing original.`, 'color: red; font-weight: bold;');
                newBlocks.splice(i, 1);
                i--; // Adjust loop index
              }
              processedThisEvent = true;
              break;
            }
          }
          console.log(`%c[content_block_stop] END processing event. Processed flag: ${processedThisEvent}`, 'color: red;');
          return newBlocks.filter(b => b.type !== 'placeholder');
        });
      } catch (e) { console.error('Error in content_block_stop handler:', e, event.data); }
    });

    eventSource.addEventListener('tool_result', (event) => {
      console.log('%cTOOL_RESULT event received', 'color: green', event.data);
      try {
        const eventData = JSON.parse(event.data as string);
        const { tool_use_id, output, is_error, name } = eventData;
        if (!tool_use_id || output === undefined) {
          console.error('[tool_result] Invalid eventData:', eventData);
          return;
        }
        console.log(`%c[tool_result] Processing: tool_use_id=${tool_use_id}, is_error=${is_error}`, 'color: green');
        currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };

        updateStreamingMessageBlocks('tool_result', blocks => {
          const newBlocks = [...blocks];
          const toolCallBlockIndex = newBlocks.findIndex(b => b.type === 'tool_use' && b.id === tool_use_id);
          const newToolResultBlock: AgentOutputContentBlock = {
            type: 'tool_result',
            id: generateUniqueBlockId(`tool-res-${tool_use_id}`),
            tool_use_id,
            content: output,
            is_error: !!is_error,
            name,
            _finalized: true,
          };
          if (toolCallBlockIndex !== -1) {
            newBlocks.splice(toolCallBlockIndex + 1, 0, newToolResultBlock);
          } else {
            console.warn(`[tool_result] Tool call with id ${tool_use_id} not found. Appending result.`);
            newBlocks.push(newToolResultBlock);
          }
          console.log('%c[tool_result] END processing event', 'color: green');
          return newBlocks.filter(b => b.type !== 'placeholder');
        });
      } catch (e) { console.error('Error in tool_result handler:', e, event.data); }
    });

    eventSource.addEventListener('tool_execution_error', (event) => {
      console.log('%cTOOL_EXECUTION_ERROR event received', 'color: orange', event.data);
      try {
        const eventData = JSON.parse(event.data as string);
        const { tool_use_id, error_message, tool_name } = eventData;
        if (!tool_use_id || !error_message) {
          console.error('[tool_execution_error] Invalid eventData:', eventData);
          return;
        }
        console.log(`%c[tool_execution_error] Processing: tool_use_id=${tool_use_id}, tool_name=${tool_name}`, 'color: orange');
        currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };

        updateStreamingMessageBlocks('tool_execution_error', blocks => {
          const newBlocks = [...blocks];
          const toolCallBlockIndex = newBlocks.findIndex(b => b.type === 'tool_use' && b.id === tool_use_id);
          const newToolErrorBlock: AgentOutputContentBlock = {
            type: 'tool_result', // Represent as a tool_result with an error
            id: generateUniqueBlockId(`tool-err-${tool_use_id}`),
            tool_use_id,
            content: error_message,
            is_error: true,
            name: tool_name,
            _finalized: true,
          };
          if (toolCallBlockIndex !== -1) {
            newBlocks.splice(toolCallBlockIndex + 1, 0, newToolErrorBlock);
          } else {
            console.warn(`[tool_execution_error] Tool call with id ${tool_use_id} not found. Appending error.`);
            newBlocks.push(newToolErrorBlock);
          }
          console.log('%c[tool_execution_error] END processing event', 'color: orange');
          return newBlocks.filter(b => b.type !== 'placeholder');
        });
      } catch (e) { console.error('Error in tool_execution_error handler:', e, event.data); }
    });

    eventSource.addEventListener('stream_end', (event) => {
      console.log('%cSSE STREAM_END event received', 'color: gray', event.data);
      currentStreamingTextInfoRef.current = { blockId: null, llmMessageIndex: null };
      setIsLoading(false);
      setMessages(prevMessages =>
        prevMessages.map(msg =>
          msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
        )
      );
      eventSourceRef.current?.close();
    });
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
