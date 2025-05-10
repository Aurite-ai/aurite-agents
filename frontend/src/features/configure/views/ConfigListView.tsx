import React, { useEffect, useState } from 'react';
import apiClient from '../../../lib/apiClient'; // Adjust path as needed
import useUIStore from '../../../store/uiStore'; // Adjust path as needed
import useProjectStore from '../../../store/projectStore'; // Added
import type { ComponentType } from '../../../components/layout/ComponentSidebar'; // Adjust path as needed
import ConfigEditorView from './ConfigEditorView'; // Import the editor view

interface ConfigFile {
  name: string;
  // We can add more details later, like last modified, size, etc.
}

const ConfigListView: React.FC = () => {
  const { selectedComponent } = useUIStore();
  const { lastComponentsUpdateTimestamp } = useProjectStore(); // Added
  const [configFiles, setConfigFiles] = useState<ConfigFile[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  // Rename selectedFile to editingFile to better reflect its purpose
  const [editingFile, setEditingFile] = useState<string | null>(null);

  useEffect(() => {
    // When selectedComponent changes, clear any file being edited
    setEditingFile(null);

    const fetchConfigFiles = async () => {
      if (!selectedComponent) return;

      setIsLoading(true);
      setError(null);
      setConfigFiles([]); // Clear previous files

      try {
        // Map UI component type to API component type if necessary
        // For now, assuming they are the same or selectedComponent is already the API type
        const apiComponentType = selectedComponent;

        const response = await apiClient(`/configs/${apiComponentType}`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `Failed to fetch ${apiComponentType} configs`);
        }
        const data: string[] = await response.json();
        setConfigFiles(data.map(name => ({ name })));
      } catch (err) {
        console.error('Error fetching config files:', err);
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    fetchConfigFiles();
  }, [selectedComponent, lastComponentsUpdateTimestamp]); // Added lastComponentsUpdateTimestamp

  const handleFileSelect = (filename: string) => {
    setEditingFile(filename);
  };

  const handleCloseEditor = () => {
    setEditingFile(null);
    // Optionally, could re-fetch the list here if edits might change it,
    // or rely on a save action in the editor to trigger a list refresh.
  };

  if (editingFile && selectedComponent) {
    return (
      <ConfigEditorView
        componentType={selectedComponent}
        filename={editingFile}
        onClose={handleCloseEditor}
      />
    );
  }

  // Displaying list view content
  if (isLoading) {
    return <p className="text-dracula-comment">Loading configuration files...</p>;
  }

  if (error) {
    return <p className="text-dracula-red">Error: {error}</p>;
  }

  return (
    <div className="p-1">
      <h3 className="text-lg font-semibold text-dracula-purple mb-3">
        {selectedComponent.charAt(0).toUpperCase() + selectedComponent.slice(1)} Configurations
      </h3>
      {configFiles.length === 0 ? (
        <p className="text-dracula-comment">No configuration files found for {selectedComponent}.</p>
      ) : (
        <ul className="space-y-2">
          {configFiles.map((file) => (
            <li key={file.name}>
              <button
                onClick={() => handleFileSelect(file.name)}
                className={`w-full text-left p-3 rounded-md transition-colors duration-150 ease-in-out
                  focus:outline-none focus:ring-2 focus:ring-dracula-pink
                  ${
                    editingFile === file.name // This active state might not be needed if we switch views
                      ? 'bg-dracula-pink text-dracula-background'
                      : 'bg-dracula-current-line hover:bg-opacity-80 text-dracula-foreground focus:bg-dracula-comment focus:bg-opacity-50'
                  }
                `}
              >
                {file.name}
              </button>
            </li>
          ))}
        </ul>
      )}
      {/* TODO: Add "Create New" button here */}
    </div>
  );
};

export default ConfigListView;
