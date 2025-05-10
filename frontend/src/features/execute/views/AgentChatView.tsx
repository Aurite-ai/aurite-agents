import React, { useState, useEffect, useRef } from 'react';
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
} from '@chatscope/chat-ui-kit-react';
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';

import {
  // getConfigFileContent, // No longer used directly here for individual configs
  getSpecificComponentConfig, // New function to get specific config by ID/name
  registerLlmConfigAPI,
  registerAgentAPI,
  executeAgentAPI
} from '../../../lib/apiClient';

// Assuming types are defined in a central place
import type {
  AgentConfig,
  LLMConfig,
  AgentExecutionResult, // Import the shared type
  // AgentOutputMessage and AgentOutputContentBlock are implicitly typed
  // by their usage within AgentExecutionResult and are not directly
  // instantiated or used as standalone types in this component's props/state.
  // If they were, we would import them explicitly.
} from '../../../types/projectManagement';

interface AgentChatViewProps {
  agentName: string;
  onClose: () => void; // To go back to the list view
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'error' | 'system';
  content: string;
  timestamp: Date;
}

// Helper function for pre-execution registration
const performPreExecutionRegistration = async (
  agentName: string,
  addSystemMessage: (text: string) => void, // Callback to add system messages to UI
  silent: boolean = false // Added silent flag
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
  const [isLoading, setIsLoading] = useState<boolean>(false); // For message sending
  const [isInitializing, setIsInitializing] = useState<boolean>(false); // For initial agent setup
  const [chatError, setChatError] = useState<string | null>(null);

  const addMessage = (role: ChatMessage['role'], content: string) => {
    setMessages(prev => [...prev, { id: Date.now().toString(), role, content, timestamp: new Date() }]);
  };

  // Effect for initializing/re-initializing agent session when agentName changes
  useEffect(() => {
    const setupAgentSession = async () => {
      if (!agentName) return;

      setIsInitializing(true);
      setMessages([]); // Clear previous messages - good to keep for a fresh chat session
      setChatError(null);
      // Removed: addMessage('system', `Initializing session for agent: ${agentName}...`);

      try {
        // Call with silent = true to suppress internal system messages from this function
        await performPreExecutionRegistration(agentName, (msg) => addMessage('system', msg), true);
        // Removed: addMessage('system', `Agent ${agentName} is ready. You can now send messages.`);
        // If we want a "ready" message, it should be a single, specific one after all silent setup.
        // For now, per request, keeping it clean until user sends a message.
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to initialize agent session.';
        // Still show critical initialization errors in the chat
        addMessage('error', `Initialization Error: ${errorMessage}`);
        setChatError(errorMessage);
        console.error(`Error initializing agent ${agentName}:`, err);
      } finally {
        setIsInitializing(false);
      }
    };

    setupAgentSession();
  }, [agentName]); // Re-run when agentName changes

  const handleSend = async (text: string) => {
    if (!text.trim() || isInitializing || isLoading) return;

    const userMessageContent = text;
    addMessage('user', userMessageContent);
    setIsLoading(true);
    setChatError(null);

    try {
      // Pre-execution registration is now handled by useEffect/setupAgentSession
      // Removed: addMessage('system', `Executing agent ${agentName} with your message...`);
      const executionResult: AgentExecutionResult = await executeAgentAPI(agentName, userMessageContent);
      // setIsTyping(false); // Hide typing indicator

      if (executionResult.error) {
        addMessage('error', `Execution Error: ${executionResult.error}`);
      } else if (executionResult.final_response && executionResult.final_response.content && executionResult.final_response.content.length > 0) {
        const firstBlock = executionResult.final_response.content[0];
        if (firstBlock.type === 'text' && firstBlock.text !== undefined && firstBlock.text !== null) {
          if (typeof firstBlock.text === 'string') {
            addMessage('assistant', firstBlock.text);
          } else { // It's a Record<string, any> due to schema
            addMessage('assistant', JSON.stringify(firstBlock.text, null, 2));
          }
        } else {
          // Fallback if the first block is not text or text is empty
          addMessage('assistant', `Received complex response: ${JSON.stringify(executionResult.final_response, null, 2)}`);
        }
      } else {
        // Fallback if no final_response or no content in final_response
        addMessage('assistant', `Execution completed. Full result: ${JSON.stringify(executionResult, null, 2)}`);
      }

    } catch (err) {
      // setIsTyping(false); // Hide typing indicator
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
      addMessage('error', `Error: ${errorMessage}`);
      setChatError(errorMessage); // Set general chat error
      console.error('Chat execution error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Map our ChatMessage role to what @chatscope/chat-ui-kit-react expects for Message model
  const mapRoleToDirection = (role: ChatMessage['role']): "incoming" | "outgoing" => {
    return role === 'user' ? 'outgoing' : 'incoming';
  };

  return (
    // Adjust height as needed, ensure it fits within your layout
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-dracula-background p-0 rounded-lg shadow-md border border-dracula-current-line">
      {/* Header section - can be styled with Tailwind */}
      <div className="flex justify-between items-center p-3 border-b border-dracula-comment bg-dracula-current-line rounded-t-lg">
        <h3 className="text-xl font-semibold text-dracula-cyan">Chat with: {agentName}</h3>
        <button
          onClick={onClose}
          className="text-sm bg-dracula-purple hover:bg-opacity-80 text-dracula-background py-1 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-dracula-pink"
        >
          Back to List
        </button>
      </div>

      {/* Chat UI Kit Integration */}
      <div style={{ position: "relative", flexGrow: 1, overflow: "hidden" }} className="bg-dracula-background">
        <MainContainer responsive className="h-full">
          <ChatContainer className="h-full">
            <MessageList
              // typingIndicator={isTyping ? <TypingIndicator content="Agent is typing" /> : null}
              className="bg-dracula-background" // Apply Tailwind background
            >
              {messages.map((msg) => {
                // Special rendering for system and error messages, or integrate them differently
                if (msg.role === 'system' || msg.role === 'error') {
                  return (
                    <Message
                      key={msg.id}
                      model={{
                        message: `[${msg.role.toUpperCase()}] ${msg.content}\n${msg.timestamp.toLocaleTimeString()}`,
                        sentTime: msg.timestamp.toISOString(), // Or however you want to format
                        sender: msg.role,
                        direction: "incoming", // Treat system/error as incoming for display
                        position: "single"
                      }}
                      // className={`cs-message--${msg.role === 'system' ? 'system' : 'error'}`} // Custom class for styling
                    >
                       <Message.CustomContent>
                        <div className={`p-2 rounded-md text-xs
                          ${msg.role === 'system' ? 'bg-dracula-comment bg-opacity-30 text-dracula-comment italic' : ''}
                          ${msg.role === 'error' ? 'bg-dracula-red bg-opacity-30 text-dracula-red' : ''}
                        `}>
                          <strong>{msg.role.toUpperCase()}:</strong> {msg.content}
                          <div className="text-xs opacity-60 mt-1">{msg.timestamp.toLocaleTimeString()}</div>
                        </div>
                      </Message.CustomContent>
                    </Message>
                  );
                }
                return (
                  <Message
                    key={msg.id}
                    model={{
                      message: msg.content,
                      sentTime: msg.timestamp.toISOString(), // Or a string like "just now"
                      sender: msg.role, // 'user' or 'assistant'
                      direction: mapRoleToDirection(msg.role),
                      position: "single" // Or "first", "normal", "last" for grouping
                    }}
                    // Apply Tailwind classes for user/assistant messages if default styles aren't enough
                    // className={msg.role === 'user' ? 'my-user-message' : 'my-assistant-message'}
                  />
                );
              })}
            </MessageList>
            <MessageInput
              placeholder="Type message here..."
              onSend={handleSend}
              attachButton={false} // Disable attach button for now
              disabled={isLoading}
              sendDisabled={isLoading}
              className="bg-dracula-current-line" // Style input area
              // You can further style the input itself using CSS or by targeting its internal elements
            />
          </ChatContainer>
        </MainContainer>
      </div>
      {chatError && <p className="text-sm text-dracula-red p-2 text-center">{chatError}</p>}
    </div>
  );
};

export default AgentChatView;
