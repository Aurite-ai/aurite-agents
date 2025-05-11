import React, { useState } from 'react';
import { executeSimpleWorkflowAPI } from '../../../lib/apiClient';
import type { ExecuteWorkflowResponse } from '../../../types/projectManagement';

interface SimpleWorkflowExecuteViewProps {
  workflowName: string;
  onClose: () => void;
}

const SimpleWorkflowExecuteView: React.FC<SimpleWorkflowExecuteViewProps> = ({ workflowName, onClose }) => {
  const [inputValue, setInputValue] = useState<string>('');
  const [outputValue, setOutputValue] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunWorkflow = async () => {
    if (!inputValue.trim()) {
      setError('Input message cannot be empty.');
      return;
    }
    setIsLoading(true);
    setOutputValue(null);
    setError(null);

    try {
      const response: ExecuteWorkflowResponse = await executeSimpleWorkflowAPI(workflowName, inputValue);

      if (response.status === 'completed') {
        setOutputValue(response.final_message || 'Workflow completed, but no final message was returned.');
      } else {
        setError(response.error || 'Workflow execution failed.');
      }
    } catch (err) {
      console.error('Error executing simple workflow:', err);
      const apiError = err as any;
      setError(apiError.message || 'An unexpected error occurred during execution.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-dracula-background p-4 rounded-lg shadow-md border border-dracula-current-line max-w-4xl mx-auto">
      <div className="flex justify-between items-center p-3 border-b border-dracula-comment bg-dracula-current-line rounded-t-lg mb-4">
        <h3 className="text-xl font-semibold text-dracula-cyan">
          Execute Simple Workflow: {workflowName}
        </h3>
        <button
          onClick={onClose}
          className="text-sm bg-dracula-purple hover:bg-opacity-80 text-dracula-background py-1 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-dracula-pink"
        >
          Back to List
        </button>
      </div>

      <div className="flex-grow flex flex-col space-y-4 overflow-y-auto">
        {/* Input Section */}
        <div className="space-y-2">
          <label htmlFor="workflowInput" className="block text-sm font-medium text-dracula-foreground">
            Initial User Message:
          </label>
          <textarea
            id="workflowInput"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter initial user message here..."
            rows={8}
            className="w-full p-2 rounded-md bg-dracula-current-line text-dracula-foreground border border-dracula-comment focus:ring-2 focus:ring-dracula-pink focus:border-dracula-pink"
            disabled={isLoading}
          />
          <button
            onClick={handleRunWorkflow}
            disabled={isLoading || !inputValue.trim()}
            className="px-4 py-2 bg-dracula-green text-dracula-background font-semibold rounded-md hover:bg-opacity-90 focus:outline-none focus:ring-2 focus:ring-dracula-pink disabled:bg-dracula-comment disabled:cursor-not-allowed"
          >
            {isLoading ? 'Running...' : 'Run Workflow'}
          </button>
        </div>

        {/* Output Section */}
        {isLoading && (
          <p className="text-dracula-comment text-center">Running workflow...</p>
        )}
        {error && (
          <div className="p-3 rounded-md bg-dracula-red bg-opacity-30 text-dracula-red border border-dracula-red">
            <p className="font-semibold">Error:</p>
            <pre className="whitespace-pre-wrap text-sm">{error}</pre>
          </div>
        )}
        {outputValue !== null && (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-dracula-foreground">
              Final Message:
            </label>
            <pre className="w-full p-3 rounded-md bg-dracula-current-line text-dracula-foreground border border-dracula-comment overflow-x-auto text-sm">
              {outputValue}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default SimpleWorkflowExecuteView;
