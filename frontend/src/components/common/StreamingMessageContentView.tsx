import React from 'react';
import type { AgentOutputContentBlock } from '../../types/projectManagement';
import StructuredResponseView from './StructuredResponseView';
import ToolCallView from './ToolCallView';
import ToolResultView from './ToolResultView';

interface StreamingMessageContentViewProps {
  blocks: AgentOutputContentBlock[];
}

const StreamingMessageContentView: React.FC<StreamingMessageContentViewProps> = ({ blocks }) => {
  if (!blocks || blocks.length === 0) {
    return null; // Or a loading spinner, or some placeholder
  }

  return (
    <div className="streaming-message-content">
      {blocks.map((block, index) => {
        // Key should be more stable if blocks have IDs, fall back to index if not.
        // Assuming block.id is present for tool_use and tool_result as per AgentOutputContentBlock
        const key = block.id ? `${block.type}-${block.id}` : `${block.type}-${index}`;

        switch (block.type) {
          case 'text':
            if (typeof block.text === 'string') {
              // Attempt to parse JSON only if it looks like a JSON object or array
              if (block.text.trim().startsWith('{') || block.text.trim().startsWith('[')) {
                try {
                  const jsonData = JSON.parse(block.text);
                  // Ensure it's an object and not an array or primitive for StructuredResponseView
                  if (typeof jsonData === 'object' && jsonData !== null && !Array.isArray(jsonData)) {
                    return <StructuredResponseView key={key} data={jsonData} />;
                  }
                } catch (e) {
                  // Not valid JSON, or not the type we want for StructuredResponseView, render as plain text
                }
              }
              return <span key={key} className="text-chunk">{block.text}</span>;
            } else if (typeof block.text === 'object' && block.text !== null) {
              // If block.text is already an object (e.g. from schema)
              return <StructuredResponseView key={key} data={block.text as Record<string, any>} />;
            }
            return null;
          case 'tool_use':
            if (block.id && block.name && block.input !== undefined) {
              return (
                <ToolCallView
                  key={key}
                  toolId={block.id}
                  toolName={block.name}
                  toolInput={block.input}
                  // We might need a prop for "isStreamingInput" or "isPending" if input arrives in chunks
                />
              );
            }
            return <span key={key} className="tool-call-placeholder">Tool call forming...</span>;
          case 'tool_result':
            if (block.tool_use_id && block.content !== undefined) {
              return (
                <ToolResultView
                  key={key}
                  toolUseId={block.tool_use_id}
                  toolName={block.name} // Optional: ToolResultView might not always have toolName directly from this block
                  result={block.content}
                  isError={block.is_error ?? false}
                />
              );
            }
            return <span key={key} className="tool-result-placeholder">Tool result pending...</span>;
          default:
            console.warn('Unknown content block type:', block.type);
            return <span key={key} className="unknown-block">Unsupported content type: {block.type}</span>;
        }
      })}
    </div>
  );
};

export default StreamingMessageContentView;
