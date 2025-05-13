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
          case 'thinking_finalized':
            return (
              <div key={key} className="whitespace-pre-wrap p-2 my-1 border border-dashed border-dracula-comment rounded-md bg-dracula-current-line bg-opacity-30">
                <span className="text-xs text-dracula-comment italic">Thinking:</span>
                <div className="text-sm">{block.text}</div> {/* block.text now holds the thinking content */}
              </div>
            );

          case 'final_response_data':
            return (
              <div key={key}>
                {/* thinkingText property is no longer used here; thinking is handled by 'thinking_finalized' type */}
                {block.parsedJson && (
                  <StructuredResponseView data={block.parsedJson} />
                )}
                {!block.parsedJson && block.text && (
                  // This case might occur if json_stream failed to parse but was finalized as final_response_data with raw text
                  <div className="whitespace-pre-wrap text-xs text-dracula-red italic">Raw (Unparsed) Response: {block.text}</div>
                )}
              </div>
            );

          case 'text':
            // This case now handles plain text from the agent, or text that was part of thinking stream before finalization.
            // Also, user messages if this component were used for them (though typically it's for assistant messages).
            if (typeof block.text === 'string') {
              // Avoid rendering raw <thinking> tags if a block is temporarily 'text' during streaming
              if (block.text.startsWith("<thinking>") && block.text.endsWith("</thinking>")) {
                 // Potentially show a generic "Assistant is working..." or the raw text if preferred during transition
                 return <div key={key} className="whitespace-pre-wrap text-xs text-dracula-comment italic">Processing...</div>;
              }
              return <div key={key} className="whitespace-pre-wrap">{block.text}</div>;
            }
            if (typeof block.text === 'object' && block.text !== null) { // Should be rare
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
