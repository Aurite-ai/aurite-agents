import React, { useEffect, useState } from 'react';
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs/components/prism-core';
import 'prismjs/components/prism-json';
import 'prismjs/themes/prism-okaidia.css'; // Using Okaidia theme for dark mode

// Import the new generic functions
import {
  getConfigFileContent as fetchFileContentGeneric,
  saveConfigFileContent as saveFileContentGeneric
} from '../../../lib/apiClient';
import type { SelectedSidebarItemType } from '../../../components/layout/ComponentSidebar'; // Changed ComponentType to SelectedSidebarItemType

interface ConfigEditorViewProps {
  componentType: SelectedSidebarItemType; // Changed ComponentType to SelectedSidebarItemType
  filename: string;
  onClose: () => void; // To go back to the list view
}

const ConfigEditorView: React.FC<ConfigEditorViewProps> = ({
  componentType,
  filename,
  onClose,
}) => {
  // Store the initial props in state, only set once on mount
  const [initialComponentType] = useState(componentType);
  const [initialFilename] = useState(filename);

  const [code, setCode] = useState<string>('// Loading...');
  const [isLoading, setIsLoading] = useState<boolean>(false); // For initial content loading
  const [error, setError] = useState<string | null>(null); // For initial content loading error
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const fetchConfigContent = async () => {
      // Use the initial state values for fetching, ignore prop changes after mount
      if (!initialComponentType || !initialFilename) return;

      setIsLoading(true);
      setError(null);
      try {
        // Use the new generic function from apiClient.ts with initial state values
        const data = await fetchFileContentGeneric(initialComponentType as string, initialFilename);
        setCode(JSON.stringify(data, null, 2)); // Pretty print JSON
      } catch (err) {
        console.error('Error fetching config content:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
        setCode(`// Error loading ${initialFilename}:\n// ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
        setIsLoading(false);
      }
    };

    fetchConfigContent();
    // Depend only on the initial state values (or effectively, run only once on mount)
  }, [initialComponentType, initialFilename]);

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
      // Use the new generic function from apiClient.ts with initial state values
      await saveFileContentGeneric(initialComponentType as string, initialFilename, parsedContent);
      setSaveStatus('Configuration saved successfully!');
      // Optionally, clear status after a few seconds
      // TODO: Consider triggering a refresh of the list view data?
      // e.g., useProjectStore.getState().notifyComponentsUpdate();
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
          {/* Display initial values, not potentially changed props */}
          Editing: {initialFilename} ({initialComponentType})
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
