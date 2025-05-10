import React from 'react';

export interface ChatMessageData {
  id: string;
  role: 'user' | 'assistant' | 'error' | 'system';
  content: string;
  timestamp: Date;
}

interface ChatMessageBubbleProps {
  message: ChatMessageData;
}

const ChatMessageBubble: React.FC<ChatMessageBubbleProps> = ({ message }) => {
  return (
    <div
      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-xl p-3 rounded-lg shadow whitespace-pre-wrap
          ${message.role === 'user' ? 'bg-dracula-purple text-white' : ''}
          ${message.role === 'assistant' ? 'bg-dracula-current-line text-dracula-foreground' : ''}
          ${message.role === 'error' ? 'bg-dracula-red text-white' : ''}
          ${message.role === 'system' ? 'bg-dracula-comment text-dracula-foreground text-xs italic' : ''}
        `}
      >
        {message.content}
        <div className="text-xs opacity-60 mt-1">
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
};

export default ChatMessageBubble;
