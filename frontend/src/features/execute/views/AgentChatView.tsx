import React, { useState, useEffect, useRef } from 'react';
import {
  getConfigFileContent,
  registerLlmConfigAPI,
  registerAgentAPI,
  executeAgentAPI
} from '../../../lib/apiClient'; // Assuming apiClient.ts is in lib
// Define types for AgentConfig, LLMConfig, and AgentExecutionResult if not already globally available
// For now, using 'any' as placeholders.
// import type { AgentConfig, LLMConfig } from '../../../types/projectManagement'; // Or a more specific types file
// import type { AgentExecutionResult } from '../../../types/execution'; // Or a more specific types file

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

const AgentChatView: React.FC<AgentChatViewProps> = ({ agentName, onClose }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const addMessage = (role: ChatMessage['role'], content: string) => {
    setMessages(prev => [...prev, { id: Date.now().toString(), role, content, timestamp: new Date() }]);
  };

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const userMessageContent = inputValue;
    addMessage('user', userMessageContent);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      // 1. Pre-Execution Registration
      addMessage('system', `Fetching configuration for agent: ${agentName}...`);
      const agentConfig = await getConfigFileContent("agents", `${agentName}.json`);
      addMessage('system', `Agent configuration for ${agentName} fetched.`);

      if (agentConfig && agentConfig.llm_config_id) {
        addMessage('system', `Fetching LLM configuration: ${agentConfig.llm_config_id}...`);
        const llmConfig = await getConfigFileContent("llms", `${agentConfig.llm_config_id}.json`);
        addMessage('system', `LLM configuration ${agentConfig.llm_config_id} fetched. Registering...`);
        await registerLlmConfigAPI(llmConfig);
        addMessage('system', `LLM configuration ${agentConfig.llm_config_id} registered/updated.`);
      }

      addMessage('system', `Registering/updating agent: ${agentName}...`);
      await registerAgentAPI(agentConfig);
      addMessage('system', `Agent ${agentName} registered/updated.`);

      // 2. Execute Agent
      addMessage('system', `Executing agent ${agentName} with your message...`);
      const executionResult = await executeAgentAPI(agentName, userMessageContent);

      // Assuming executionResult has a structure like { final_response: string, error?: string, conversation?: any[] }
      // This needs to align with actual AgentExecutionResult structure from backend
      if (executionResult.error) {
        addMessage('error', `Execution Error: ${executionResult.error}`);
      } else if (executionResult.final_response) {
        addMessage('assistant', executionResult.final_response);
      } else {
        // Handle cases where there's no direct final_response, e.g. tool use or complex conversation
        // For now, just log the full result if no simple response.
        addMessage('assistant', `Execution finished. Full result: ${JSON.stringify(executionResult, null, 2)}`);
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
      addMessage('error', `Error: ${errorMessage}`);
      setError(errorMessage);
      console.error('Chat execution error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)] bg-dracula-background p-4 rounded-lg shadow-md border border-dracula-current-line">
      <div className="flex justify-between items-center mb-3 pb-3 border-b border-dracula-comment">
        <h3 className="text-xl font-semibold text-dracula-cyan">Chat with: {agentName}</h3>
        <button
          onClick={onClose}
          className="text-sm bg-dracula-comment hover:bg-opacity-75 text-dracula-foreground py-1 px-3 rounded-md"
        >
          Back to List
        </button>
      </div>

      <div className="flex-grow overflow-y-auto mb-4 pr-2 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xl p-3 rounded-lg shadow whitespace-pre-wrap
                ${msg.role === 'user' ? 'bg-dracula-purple text-white' : ''}
                ${msg.role === 'assistant' ? 'bg-dracula-current-line text-dracula-foreground' : ''}
                ${msg.role === 'error' ? 'bg-dracula-red text-white' : ''}
                ${msg.role === 'system' ? 'bg-dracula-comment text-dracula-foreground text-xs italic' : ''}
              `}
            >
              {msg.content}
              <div className="text-xs opacity-60 mt-1">
                {msg.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {error && <p className="text-sm text-dracula-red mb-2">Error: {error}</p>}

      <div className="flex items-center border-t border-dracula-comment pt-3">
        <textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !isLoading) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Type your message..."
          className="flex-grow p-2 border border-dracula-comment rounded-md bg-dracula-background text-dracula-foreground focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink resize-none"
          rows={2}
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !inputValue.trim()}
          className="ml-2 bg-dracula-green hover:bg-opacity-80 text-dracula-background font-semibold py-2 px-4 rounded-md disabled:opacity-50"
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
};

export default AgentChatView;
