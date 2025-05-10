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
    // Return a placeholder if there are no blocks yet, or if the parent indicates loading
    return <span className="text-xs text-dracula-comment italic">Assistant is working...</span>;
  }

  return (
    <div className="flex flex-col space-y-2">
      {blocks.map((block, index) => {
        const key = block.id ? `${block.type}-${block.id}-${index}` : `${block.type}-${index}`;

        switch (block.type) {
          case 'final_response_data':
            return (
              <div key={key}>
                {block.thinkingText && (
                  <div className="whitespace-pre-wrap p-2 my-1 border border-dashed border-dracula-comment rounded-md bg-dracula-current-line bg-opacity-30">
                    <span className="text-xs text-dracula-comment italic">Thinking:</span>
                    <div className="text-sm">{block.thinkingText}</div>
                  </div>
                )}
                {block.parsedJson && (
                  <StructuredResponseView data={block.parsedJson} />
                )}
                {!block.parsedJson && block.text && ( // Fallback for raw JSON string if parsing failed at view but was intended
                  <div className="whitespace-pre-wrap text-xs text-dracula-comment italic">Raw JSON: {block.text}</div>
                )}
              </div>
            );
          // case 'structured_json': // This type is now replaced by 'final_response_data'
          //   if (block.parsedJson) {
          //     return <StructuredResponseView key={key} data={block.parsedJson} />;
          //   }
          //   // Fallback if parsedJson is somehow missing, try to parse from text
          //   if (typeof block.text === 'string') {
          //     try {
          //       const jsonData = JSON.parse(block.text);
          //       if (typeof jsonData === 'object' && jsonData !== null && !Array.isArray(jsonData)) {
          //         return <StructuredResponseView key={key} data={jsonData} />;
          //       }
          //     } catch (e) { /* Fall through to render as text */ }
          //   }
          //   // If all else fails, render the raw text of the supposed JSON
          //   return <div key={key} className="whitespace-pre-wrap text-xs text-dracula-comment italic">Raw JSON: {block.text}</div>;

          case 'text':
            // This case now primarily handles non-JSON text, like <thinking> blocks that weren't part of final_response_data
            // or text that failed to parse as JSON in the 'final_response_data' case's fallback.
            if (typeof block.text === 'string') {
              return <div key={key} className="whitespace-pre-wrap">{block.text}</div>;
            }
            // If block.text was already an object (should be rare now with AgentChatView changes)
            if (typeof block.text === 'object' && block.text !== null) {
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
                  toolInput={block.input as Record<string, any>}
                />
              );
            }
            return <div key={key} className="text-xs text-dracula-comment italic">Tool call forming...</div>;

          case 'tool_result':
            if (block.tool_use_id && block.content !== undefined) {
              return (
                <ToolResultView
                  key={key}
                  toolUseId={block.tool_use_id}
                  toolName={block.name}
                  result={block.content as any}
                  isError={block.is_error ?? false}
                />
              );
            }
            return <div key={key} className="text-xs text-dracula-comment italic">Tool result pending...</div>;

          case 'placeholder':
            return null; // Don't render placeholders

          default:
            console.warn('StreamingMessageContentView: Unknown block type or unhandled block', block);
            const fallbackText = typeof block.text === 'string' ? block.text : JSON.stringify(block.text);
            return fallbackText ? <div key={key} className="whitespace-pre-wrap text-xs text-dracula-comment italic"> (Raw/Unknown: {fallbackText})</div> : null;
        }
      })}
    </div>
  );
};

export default StreamingMessageContentView;
