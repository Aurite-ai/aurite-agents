import React, { type JSX } from 'react';
import type { AgentOutputContentBlock } from '../../types/projectManagement'; // For nested content

interface ToolResultViewProps {
  toolName?: string; // Optional: if you want to display which tool this result is for
  toolUseId: string;
  result: string | Record<string, any> | AgentOutputContentBlock[]; // Can be simple string, JSON object, or list of content blocks
  isError?: boolean;
}

const renderResultContent = (content: any): JSX.Element => {
  if (typeof content === 'string') {
    // If it's a simple string, display it.
    // Could be plain text or a JSON string needing parsing if it's from an error.
    try {
      const parsedJson = JSON.parse(content);
      // If it parses, pretty print it, otherwise show as string
      return (
        <pre className="mt-1 p-2 bg-dracula-background bg-opacity-50 rounded text-xs overflow-x-auto">
          {JSON.stringify(parsedJson, null, 2)}
        </pre>
      );
    } catch (e) {
      return <span>{content}</span>;
    }
  }
  if (Array.isArray(content)) {
    // If it's an array (likely of content blocks from Anthropic's tool result format)
    return (
      <div>
        {content.map((block, index) => {
          if (block.type === 'text' && block.text) {
            return <p key={index} className="mb-1">{block.text}</p>;
          }
          // Add rendering for other potential block types if necessary
          return <pre key={index} className="mt-1 p-2 bg-dracula-background bg-opacity-50 rounded text-xs overflow-x-auto">{JSON.stringify(block, null, 2)}</pre>;
        })}
      </div>
    );
  }
  if (typeof content === 'object' && content !== null) {
    return (
      <pre className="mt-1 p-2 bg-dracula-background bg-opacity-50 rounded text-xs overflow-x-auto">
        {JSON.stringify(content, null, 2)}
      </pre>
    );
  }
  return <span className="text-dracula-comment">No displayable content for tool result.</span>;
};

const ToolResultView: React.FC<ToolResultViewProps> = ({ toolName, toolUseId, result, isError }) => {
  const bgColor = isError ? 'bg-dracula-red bg-opacity-30 border-dracula-red' : 'bg-dracula-green bg-opacity-20 border-dracula-green';
  const titleColor = isError ? 'text-dracula-red' : 'text-dracula-green';

  return (
    <div className={`my-2 p-3 ${bgColor} rounded-lg shadow text-sm text-dracula-foreground border`}>
      <div className={`font-semibold ${titleColor} mb-1`}>
        Tool Result {toolName && <span className="font-mono">({toolName})</span>} for ID: {toolUseId}
        {isError && <span className="ml-2 text-xs italic text-white">(Error)</span>}
      </div>
      <div className="text-xs">
        {renderResultContent(result)}
      </div>
    </div>
  );
};

export default ToolResultView;
