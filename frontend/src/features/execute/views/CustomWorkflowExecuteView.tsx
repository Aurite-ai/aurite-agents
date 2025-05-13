import React, { useState } from 'react';
import { executeCustomWorkflowAPI } from '../../../lib/apiClient';
import type { ExecuteCustomWorkflowResponse } from '../../../types/projectManagement';

interface CustomWorkflowExecuteViewProps {
  workflowName: string;
  onClose: () => void;
}

const CustomWorkflowExecuteView: React.FC<CustomWorkflowExecuteViewProps> = ({ workflowName, onClose }) => {
  const [inputValue, setInputValue] = useState<string>('');
  const [outputValue, setOutputValue] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunWorkflow = async () => {
    if (!inputValue.trim()) {
      setError('Input cannot be empty.');
      return;
    }
    setIsLoading(true);
    setOutputValue(null);
    setError(null);

    try {
      // Attempt to parse input as JSON, otherwise send as string
      let parsedInput: any;
      try {
        parsedInput = JSON.parse(inputValue);
      } catch (e) {
        parsedInput = inputValue;
      }

      const response: ExecuteCustomWorkflowResponse = await executeCustomWorkflowAPI(workflowName, parsedInput);

      if (response.status === 'completed') {
        let processedResult = response.result;
        // Check if the result is an object and contains agent_result_text as a string
        if (processedResult && typeof processedResult === 'object' && typeof (processedResult as any).agent_result_text === 'string') {
          try {
            const parsedAgentResult = JSON.parse((processedResult as any).agent_result_text);
            // Create a new object to avoid mutating the original response.result directly if it's complex
            processedResult = {
              ...processedResult,
              agent_result_text: parsedAgentResult,
            };
          } catch (e) {
            // If agent_result_text is not valid JSON, leave it as a string.
            console.warn('agent_result_text could not be parsed as JSON:', (processedResult as any).agent_result_text, e);
          }
        }

        if (typeof processedResult === 'string') {
          setOutputValue(processedResult);
        } else {
          setOutputValue(JSON.stringify(processedResult, null, 2));
        }
      } else {
        setError(response.error || 'Workflow execution failed.');
      }
    } catch (err) {
      console.error('Error executing custom workflow:', err);
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
          Execute Custom Workflow: {workflowName}
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
            Input (JSON or Plain Text):
          </label>
          <textarea
            id="workflowInput"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter workflow input here..."
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
              Output:
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

export default CustomWorkflowExecuteView;
