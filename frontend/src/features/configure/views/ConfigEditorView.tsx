import React, { useEffect, useState } from 'react';
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs/components/prism-core';
import 'prismjs/components/prism-json';
import 'prismjs/themes/prism-okaidia.css'; // Using Okaidia theme for dark mode

import apiClient from '../../../lib/apiClient';
import type { ComponentType } from '../../../components/layout/ComponentSidebar';

interface ConfigEditorViewProps {
  componentType: ComponentType;
  filename: string;
  onClose: () => void; // To go back to the list view
}

const ConfigEditorView: React.FC<ConfigEditorViewProps> = ({
  componentType,
  filename,
  onClose,
}) => {
  const [code, setCode] = useState<string>('// Loading...');
  const [isLoading, setIsLoading] = useState<boolean>(false); // For initial content loading
  const [error, setError] = useState<string | null>(null); // For initial content loading error
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const fetchConfigContent = async () => {
      if (!componentType || !filename) return;

      setIsLoading(true);
      setError(null);
      try {
        const response = await apiClient(`/configs/${componentType}/${filename}`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `Failed to fetch ${filename}`);
        }
        const data = await response.json(); // Assuming content is JSON
        setCode(JSON.stringify(data, null, 2)); // Pretty print JSON
      } catch (err) {
        console.error('Error fetching config content:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
        setCode(`// Error loading ${filename}:\n// ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
        setIsLoading(false);
      }
    };

    fetchConfigContent();
  }, [componentType, filename]);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus(null);
    setSaveError(null);

    let parsedContent: object;
    try {
      parsedContent = JSON.parse(code);
    } catch (parseError) {
      setSaveError('Invalid JSON format. Please correct and try again.');
      setIsSaving(false);
      return;
    }

    try {
      const response = await apiClient(`/configs/${componentType}/${filename}`, {
        method: 'PUT',
        body: { content: parsedContent }, // apiClient will stringify this
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to save ${filename}`);
      }

      setSaveStatus('Configuration saved successfully!');
      // Optionally, clear status after a few seconds
      setTimeout(() => setSaveStatus(null), 3000);

    } catch (err) {
      console.error('Error saving config content:', err);
      setSaveError(err instanceof Error ? err.message : 'An unknown error occurred during save.');
    } finally {
      setIsSaving(false);
    }
  };

  const editorStyle = {
    fontFamily: '"Fira code", "Fira Mono", monospace',
    fontSize: 14,
    backgroundColor: '#282a36', // dracula-background
    borderRadius: '0.375rem', // rounded-md
    border: '1px solid #44475a', // dracula-current-line (or comment for softer border)
    minHeight: '300px',
    overflow: 'auto',
  };

  if (isLoading) {
    return <p className="text-dracula-comment">Loading editor...</p>;
  }

  return (
    <div className="p-1">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-dracula-purple">
          Editing: {filename} ({componentType})
        </h3>
        <button
            onClick={onClose}
            className="bg-dracula-comment hover:bg-opacity-80 text-dracula-foreground font-semibold py-2 px-4 rounded-md text-sm"
        >
            Back to List
        </button>
      </div>

      {error && <p className="text-dracula-red mb-2">Initial Load Error: {error}</p>}

      <div className="bg-dracula-background p-0.5 rounded-md shadow-lg" style={{ minHeight: '300px' }}>
        <Editor
          value={code}
          onValueChange={newCode => setCode(newCode)}
          highlight={codeToHighlight => highlight(codeToHighlight, languages.json, 'json')}
          padding={10}
          style={editorStyle}
          className="text-dracula-foreground" // Ensure text color is applied
          disabled={isLoading || isSaving} // Disable editor while loading or saving
        />
      </div>

      {saveStatus && <p className="mt-2 text-sm text-dracula-green">{saveStatus}</p>}
      {saveError && <p className="mt-2 text-sm text-dracula-red">{saveError}</p>}

      <button
        onClick={handleSave}
        className="mt-4 bg-dracula-green hover:bg-opacity-80 text-dracula-background font-semibold py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-dracula-pink disabled:opacity-50 disabled:bg-dracula-comment"
        disabled={isLoading || isSaving}
      >
        {isSaving ? 'Saving...' : 'Save Configuration'}
      </button>
    </div>
  );
};

export default ConfigEditorView;
