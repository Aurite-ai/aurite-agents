import React from 'react';

interface ToolCallViewProps {
  toolName: string;
  toolInput: Record<string, any>;
  toolId: string;
  status?: 'pending' | 'executing' | 'completed' | 'error'; // Optional status
}

const ToolCallView: React.FC<ToolCallViewProps> = ({ toolName, toolInput, toolId, status }) => {
  return (
    <div className="my-2 p-3 bg-dracula-purple bg-opacity-20 rounded-lg shadow text-sm text-dracula-foreground border border-dracula-purple">
      <div className="font-semibold text-dracula-pink mb-1">
        Tool Call: <span className="font-mono">{toolName}</span> (ID: {toolId})
        {status && <span className="ml-2 text-xs italic text-dracula-comment">[{status}]</span>}
      </div>
      <div className="text-xs">
        <strong className="text-dracula-cyan">Input:</strong>
        <pre className="mt-1 p-2 bg-dracula-background bg-opacity-50 rounded text-xs overflow-x-auto">
          {JSON.stringify(toolInput, null, 2)}
        </pre>
      </div>
    </div>
  );
};

export default ToolCallView;
