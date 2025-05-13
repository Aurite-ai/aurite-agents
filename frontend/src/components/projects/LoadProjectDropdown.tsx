import React, { useState, useEffect, useRef } from 'react';
import { loadProjectComponents } from '../../lib/apiClient'; // Adjust path as needed
import useProjectStore from '../../store/projectStore'; // Adjust path as needed
import type { ApiError } from '../../types/projectManagement'; // Adjust path

interface LoadProjectDropdownProps {
  // Props to control visibility from Header, if needed, or can be self-contained
}

const LoadProjectDropdown: React.FC<LoadProjectDropdownProps> = () => {
  const {
    availableProjectFiles,
    fetchAvailableProjectFiles,
    isLoadingProjectFiles,
    projectFileError,
    notifyComponentsUpdated
  } = useProjectStore();

  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false); // Local loading for individual load action
  const [error, setError] = useState<ApiError | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchAvailableProjectFiles();
  }, [fetchAvailableProjectFiles]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleLoadProject = async (projectFilename: string) => {
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);
    setIsOpen(false); // Close dropdown on selection

    const projectConfigPath = `config/projects/${projectFilename}`;

    try {
      const result = await loadProjectComponents(projectConfigPath);
      setSuccessMessage(result.message || `Successfully loaded components from ${projectFilename}.`);
      notifyComponentsUpdated(); // Notify other parts of the UI to refresh
      setTimeout(() => setSuccessMessage(null), 3000); // Clear message after 3s
    } catch (err) {
      setError(err as ApiError);
      setTimeout(() => setError(null), 5000); // Clear error after 5s
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => {
          setIsOpen(!isOpen);
          if (!isOpen) fetchAvailableProjectFiles(); // Refresh list when opening
        }}
        className="py-2 px-4 bg-dracula-purple text-dracula-foreground rounded-md hover:bg-opacity-80 transition-colors focus:outline-none focus:ring-2 focus:ring-dracula-pink focus:ring-opacity-75"
      >
        Load Project
      </button>
      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 bg-dracula-current-line rounded-md shadow-lg z-50 border border-dracula-comment">
          <div className="p-2">
            {isLoadingProjectFiles && <div className="p-2 text-dracula-comment">Loading projects...</div>}
            {projectFileError && <div className="p-2 text-dracula-red">Error: {projectFileError.message}</div>}
            {!isLoadingProjectFiles && !projectFileError && availableProjectFiles.length === 0 && (
              <div className="p-2 text-dracula-comment">No projects found.</div>
            )}
            {!isLoadingProjectFiles && availableProjectFiles.length > 0 && (
              <ul>
                {availableProjectFiles.map((file) => (
                  <li key={file}>
                    <button
                      onClick={() => handleLoadProject(file)}
                      className="w-full text-left px-3 py-2 text-sm text-dracula-foreground hover:bg-dracula-selection rounded-md transition-colors"
                      disabled={isLoading}
                    >
                      {file}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
      {/* Global messages for load operation status */}
      {isLoading && (
        <div className="fixed bottom-4 right-4 p-3 bg-dracula-comment text-dracula-foreground rounded-md shadow-lg z-50">
          Loading selected project...
        </div>
      )}
      {error && (
        <div className="fixed bottom-4 right-4 p-3 bg-dracula-red text-white rounded-md shadow-lg z-50">
          Error: {error.message}
        </div>
      )}
      {successMessage && (
        <div className="fixed bottom-4 right-4 p-3 bg-dracula-green text-dracula-background rounded-md shadow-lg z-50">
          {successMessage}
        </div>
      )}
    </div>
  );
};

export default LoadProjectDropdown;
