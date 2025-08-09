import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Loader2, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { InputPanelProps, ExecutionRequest } from '@/types/execution';
import { SessionSelector } from './SessionSelector';

export const InputPanel: React.FC<InputPanelProps> = ({ agent, onExecute, disabled = false }) => {
  const [message, setMessage] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [stream, setStream] = useState(true);
  const [debugMode, setDebugMode] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || disabled) {
      return;
    }

    const request: ExecutionRequest = {
      user_message: message.trim(),
      session_id: sessionId || undefined,
      system_prompt: systemPrompt || undefined,
      stream,
      debug_mode: debugMode,
    };

    onExecute(request);
  };

  const getExamplePrompts = (agent: any): string[] => {
    // Generate example prompts based on agent capabilities
    const examples = [
      `Help me understand ${agent.name}`,
      'What can you do for me?',
      'Show me an example of your capabilities',
    ];

    // Add tool-specific examples if MCP servers are configured
    if (agent.mcp_servers && agent.mcp_servers.length > 0) {
      examples.push(`Use your ${agent.mcp_servers[0]} tools to help me`);
    }

    return examples;
  };

  return (
    <div className="p-4 space-y-6">
      {/* Agent Info */}
      <div className="space-y-2">
        <h3 className="font-medium text-foreground">Agent Information</h3>
        <div className="text-sm text-muted-foreground space-y-1">
          <p>• Description: {agent.description || 'No description available'}</p>
          <p>• Tools: {agent.mcp_servers?.join(', ') || 'None'}</p>
          <p>• Model: {agent.model || agent.llm_config_id || 'Default'}</p>
        </div>
      </div>

      {/* Message Input */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="message">Your Message *</Label>
          <Textarea
            id="message"
            placeholder="What would you like the agent to do?"
            value={message}
            onChange={e => setMessage(e.target.value)}
            className="min-h-[120px] resize-none"
            disabled={disabled}
          />
          <div className="text-xs text-muted-foreground text-right">
            {message.length} characters
          </div>
        </div>

        {/* Session Management */}
        <SessionSelector
          agentName={agent.name}
          selectedSessionId={sessionId}
          onSessionSelect={setSessionId}
          onSessionCreate={(sessionName: string) => {
            console.log('Creating session:', sessionName);
            // TODO: Implement session creation
          }}
          disabled={disabled}
        />

        {/* Advanced Options */}
        <div className="space-y-3">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full justify-between"
            disabled={disabled}
          >
            Advanced Options
            <ChevronDown
              className={`h-4 w-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`}
            />
          </Button>

          <AnimatePresence>
            {showAdvanced && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="space-y-3 overflow-hidden"
              >
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="stream"
                    checked={stream}
                    onCheckedChange={setStream}
                    disabled={disabled}
                  />
                  <Label htmlFor="stream" className="text-sm">
                    Stream response in real-time
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="debug"
                    checked={debugMode}
                    onCheckedChange={setDebugMode}
                    disabled={disabled}
                  />
                  <Label htmlFor="debug" className="text-sm">
                    Debug mode (show tool calls)
                  </Label>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="system-prompt" className="text-sm">
                    System Prompt Override
                  </Label>
                  <Textarea
                    id="system-prompt"
                    placeholder="Optional: Override the agent's system prompt"
                    value={systemPrompt}
                    onChange={e => setSystemPrompt(e.target.value)}
                    className="min-h-[80px] resize-none"
                    disabled={disabled}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Execute Button */}
        <Button type="submit" className="w-full" disabled={!message.trim() || disabled}>
          {disabled ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Executing...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Execute Agent
            </>
          )}
        </Button>
      </form>

      {/* Input Examples */}
      {!disabled && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Example prompts:</h4>
          <div className="space-y-1">
            {getExamplePrompts(agent).map((example, index) => (
              <button
                key={index}
                type="button"
                onClick={() => setMessage(example)}
                className="block w-full text-left text-xs text-muted-foreground hover:text-foreground p-2 rounded border border-border hover:bg-accent transition-colors"
              >
                "{example}"
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
