import React, { useState, useEffect } from 'react';
import { 
  MCPServerConfig, 
  MCPServerFormFields,
  RootConfig 
} from '../types';
import mcpServersService from '../services/mcpServers.service';

interface MCPServerManagerProps {
  className?: string;
}

const MCPServerManager: React.FC<MCPServerManagerProps> = ({ className }) => {
  const [servers, setServers] = useState<string[]>([]);
  const [activeServers, setActiveServers] = useState<string[]>([]);
  const [selectedServer, setSelectedServer] = useState<MCPServerConfig | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [formData, setFormData] = useState<MCPServerFormFields>(mcpServersService.getDefaultForm());
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load servers on component mount
  useEffect(() => {
    loadServers();
    loadActiveServers();
  }, []);

  const loadServers = async () => {
    try {
      setLoading(true);
      const serverList = await mcpServersService.listMCPServers();
      setServers(serverList);
    } catch (err) {
      setError('Failed to load MCP servers');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadActiveServers = async () => {
    try {
      const activeList = await mcpServersService.listActiveMCPServers();
      setActiveServers(activeList);
    } catch (err) {
      console.error('Failed to load active servers:', err);
    }
  };

  const handleSelectServer = async (serverName: string) => {
    try {
      setLoading(true);
      const config = await mcpServersService.getMCPServer(serverName);
      setSelectedServer(config);
      setFormData(mcpServersService.configToForm(config));
      setIsEditing(false);
      setIsCreating(false);
    } catch (err) {
      setError(`Failed to load server ${serverName}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNew = () => {
    setSelectedServer(null);
    setFormData(mcpServersService.getDefaultForm());
    setFormErrors({});
    setIsCreating(true);
    setIsEditing(false);
  };

  const handleEdit = () => {
    if (selectedServer) {
      setFormData(mcpServersService.configToForm(selectedServer));
      setFormErrors({});
      setIsEditing(true);
      setIsCreating(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setIsCreating(false);
    setFormErrors({});
    if (selectedServer) {
      setFormData(mcpServersService.configToForm(selectedServer));
    }
  };

  const handleFormChange = (field: keyof MCPServerFormFields, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error for this field
    if (formErrors[field]) {
      setFormErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate form
    const errors = mcpServersService.validateForm(formData);
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    try {
      setLoading(true);
      const config = mcpServersService.formToConfig(formData);

      if (isCreating) {
        await mcpServersService.createMCPServerWithValidation(config.name, config);
        await loadServers();
        setIsCreating(false);
      } else if (isEditing && selectedServer) {
        await mcpServersService.updateMCPServerWithValidation(selectedServer.name, config);
        setSelectedServer(config);
        setIsEditing(false);
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (serverName: string) => {
    if (!confirm(`Are you sure you want to delete server "${serverName}"?`)) {
      return;
    }

    try {
      setLoading(true);
      await mcpServersService.deleteMCPServer(serverName);
      await loadServers();
      if (selectedServer?.name === serverName) {
        setSelectedServer(null);
      }
      setError(null);
    } catch (err) {
      setError(`Failed to delete server ${serverName}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (serverName: string) => {
    try {
      setLoading(true);
      await mcpServersService.registerMCPServer(serverName);
      await loadActiveServers();
      setError(null);
    } catch (err) {
      setError(`Failed to register server ${serverName}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUnregister = async (serverName: string) => {
    try {
      setLoading(true);
      await mcpServersService.unregisterMCPServer(serverName);
      await loadActiveServers();
      setError(null);
    } catch (err) {
      setError(`Failed to unregister server ${serverName}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const renderTransportFields = () => {
    switch (formData.transport_type) {
      case 'stdio':
        return (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Server Path</label>
            <input
              type="text"
              value={formData.server_path}
              onChange={(e) => handleFormChange('server_path', e.target.value)}
              className="w-full p-2 border rounded"
              placeholder="path/to/server.py"
            />
            {formErrors.server_path && (
              <p className="text-red-500 text-sm mt-1">{formErrors.server_path}</p>
            )}
          </div>
        );

      case 'http_stream':
        return (
          <>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">HTTP Endpoint</label>
              <input
                type="url"
                value={formData.http_endpoint}
                onChange={(e) => handleFormChange('http_endpoint', e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="https://api.example.com/mcp"
              />
              {formErrors.http_endpoint && (
                <p className="text-red-500 text-sm mt-1">{formErrors.http_endpoint}</p>
              )}
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Headers</label>
              {formData.headers.map((header, index) => (
                <div key={index} className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={header.key}
                    onChange={(e) => {
                      const newHeaders = [...formData.headers];
                      newHeaders[index] = { ...header, key: e.target.value };
                      handleFormChange('headers', newHeaders);
                    }}
                    className="flex-1 p-2 border rounded"
                    placeholder="Header name"
                  />
                  <input
                    type="text"
                    value={header.value}
                    onChange={(e) => {
                      const newHeaders = [...formData.headers];
                      newHeaders[index] = { ...header, value: e.target.value };
                      handleFormChange('headers', newHeaders);
                    }}
                    className="flex-1 p-2 border rounded"
                    placeholder="Header value"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const newHeaders = formData.headers.filter((_, i) => i !== index);
                      handleFormChange('headers', newHeaders);
                    }}
                    className="px-3 py-2 bg-red-500 text-white rounded"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => {
                  const newHeaders = [...formData.headers, { key: '', value: '' }];
                  handleFormChange('headers', newHeaders);
                }}
                className="px-3 py-2 bg-blue-500 text-white rounded"
              >
                Add Header
              </button>
            </div>
          </>
        );

      case 'local':
        return (
          <>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Command</label>
              <input
                type="text"
                value={formData.command}
                onChange={(e) => handleFormChange('command', e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="./my-server"
              />
              {formErrors.command && (
                <p className="text-red-500 text-sm mt-1">{formErrors.command}</p>
              )}
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Arguments</label>
              {formData.args.map((arg, index) => (
                <div key={index} className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={arg}
                    onChange={(e) => {
                      const newArgs = [...formData.args];
                      newArgs[index] = e.target.value;
                      handleFormChange('args', newArgs);
                    }}
                    className="flex-1 p-2 border rounded"
                    placeholder="Argument"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const newArgs = formData.args.filter((_, i) => i !== index);
                      handleFormChange('args', newArgs);
                    }}
                    className="px-3 py-2 bg-red-500 text-white rounded"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => {
                  const newArgs = [...formData.args, ''];
                  handleFormChange('args', newArgs);
                }}
                className="px-3 py-2 bg-blue-500 text-white rounded"
              >
                Add Argument
              </button>
            </div>
          </>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`mcp-server-manager ${className || ''}`}>
      <div className="flex h-full">
        {/* Server List */}
        <div className="w-1/3 border-r p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">MCP Servers</h2>
            <button
              onClick={handleCreateNew}
              className="px-3 py-1 bg-green-500 text-white rounded text-sm"
              disabled={loading}
            >
              Create New
            </button>
          </div>

          {error && (
            <div className="mb-4 p-2 bg-red-100 border border-red-400 text-red-700 rounded">
              {error}
            </div>
          )}

          {loading && <div className="text-center py-4">Loading...</div>}

          <div className="space-y-2">
            {servers.map(serverName => (
              <div
                key={serverName}
                className={`p-3 border rounded cursor-pointer hover:bg-gray-50 ${
                  selectedServer?.name === serverName ? 'bg-blue-50 border-blue-300' : ''
                }`}
                onClick={() => handleSelectServer(serverName)}
              >
                <div className="flex justify-between items-center">
                  <span className="font-medium">{serverName}</span>
                  <div className="flex gap-1">
                    {activeServers.includes(serverName) ? (
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded">
                        Inactive
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Server Details/Form */}
        <div className="flex-1 p-4">
          {(isCreating || isEditing) ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">
                  {isCreating ? 'Create MCP Server' : 'Edit MCP Server'}
                </h3>
                <div className="space-x-2">
                  <button
                    type="button"
                    onClick={handleCancel}
                    className="px-3 py-1 bg-gray-500 text-white rounded"
                    disabled={loading}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-3 py-1 bg-blue-500 text-white rounded"
                    disabled={loading}
                  >
                    {loading ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>

              {/* Basic Fields */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleFormChange('name', e.target.value)}
                  className="w-full p-2 border rounded"
                  disabled={isEditing} // Can't change name when editing
                />
                {formErrors.name && (
                  <p className="text-red-500 text-sm mt-1">{formErrors.name}</p>
                )}
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => handleFormChange('description', e.target.value)}
                  className="w-full p-2 border rounded"
                  rows={2}
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Transport Type</label>
                <select
                  value={formData.transport_type}
                  onChange={(e) => handleFormChange('transport_type', e.target.value)}
                  className="w-full p-2 border rounded"
                >
                  <option value="stdio">Stdio</option>
                  <option value="http_stream">HTTP Stream</option>
                  <option value="local">Local Command</option>
                </select>
              </div>

              {/* Transport-specific fields */}
              {renderTransportFields()}

              {/* Capabilities */}
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Capabilities</label>
                <div className="space-y-2">
                  {['tools', 'prompts', 'resources'].map(capability => (
                    <label key={capability} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.capabilities.includes(capability)}
                        onChange={(e) => {
                          const newCapabilities = e.target.checked
                            ? [...formData.capabilities, capability]
                            : formData.capabilities.filter(c => c !== capability);
                          handleFormChange('capabilities', newCapabilities);
                        }}
                        className="mr-2"
                      />
                      {capability}
                    </label>
                  ))}
                </div>
                {formErrors.capabilities && (
                  <p className="text-red-500 text-sm mt-1">{formErrors.capabilities}</p>
                )}
              </div>

              {/* Advanced Settings */}
              <details className="mb-4">
                <summary className="cursor-pointer font-medium">Advanced Settings</summary>
                <div className="mt-4 space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Timeout (seconds)</label>
                    <input
                      type="number"
                      value={formData.timeout}
                      onChange={(e) => handleFormChange('timeout', parseFloat(e.target.value))}
                      className="w-full p-2 border rounded"
                      min="0.1"
                      step="0.1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Registration Timeout (seconds)</label>
                    <input
                      type="number"
                      value={formData.registration_timeout}
                      onChange={(e) => handleFormChange('registration_timeout', parseFloat(e.target.value))}
                      className="w-full p-2 border rounded"
                      min="0.1"
                      step="0.1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Routing Weight</label>
                    <input
                      type="number"
                      value={formData.routing_weight}
                      onChange={(e) => handleFormChange('routing_weight', parseFloat(e.target.value))}
                      className="w-full p-2 border rounded"
                      min="0.1"
                      step="0.1"
                    />
                  </div>
                </div>
              </details>
            </form>
          ) : selectedServer ? (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">{selectedServer.name}</h3>
                <div className="space-x-2">
                  {activeServers.includes(selectedServer.name) ? (
                    <button
                      onClick={() => handleUnregister(selectedServer.name)}
                      className="px-3 py-1 bg-orange-500 text-white rounded"
                      disabled={loading}
                    >
                      Unregister
                    </button>
                  ) : (
                    <button
                      onClick={() => handleRegister(selectedServer.name)}
                      className="px-3 py-1 bg-green-500 text-white rounded"
                      disabled={loading}
                    >
                      Register
                    </button>
                  )}
                  <button
                    onClick={handleEdit}
                    className="px-3 py-1 bg-blue-500 text-white rounded"
                    disabled={loading}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(selectedServer.name)}
                    className="px-3 py-1 bg-red-500 text-white rounded"
                    disabled={loading}
                  >
                    Delete
                  </button>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <strong>Description:</strong> {selectedServer.description || 'No description'}
                </div>
                <div>
                  <strong>Transport Type:</strong> {selectedServer.transport_type || 'Not specified'}
                </div>
                <div>
                  <strong>Capabilities:</strong> {selectedServer.capabilities.join(', ')}
                </div>
                {selectedServer.server_path && (
                  <div>
                    <strong>Server Path:</strong> {selectedServer.server_path}
                  </div>
                )}
                {selectedServer.http_endpoint && (
                  <div>
                    <strong>HTTP Endpoint:</strong> {selectedServer.http_endpoint}
                  </div>
                )}
                {selectedServer.command && (
                  <div>
                    <strong>Command:</strong> {selectedServer.command}
                  </div>
                )}
                <div>
                  <strong>Timeout:</strong> {selectedServer.timeout || 10.0}s
                </div>
                <div>
                  <strong>Registration Timeout:</strong> {selectedServer.registration_timeout || 30.0}s
                </div>
                <div>
                  <strong>Routing Weight:</strong> {selectedServer.routing_weight || 1.0}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-500 py-8">
              Select a server to view details or create a new one
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MCPServerManager;
