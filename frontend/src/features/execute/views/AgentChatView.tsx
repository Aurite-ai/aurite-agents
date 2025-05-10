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
  getConfigFileContent,
  registerLlmConfigAPI,
  registerAgentAPI,
  executeAgentAPI
} from '../../../lib/apiClient'; // Assuming apiClient.ts is in lib

// Assuming types are defined in a central place
import type { AgentConfig, LLMConfig } from '../../../types/projectManagement';

// Placeholder for AgentExecutionResult - adjust based on actual backend response
interface AgentExecutionResult {
  final_response?: string;
  error?: string;
  // conversation?: any[]; // If backend returns full conversation history
  // Add other fields as per your backend's response structure
}

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
  addSystemMessage: (text: string) => void // Callback to add system messages to UI
): Promise<void> => {
  addSystemMessage(`Fetching configuration for agent: ${agentName}...`);
  const agentConfig: AgentConfig = await getConfigFileContent("agents", `${agentName}.json`);
  addSystemMessage(`Agent configuration for ${agentName} fetched.`);

  if (agentConfig && agentConfig.llm_config_id) {
    addSystemMessage(`Fetching LLM configuration: ${agentConfig.llm_config_id}...`);
    const llmConfig: LLMConfig = await getConfigFileContent("llms", `${agentConfig.llm_config_id}.json`);
    addSystemMessage(`LLM configuration ${agentConfig.llm_config_id} fetched. Registering...`);
    await registerLlmConfigAPI(llmConfig);
    addSystemMessage(`LLM configuration ${agentConfig.llm_config_id} registered/updated.`);
  } else if (agentConfig && !agentConfig.llm_config_id) {
    addSystemMessage(`Agent ${agentName} does not have an LLM configuration specified. Skipping LLM registration.`);
  }

  addSystemMessage(`Registering/updating agent: ${agentName}...`);
  await registerAgentAPI(agentConfig); // agentConfig should be AgentConfig type
  addSystemMessage(`Agent ${agentName} registered/updated.`);
};

const AgentChatView: React.FC<AgentChatViewProps> = ({ agentName, onClose }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  // inputValue is now managed by MessageInput's onSend prop
  const [isLoading, setIsLoading] = useState<boolean>(false);
  // Error state for displaying general errors, not individual message errors
  const [chatError, setChatError] = useState<string | null>(null);
  // const [isTyping, setIsTyping] = useState(false); // For typing indicator
  // messagesEndRef and scrollToBottom are no longer needed with MessageList

  const addMessage = (role: ChatMessage['role'], content: string) => {
    setMessages(prev => [...prev, { id: Date.now().toString(), role, content, timestamp: new Date() }]);
  };

  const handleSend = async (text: string) => { // text comes from MessageInput
    if (!text.trim()) return;

    const userMessageContent = text;
    addMessage('user', userMessageContent);
    // setInputValue(''); // No longer needed
    setIsLoading(true);
    setChatError(null); // Clears general chat error
    // setIsTyping(true); // Show typing indicator

    try {
      // 1. Pre-Execution Registration
      // Use the helper function. addMessage callback is used for system messages.
      await performPreExecutionRegistration(agentName, (msg) => addMessage('system', msg));

      // 2. Execute Agent
      addMessage('system', `Executing agent ${agentName} with your message...`);
      const executionResult: AgentExecutionResult = await executeAgentAPI(agentName, userMessageContent);
      // setIsTyping(false); // Hide typing indicator

      if (executionResult.error) {
        addMessage('error', `Execution Error: ${executionResult.error}`);
      } else if (executionResult.final_response) {
        addMessage('assistant', executionResult.final_response);
      } else {
        addMessage('assistant', `Execution finished. Result: ${JSON.stringify(executionResult, null, 2)}`);
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
