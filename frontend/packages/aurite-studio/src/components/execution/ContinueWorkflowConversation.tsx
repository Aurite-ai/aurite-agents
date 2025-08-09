import React, { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { ContinueWorkflowConversationProps } from '@/types/execution';

export const ContinueWorkflowConversation: React.FC<ContinueWorkflowConversationProps> = ({
  sessionId,
  workflowName,
  onSendMessage,
  disabled = false,
}) => {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || disabled || isLoading) {
      return;
    }

    setIsLoading(true);
    try {
      await onSendMessage(message.trim());
      setMessage(''); // Clear the input after successful send
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">Continue Workflow Conversation</Label>
        <span className="text-xs text-muted-foreground">Session: {sessionId.slice(0, 8)}...</span>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <Textarea
          placeholder={`Continue the ${workflowName} workflow conversation...`}
          value={message}
          onChange={e => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          className="min-h-[80px] resize-none"
          disabled={disabled || isLoading}
        />

        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            Press Enter to send, Shift+Enter for new line
          </div>
          <Button type="submit" size="sm" disabled={!message.trim() || disabled || isLoading}>
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
        This will continue the workflow execution with your additional input.
      </div>
    </div>
  );
};
