import React, { useState, useEffect, type JSX } from 'react'; // Removed useRef as it's not used after MessageList integration
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
} from '@chatscope/chat-ui-kit-react';
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';
import StructuredResponseView from '../../../components/common/StructuredResponseView';
import ToolCallView from '../../../components/common/ToolCallView'; // Added import
import ToolResultView from '../../../components/common/ToolResultView'; // Added import

import {
  getSpecificComponentConfig,
  registerLlmConfigAPI,
  registerAgentAPI,
  executeAgentAPI
} from '../../../lib/apiClient';

import type {
  AgentConfig,
  LLMConfig,
  AgentExecutionResult,
} from '../../../types/projectManagement';

interface AgentChatViewProps {
  agentName: string;
  onClose: () => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'error' | 'system';
  content: string | JSX.Element;
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
  const [isInitializing, setIsInitializing] = useState<boolean>(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const addMessage = (role: ChatMessage['role'], content: string | JSX.Element) => {
    setMessages(prev => [...prev, { id: Date.now().toString(), role, content, timestamp: new Date() }]);
  };

  useEffect(() => {
    const setupAgentSession = async () => {
      if (!agentName) return;
      setIsInitializing(true);
      setMessages([]);
      setChatError(null);
      try {
        await performPreExecutionRegistration(agentName, (msg) => addMessage('system', msg), true);
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

  const handleSend = async (text: string) => {
    if (!text.trim() || isInitializing || isLoading) return;
    const userMessageContent = text;
    addMessage('user', userMessageContent);
    setIsLoading(true);
    setChatError(null);
    try {
      const executionResult: AgentExecutionResult = await executeAgentAPI(agentName, userMessageContent);

      if (executionResult.error) {
        addMessage('error', `Execution Error: ${executionResult.error}`);
      } else if (executionResult.conversation && executionResult.conversation.length > 0) {
        // Process the entire conversation history from the result
        // Skip the initial user message we already added
        const conversationMessages = executionResult.conversation.slice(messages.filter(m => m.role === 'user').length);

        conversationMessages.forEach(convMessage => {
          if (convMessage.role === 'assistant') {
            convMessage.content.forEach(block => {
              if (block.type === 'text' && block.text !== undefined && block.text !== null) {
                if (typeof block.text === 'string') {
                  try {
                    const jsonData = JSON.parse(block.text);
                    if (typeof jsonData === 'object' && jsonData !== null && !Array.isArray(jsonData)) {
                      addMessage('assistant', <StructuredResponseView data={jsonData} />);
                    } else {
                      addMessage('assistant', block.text);
                    }
                  } catch (e) {
                    addMessage('assistant', block.text);
                  }
                } else { // It's a Record<string, any>
                  addMessage('assistant', <StructuredResponseView data={block.text as Record<string, any>} />);
                }
              } else if (block.type === 'tool_use' && block.id && block.name && block.input) {
                addMessage('assistant', <ToolCallView toolId={block.id} toolName={block.name} toolInput={block.input} />);
              }
            });
          } else if (convMessage.role === 'user') { // Typically for tool results
            convMessage.content.forEach(block => {
              if (block.type === 'tool_result' && block.tool_use_id && block.content) {
                 // The 'content' of a tool_result can be a string or array of blocks.
                 // ToolResultView's renderResultContent handles this.
                addMessage('user', <ToolResultView toolUseId={block.tool_use_id} result={block.content} isError={block.is_error} />);
              } else if (block.type === 'text' && typeof block.text === 'string') {
                // This case might not happen if user messages are only for tool results or initial input
                // but good to handle if user role can have plain text in conversation history.
                // We've already added the initial user message, so this would be for subsequent user text if any.
                // For now, we assume user messages in conversation are primarily tool_results.
              }
            });
          }
        });

        // If after processing conversation, there's still a final_response object not covered
        // (e.g. if conversation doesn't include the absolute last utterance, which is unlikely with current Agent model)
        // This part might become redundant if conversation always includes the final_response content.
        if (executionResult.final_response &&
            !executionResult.conversation.find(m => m.id === executionResult.final_response?.id)) {
            // This logic is a fallback and might need refinement based on how `final_response` relates to `conversation`
            executionResult.final_response.content.forEach(block => {
                 if (block.type === 'text' && block.text !== undefined && block.text !== null) {
                    if (typeof block.text === 'string') addMessage('assistant', block.text);
                    else addMessage('assistant', <StructuredResponseView data={block.text as Record<string, any>} />);
                 }
            });
        }

      } else {
        addMessage('assistant', `Execution completed, but no standard response found. Full result: ${JSON.stringify(executionResult, null, 2)}`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
      addMessage('error', `Error: ${errorMessage}`);
      setChatError(errorMessage);
      console.error('Chat execution error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const mapRoleToDirection = (role: ChatMessage['role']): "incoming" | "outgoing" => {
    return role === 'user' ? 'outgoing' : 'incoming';
  };

  return (
    <div className="flex flex-col h-[calc(100vh-15rem)] bg-dracula-background p-0 rounded-lg shadow-md border border-dracula-current-line max-w-6xl mx-auto"> {/* Adjusted height and width */}
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
            <MessageList className="bg-dracula-background"> {/* Removed pt-4 */}
              {messages.map((msg) => {
                // Render error messages using CustomContent for specific styling
                if (msg.role === 'error') {
                  return (
                    <Message
                      key={msg.id}
                      model={{ /* Model can be minimal if using full custom content */
                        sentTime: msg.timestamp.toISOString(),
                        sender: msg.role,
                        direction: "incoming",
                        position: "single"
                      }}
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
                // Render user and assistant messages
                if (msg.role === 'user' || msg.role === 'assistant') {
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
                  } else { // msg.content is JSX.Element (our StructuredResponseView for assistant)
                    return (
                      <Message
                        key={msg.id}
                        model={{
                          // message: undefined, // No simple string message
                          sentTime: msg.timestamp.toISOString(),
                          sender: msg.role,
                          direction: mapRoleToDirection(msg.role),
                          position: "single"
                        }}
                      >
                        <Message.CustomContent>
                          {msg.content}
                        </Message.CustomContent>
                      </Message>
                    );
                  }
                }
                // System messages are now silent and won't be rendered here unless explicitly added for debugging
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
