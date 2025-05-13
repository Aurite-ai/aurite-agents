import React, { useState } from 'react';
import { createProjectFile } from '../../lib/apiClient'; // Adjust path as needed
import useProjectStore from '../../store/projectStore'; // Adjust path as needed
import type { ApiError } from '../../types/projectManagement'; // Adjust path

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const CreateProjectModal: React.FC<CreateProjectModalProps> = ({ isOpen, onClose }) => {
  const [filename, setFilename] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { fetchAvailableProjectFiles } = useProjectStore.getState();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    if (!filename.endsWith('.json')) {
      setError({ message: 'Filename must end with .json' });
      setIsLoading(false);
      return;
    }

    try {
      await createProjectFile(filename, projectName, projectDescription);
      setSuccessMessage(`Project "${projectName}" created successfully in ${filename}!`);
      fetchAvailableProjectFiles(); // Refresh the list of project files
      // Reset form and close modal after a short delay to show success
      setTimeout(() => {
        setFilename('');
        setProjectName('');
        setProjectDescription('');
        onClose();
        setSuccessMessage(null); // Clear success message before next open
      }, 2000);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-dracula-current-line p-6 rounded-lg shadow-xl w-full max-w-md">
        <h2 className="text-xl font-semibold text-dracula-foreground mb-4">Create New Project</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="filename" className="block text-sm font-medium text-dracula-comment mb-1">
              Project Filename (e.g., my_project.json)
            </label>
            <input
              type="text"
              id="filename"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              className="w-full p-2 bg-dracula-background border border-dracula-comment rounded-md text-dracula-foreground focus:ring-dracula-pink focus:border-dracula-pink"
              required
            />
          </div>
          <div className="mb-4">
            <label htmlFor="projectName" className="block text-sm font-medium text-dracula-comment mb-1">
              Project Name
            </label>
            <input
              type="text"
              id="projectName"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="w-full p-2 bg-dracula-background border border-dracula-comment rounded-md text-dracula-foreground focus:ring-dracula-pink focus:border-dracula-pink"
              required
            />
          </div>
          <div className="mb-4">
            <label htmlFor="projectDescription" className="block text-sm font-medium text-dracula-comment mb-1">
              Project Description (Optional)
            </label>
            <textarea
              id="projectDescription"
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              rows={3}
              className="w-full p-2 bg-dracula-background border border-dracula-comment rounded-md text-dracula-foreground focus:ring-dracula-pink focus:border-dracula-pink"
            />
          </div>

          {error && (
            <div className="mb-4 p-3 bg-dracula-red bg-opacity-20 text-dracula-red rounded-md text-sm">
              Error: {error.message}
              {error.details && <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(error.details, null, 2)}</pre>}
            </div>
          )}
          {successMessage && (
            <div className="mb-4 p-3 bg-dracula-green bg-opacity-20 text-dracula-green rounded-md text-sm">
              {successMessage}
            </div>
          )}

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={() => {
                onClose();
                setError(null);
                setSuccessMessage(null);
              }}
              className="py-2 px-4 bg-dracula-comment text-dracula-foreground rounded-md hover:bg-opacity-80 transition-colors"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="py-2 px-4 bg-dracula-pink text-dracula-background rounded-md hover:bg-opacity-80 transition-colors disabled:opacity-50"
              disabled={isLoading}
            >
              {isLoading ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateProjectModal;
