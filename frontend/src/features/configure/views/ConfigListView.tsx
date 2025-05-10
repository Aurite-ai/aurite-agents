import React, { useEffect, useState } from 'react';
// Import the new generic function
import { listConfigFiles as fetchFilesGeneric } from '../../../lib/apiClient'; // Renamed import
import useUIStore from '../../../store/uiStore';
import useProjectStore from '../../../store/projectStore';
import type { SelectedSidebarItemType } from '../../../components/layout/ComponentSidebar'; // Changed ComponentType to SelectedSidebarItemType
import ConfigEditorView from './ConfigEditorView';

interface ConfigFile {
  name: string;
  // We can add more details later, like last modified, size, etc.
}

const ConfigListView: React.FC = () => {
  const { selectedComponent } = useUIStore() as { selectedComponent: SelectedSidebarItemType | null }; // Cast for clarity
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
        // Use the new generic function from apiClient.ts
        const data: string[] = await fetchFilesGeneric(selectedComponent as string); // selectedComponent might be null, handle or ensure it's passed correctly
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
        componentType={selectedComponent as SelectedSidebarItemType} // Ensure type matches
        filename={editingFile}
        onClose={handleCloseEditor}
      />
    );
  }

  // Displaying list view content
  if (!selectedComponent) { // Handle case where no component is selected yet
    return <p className="text-dracula-comment p-1">Please select a component type from the sidebar.</p>;
  }

  if (isLoading) {
    return <p className="text-dracula-comment p-1">Loading configuration files...</p>;
  }

  if (error) {
    return <p className="text-dracula-red p-1">Error: {error}</p>;
  }

  return (
    <div className="p-1">
      <h3 className="text-lg font-semibold text-dracula-purple mb-3">
        {(selectedComponent as string).charAt(0).toUpperCase() + (selectedComponent as string).slice(1)} Configurations
      </h3>
      {configFiles.length === 0 ? (
        <p className="text-dracula-comment">No configuration files found for {selectedComponent as string}.</p>
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
