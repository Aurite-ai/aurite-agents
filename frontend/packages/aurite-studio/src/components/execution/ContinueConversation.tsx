import React, { useState } from 'react';
import { Send, RotateCcw, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ContinueConversationProps } from '@/types/execution';

export const ContinueConversation: React.FC<ContinueConversationProps> = ({
  sessionId,
  agentName,
  onSendMessage,
  onRegenerateResponse,
  isLoading = false,
}) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isLoading) {
      return;
    }

    onSendMessage(message.trim());
    setMessage('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-medium text-foreground">Continue Conversation</h4>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative">
          <Textarea
            placeholder="Ask a follow-up question or continue the conversation..."
            value={message}
            onChange={e => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            className="min-h-[80px] resize-none pr-12"
            disabled={isLoading}
          />
          <div className="absolute bottom-2 right-2 text-xs text-muted-foreground">
            Ctrl+Enter to send
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {onRegenerateResponse && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onRegenerateResponse}
                disabled={isLoading}
                className="h-8 px-3 text-xs"
              >
                <RotateCcw className="h-3 w-3 mr-1" />
                Regenerate
              </Button>
            )}
          </div>

          <Button
            type="submit"
            size="sm"
            disabled={!message.trim() || isLoading}
            className="h-8 px-4"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin mr-1" />
                Sending...
              </>
            ) : (
              <>
                <Send className="h-3 w-3 mr-1" />
                Send
              </>
            )}
          </Button>
        </div>
      </form>

      <div className="text-xs text-muted-foreground">
        Session: {sessionId} • Agent: {agentName}
      </div>
    </div>
  );
};
