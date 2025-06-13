import React from 'react';
import type { AgentOutputContentBlock } from '../../types/projectManagement';
// import ToolCallView from './ToolCallView';
// import ToolResultView from './ToolResultView';
// import StructuredResponseView from './StructuredResponseView';

interface StreamingMessageContentViewProps {
  blocks: AgentOutputContentBlock[];
}

const StreamingMessageContentView: React.FC<StreamingMessageContentViewProps> = ({ blocks }) => {
  if (!blocks || blocks.length === 0) {
    return <span className="text-xs text-dracula-comment italic">Assistant is thinking...</span>;
  }

  return (
    <div className="streaming-message-content flex flex-col space-y-2">
      {blocks.map((block, index) => {
        const blockKey = `${block.type}-${block.id || index}`;
        switch (block.type) {
          case 'text':
            return <div key={blockKey} className="text-white whitespace-pre-wrap"><pre><strong>[Text]:</strong> {block.text}</pre></div>;
          case 'thinking_finalized':
            return <div key={blockKey} className="p-2 my-1 bg-dracula-current-line bg-opacity-50 rounded-md text-dracula-comment italic"><pre><strong>[Thinking]:</strong> {block.text}</pre></div>;
          case 'tool_use':
            return (
              <div key={blockKey} className="p-2 my-1 bg-dracula-purple bg-opacity-20 rounded-md">
                <pre><strong>[Tool Call]:</strong> {block.name} (ID: {block.id})</pre>
                <pre className="mt-1 text-xs">Input: {JSON.stringify(block.input, null, 2)}</pre>
              </div>
            );
          case 'tool_result':
            return (
              <div key={blockKey} className={`p-2 my-1 rounded-md ${block.is_error ? 'bg-dracula-red bg-opacity-20' : 'bg-dracula-green bg-opacity-20'}`}>
                <pre><strong>[Tool Result for ID: {block.tool_use_id}]:</strong></pre>
                <pre className="mt-1 text-xs">{typeof block.content === 'string' ? block.content : JSON.stringify(block.content, null, 2)}</pre>
              </div>
            );
          case 'final_response_data':
            return (
              <div key={blockKey} className="p-2 my-1 bg-dracula-selection rounded-md">
                <pre><strong>[Final Response Data]:</strong></pre>
                <pre className="mt-1 text-xs">{block.text}</pre> {/* Displaying the raw text which should be JSON */}
              </div>
            );
          case 'processed_raw_text': // New case for diagnostic
            return <div key={blockKey} className="p-2 my-1 bg-yellow-500 text-black rounded-md"><pre><strong>[DIAGNOSTIC - PROCESSED RAW TEXT]:</strong> {block.text}</pre></div>;
          default:
            return <div key={blockKey} className="text-xs text-dracula-orange"><pre><strong>[Unknown Block Type: {block.type}]</strong> {JSON.stringify(block, null, 2)}</pre></div>;
        }
      })}
    </div>
  );
};

export default StreamingMessageContentView;
