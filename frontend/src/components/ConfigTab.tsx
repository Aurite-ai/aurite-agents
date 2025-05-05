import React, { useState, useEffect } from 'react';

// Base URL for the API (adjust if necessary)
const API_BASE_URL = ''; // Assuming FastAPI runs on the same origin

// Helper function for API calls
async function makeApiRequest(url: string, method: string, apiKey: string | null, body?: any) {
    if (!apiKey) {
        throw new Error('API Key is required.');
    }

    const headers: HeadersInit = {
        'X-API-Key': apiKey,
    };
    const options: RequestInit = {
        method: method,
        headers: headers,
    };

    if (body) {
        headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE_URL}${url}`, options);

    if (!response.ok) {
        let errorDetail = `HTTP error! status: ${response.status}`;
        try {
            const errorData = await response.json();
            errorDetail = errorData.detail || errorDetail;
        } catch (e) {
            // Ignore if response is not JSON
        }
        throw new Error(errorDetail);
    }

    // For DELETE requests with 200 OK but no content, or other methods expecting JSON
    if (response.status === 204 || response.headers.get('content-length') === '0') {
        return null; // Or return a success indicator if preferred
    }
     // Handle 200 OK for DELETE that returns JSON
    if (method === 'DELETE' && response.status === 200) {
        return await response.json();
    }
    // Handle other successful responses (GET, POST, PUT)
    if (response.status === 200 || response.status === 201) {
         return await response.json();
    }
    // Fallback for unexpected success codes
    return null;
}


// --- API Interaction Functions ---

const fetchConfigFiles = async (type: string, apiKey: string | null): Promise<string[]> => {
  console.log(`Fetching config files for type: ${type}`);
  return await makeApiRequest(`/configs/${type}`, 'GET', apiKey);
};

const fetchConfigFileContent = async (type: string, filename: string, apiKey: string | null): Promise<object> => {
    console.log(`Fetching content for: ${type}/${filename}`);
    return await makeApiRequest(`/configs/${type}/${filename}`, 'GET', apiKey);
};

const uploadConfigFile = async (type: string, filename: string, content: object, apiKey: string | null): Promise<any> => {
    console.log(`Uploading: ${type}/${filename}`, content);
    // Backend expects {"content": {...}}
    const payload = { content: content };
    return await makeApiRequest(`/configs/${type}/${filename}`, 'POST', apiKey, payload);
};

const updateConfigFile = async (type: string, filename: string, content: object, apiKey: string | null): Promise<any> => {
    console.log(`Updating: ${type}/${filename}`, content);
     // Backend expects {"content": {...}}
    const payload = { content: content };
    return await makeApiRequest(`/configs/${type}/${filename}`, 'PUT', apiKey, payload);
};

const deleteConfigFile = async (type: string, filename: string, apiKey: string | null): Promise<any> => {
    console.log(`Deleting: ${type}/${filename}`);
    return await makeApiRequest(`/configs/${type}/${filename}`, 'DELETE', apiKey);
};


const ConfigTab: React.FC = () => {
  const [selectedType, setSelectedType] = useState<'agents' | 'clients' | 'workflows'>('agents');
  const [configFiles, setConfigFiles] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>(''); // Store as string for editing
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null); // Add API Key state
  const [newFilename, setNewFilename] = useState<string>(''); // For creating new files

  // Fetch config files when selectedType changes
  useEffect(() => {
    const loadFiles = async () => {
      setIsLoading(true);
      setError(null);
      setSelectedFile(null); // Reset selected file when type changes
      setFileContent(''); // Reset content
      setNewFilename(''); // Reset new filename input
      let currentApiKey = apiKey;
      if (!currentApiKey) {
          const key = prompt('Please enter your API key:');
          if (!key) {
              setError('API key is required to list config files.');
              setIsLoading(false);
              setConfigFiles([]); // Clear files if no key provided
              return;
          }
          setApiKey(key);
          currentApiKey = key;
      }

      try {
        const files = await fetchConfigFiles(selectedType, currentApiKey);
        setConfigFiles(files);
      } catch (err: any) {
        setError(`Failed to load config files: ${err.message}`);
        setConfigFiles([]); // Clear files on error
      } finally {
        setIsLoading(false);
      }
    };
    loadFiles();
  }, [selectedType, apiKey]); // Re-run if selectedType or apiKey changes

  // Fetch file content when a file is selected
  const handleFileSelect = async (filename: string) => {
    setSelectedFile(filename);
    setIsLoading(true);
    setError(null);
    setFileContent(''); // Clear previous content
    setNewFilename(''); // Clear new filename input
    let currentApiKey = apiKey;
      if (!currentApiKey) {
          const key = prompt('Please enter your API key:');
          if (!key) {
              setError('API key is required to view config files.');
              setIsLoading(false);
              return;
          }
          setApiKey(key);
          currentApiKey = key;
      }

    try {
      const content = await fetchConfigFileContent(selectedType, filename, currentApiKey);
      setFileContent(JSON.stringify(content, null, 2)); // Pretty print JSON
    } catch (err: any) {
      setError(`Failed to load file content: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle saving changes (Update existing or Create new)
  const handleSave = async () => {
      const filenameToSave = selectedFile || newFilename;
      if (!filenameToSave) {
          setError('Please select a file to update or enter a new filename to create.');
          return;
      }
      if (!filenameToSave.endsWith('.json')) {
          setError('Filename must end with .json');
          return;
      }

      let contentToSave: object;
      try {
          contentToSave = JSON.parse(fileContent);
      } catch (e) {
          setError('Invalid JSON content. Please correct before saving.');
          return;
      }

      setIsLoading(true);
      setError(null);
      let currentApiKey = apiKey;
      if (!currentApiKey) {
          const key = prompt('Please enter your API key:');
          if (!key) {
              setError('API key is required to save config files.');
              setIsLoading(false);
              return;
          }
          setApiKey(key);
          currentApiKey = key;
      }

      try {
          let result;
          if (selectedFile) { // Update existing file
              result = await updateConfigFile(selectedType, filenameToSave, contentToSave, currentApiKey);
              alert(`File updated: ${result.filename}`); // Simple feedback
          } else { // Create new file
              result = await uploadConfigFile(selectedType, filenameToSave, contentToSave, currentApiKey);
              alert(`File created: ${result.filename}`); // Simple feedback
              // Refresh file list after creation
              const files = await fetchConfigFiles(selectedType, currentApiKey);
              setConfigFiles(files);
              setSelectedFile(filenameToSave); // Select the newly created file
              setNewFilename(''); // Clear the input
          }
          console.log("Save result:", result);
      } catch (err: any) {
          setError(`Failed to save file: ${err.message}`);
      } finally {
          setIsLoading(false);
      }
  };

  // Handle deleting a file
  const handleDelete = async () => {
      if (!selectedFile) {
          setError('Please select a file to delete.');
          return;
      }
      if (!confirm(`Are you sure you want to delete ${selectedFile}?`)) {
          return;
      }

      setIsLoading(true);
      setError(null);
      let currentApiKey = apiKey;
      if (!currentApiKey) {
          const key = prompt('Please enter your API key:');
          if (!key) {
              setError('API key is required to delete config files.');
              setIsLoading(false);
              return;
          }
          setApiKey(key);
          currentApiKey = key;
      }

      try {
          const result = await deleteConfigFile(selectedType, selectedFile, currentApiKey);
          alert(`File deleted: ${result.filename}`); // Simple feedback
          // Refresh file list after deletion
          const files = await fetchConfigFiles(selectedType, currentApiKey);
          setConfigFiles(files);
          setSelectedFile(null); // Deselect file
          setFileContent(''); // Clear content
      } catch (err: any) {
          setError(`Failed to delete file: ${err.message}`);
      } finally {
          setIsLoading(false);
      }
  };

  // Handle creating a new file (clears selection and editor)
  const handleNewFile = () => {
      setSelectedFile(null);
      setFileContent('{\n  \n}'); // Basic JSON structure
      setNewFilename(''); // Clear filename input for user
      setError(null);
      // Focus the filename input (optional, requires ref)
  };


  return (
    <div className="p-4 grid grid-cols-3 gap-4">
      {/* Left Column: File List */}
      <div className="col-span-1 border-r pr-4">
        <h2 className="text-lg font-semibold mb-3">Config Files</h2>
        <div className="mb-3">
          <label htmlFor="configTypeSelect" className="block text-sm font-medium text-gray-700 mb-1">
            Component Type:
          </label>
          <select
            id="configTypeSelect"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value as 'agents' | 'clients' | 'workflows')}
            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md border"
            disabled={isLoading}
          >
            <option value="agents">Agents</option>
            <option value="clients">Clients</option>
            <option value="workflows">Workflows</option>
          </select>
        </div>

        {isLoading && <p className="text-sm text-gray-500">Loading files...</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        <ul className="space-y-1 max-h-96 overflow-y-auto">
          {configFiles.map((file) => (
            <li key={file}>
              <button
                onClick={() => handleFileSelect(file)}
                className={`w-full text-left px-3 py-1.5 text-sm rounded ${
                  selectedFile === file ? 'bg-blue-100 text-blue-700' : 'text-gray-700 hover:bg-gray-100'
                }`}
                disabled={isLoading}
              >
                {file}
              </button>
            </li>
          ))}
        </ul>
         <button
            onClick={handleNewFile}
            className="mt-4 w-full bg-green-500 hover:bg-green-600 text-white text-sm py-2 px-4 rounded disabled:opacity-50"
            disabled={isLoading}
          >
            New File
          </button>
      </div>

      {/* Right Column: Editor */}
      <div className="col-span-2">
        <h2 className="text-lg font-semibold mb-3">
          {selectedFile ? `Editing: ${selectedFile}` : 'Create New File'}
        </h2>

        {!selectedFile && (
             <div className="mb-3">
                <label htmlFor="newFilenameInput" className="block text-sm font-medium text-gray-700 mb-1">
                    New Filename (.json):
                </label>
                <input
                    type="text"
                    id="newFilenameInput"
                    value={newFilename}
                    onChange={(e) => setNewFilename(e.target.value)}
                    placeholder="e.g., my_new_agent.json"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    disabled={isLoading || !!selectedFile} // Disable if editing existing file
                />
             </div>
        )}

        <textarea
          value={fileContent}
          onChange={(e) => setFileContent(e.target.value)}
          className="w-full h-96 p-2 border rounded font-mono text-sm"
          placeholder={selectedFile || newFilename ? "Loading content or enter JSON here..." : "Select a file or click 'New File'"}
          disabled={isLoading || (!selectedFile && !newFilename)} // Disable if loading or no file selected/new name entered
        />
        <div className="mt-3 flex justify-between items-center">
          <button
            onClick={handleSave}
            className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded text-sm disabled:opacity-50"
            disabled={isLoading || (!selectedFile && !newFilename) || !fileContent}
          >
            {selectedFile ? 'Save Changes' : 'Create File'}
          </button>
          {selectedFile && ( // Only show delete for existing files
             <button
                onClick={handleDelete}
                className="bg-red-500 hover:bg-red-600 text-white py-2 px-4 rounded text-sm disabled:opacity-50"
                disabled={isLoading || !selectedFile}
             >
                Delete File
             </button>
          )}
        </div>
         {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
      </div>
    </div>
  );
};

export default ConfigTab;
