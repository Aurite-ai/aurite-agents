import React from 'react';
import { Copy, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ResponseDisplayProps } from '@/types/execution';

export const ResponseDisplay: React.FC<ResponseDisplayProps> = ({
  content,
  isStreaming = false,
  onCopy,
  onExport
}) => {
  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    onCopy?.();
  };

  // Simple markdown-like rendering for now
  // This will be enhanced with react-markdown later
  const renderContent = (text: string) => {
    // Split by lines and process basic markdown
    const lines = text.split('\n');
    
    return lines.map((line, index) => {
      // Headers
      if (line.startsWith('# ')) {
        return (
          <h1 key={index} className="text-xl font-bold mt-4 mb-2">
            {line.substring(2)}
          </h1>
        );
      }
      if (line.startsWith('## ')) {
        return (
          <h2 key={index} className="text-lg font-semibold mt-3 mb-2">
            {line.substring(3)}
          </h2>
        );
      }
      if (line.startsWith('### ')) {
        return (
          <h3 key={index} className="text-base font-medium mt-2 mb-1">
            {line.substring(4)}
          </h3>
        );
      }

      // Code blocks
      if (line.startsWith('```')) {
        return (
          <div key={index} className="bg-muted p-3 rounded-md font-mono text-sm my-2">
            {line.substring(3)}
          </div>
        );
      }

      // Inline code
      const codeRegex = /`([^`]+)`/g;
      if (codeRegex.test(line)) {
        const parts = line.split(codeRegex);
        return (
          <p key={index} className="mb-2">
            {parts.map((part, partIndex) => 
              partIndex % 2 === 1 ? (
                <code key={partIndex} className="bg-muted px-1 py-0.5 rounded text-sm font-mono">
                  {part}
                </code>
              ) : (
                part
              )
            )}
          </p>
        );
      }

      // Bold text
      const boldRegex = /\*\*([^*]+)\*\*/g;
      if (boldRegex.test(line)) {
        const parts = line.split(boldRegex);
        return (
          <p key={index} className="mb-2">
            {parts.map((part, partIndex) => 
              partIndex % 2 === 1 ? (
                <strong key={partIndex}>{part}</strong>
              ) : (
                part
              )
            )}
          </p>
        );
      }

      // Lists
      if (line.startsWith('- ') || line.startsWith('* ')) {
        return (
          <li key={index} className="ml-4 mb-1">
            {line.substring(2)}
          </li>
        );
      }

      // Empty lines
      if (line.trim() === '') {
        return <br key={index} />;
      }

      // Regular paragraphs
      return (
        <p key={index} className="mb-2">
          {line}
        </p>
      );
    });
  };

  return (
    <div className="space-y-3">
      {/* Content */}
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <div className="text-sm leading-relaxed break-words overflow-wrap-anywhere">
          {renderContent(content)}
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
          )}
        </div>
      </div>

      {/* Actions */}
      {content && !isStreaming && (
        <div className="flex items-center gap-2 pt-2 border-t">
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopy}
            className="h-7 px-2 text-xs"
          >
            <Copy className="h-3 w-3 mr-1" />
            Copy
          </Button>
          
          {onExport && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onExport('markdown')}
              className="h-7 px-2 text-xs"
            >
              <Download className="h-3 w-3 mr-1" />
              Export
            </Button>
          )}
        </div>
      )}
    </div>
  );
};
