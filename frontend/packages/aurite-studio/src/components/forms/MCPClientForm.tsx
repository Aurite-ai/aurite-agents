import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useClientConfig, useUpdateClient, useCreateMCPServer, useDeleteClient } from '@/hooks/useClients';

interface MCPClientFormProps {
  editMode?: boolean;
}

export default function MCPClientForm({ editMode = false }: MCPClientFormProps) {
  const navigate = useNavigate();
  const { name: mcpNameParam } = useParams<{ name: string }>();
  
  // Enhanced MCP form state for full schema support
  const [mcpClientId, setMcpClientId] = useState('');
  const [mcpDescription, setMcpDescription] = useState('');
  const [mcpTransportType, setMcpTransportType] = useState<'stdio' | 'http_stream' | 'local'>('stdio');
  const [mcpCapabilities, setMcpCapabilities] = useState('');
  const [mcpTimeout, setMcpTimeout] = useState('');
  const [mcpRegistrationTimeout, setMcpRegistrationTimeout] = useState('');
  const [mcpRoutingWeight, setMcpRoutingWeight] = useState('');
  
  // Stdio transport fields
  const [mcpServerPath, setMcpServerPath] = useState('');
  
  // HTTP stream transport fields
  const [mcpHttpEndpoint, setMcpHttpEndpoint] = useState('');
  const [mcpHeaders, setMcpHeaders] = useState<Array<{key: string; value: string}>>([]);
  
  // Local transport fields
  const [mcpCommand, setMcpCommand] = useState('');
  const [mcpArgs, setMcpArgs] = useState<string[]>([]);
  
  // Form control state
  const [formPopulated, setFormPopulated] = useState(false);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);

  // API Hooks
  const { data: mcpClientConfig, isLoading: mcpClientConfigLoading } = useClientConfig(
    mcpNameParam || '',
    !!mcpNameParam && editMode
  );
  
  const updateMCPClient = useUpdateClient();
  const createMCPServer = useCreateMCPServer();
  const deleteMCPClient = useDeleteClient();

  // Effect to populate MCP form when MCP client config is loaded
  useEffect(() => {
    if (editMode && mcpClientConfig && mcpNameParam && !formPopulated) {
      console.log('🔄 Populating MCP form with config:', mcpClientConfig);
      
      // Access the nested config object - API returns { config: { ... }, name: ..., ... }
      const config = (mcpClientConfig as any).config || mcpClientConfig;
      console.log('📋 Config object to use:', config);
      
      // Try different possible field names based on the API response structure
      const name = config.name || (mcpClientConfig as any).name;
      const description = config.description;
      const transportType = config.transport_type;
      const capabilities = config.capabilities;
      const timeout = config.timeout;
      const serverPath = config.server_path;
      const httpEndpoint = config.http_endpoint;
      const command = config.command;
      const args = config.args;
      const headers = config.headers;
      const registrationTimeout = config.registration_timeout;
      const routingWeight = config.routing_weight;
      
      setMcpClientId(name || '');
      setMcpDescription(description || '');
      setMcpTransportType(transportType || 'stdio');
      setMcpCapabilities(Array.isArray(capabilities) ? capabilities.join(', ') : (capabilities || ''));
      setMcpTimeout(timeout?.toString() || '');
      setMcpRegistrationTimeout(registrationTimeout?.toString() || '');
      setMcpRoutingWeight(routingWeight?.toString() || '');
      
      // Transport-specific fields
      setMcpServerPath(serverPath || '');
      setMcpHttpEndpoint(httpEndpoint || '');
      setMcpHeaders(headers ? Object.entries(headers).map(([key, value]) => ({ key, value: String(value) })) : []);
      setMcpCommand(command || '');
      setMcpArgs(Array.isArray(args) ? args : []);
      
      // Mark form as populated to prevent re-population
      setFormPopulated(true);
      console.log('✅ MCP form populated successfully');
    } else if (editMode && mcpNameParam && !mcpClientConfig && !mcpClientConfigLoading) {
      console.log('❌ Failed to load MCP client config for:', mcpNameParam);
    }
  }, [mcpClientConfig, mcpNameParam, editMode, mcpClientConfigLoading, formPopulated]);

  // Initialize form for create mode
  useEffect(() => {
    if (!editMode && !formPopulated) {
      // Reset ALL form fields to empty/default values for new MCP client creation
      setMcpClientId('');
      setMcpDescription('');
      setMcpTransportType('stdio');
      setMcpCapabilities('');
      setMcpTimeout('');
      setMcpRegistrationTimeout('');
      setMcpRoutingWeight('');
      setMcpServerPath('');
      setMcpHttpEndpoint('');
      setMcpHeaders([]);
      setMcpCommand('');
      setMcpArgs([]);
      
      // Mark form as populated to prevent re-initialization
      setFormPopulated(true);
    }
  }, [editMode, formPopulated]);

  const handleSubmit = () => {
    // Build the complete MCP server configuration
    const validCapabilities = mcpCapabilities
      .split(',')
      .map(c => c.trim())
      .filter(c => c && ['tools', 'prompts', 'resources'].includes(c));

    const mcpServerConfig: any = {
      name: mcpClientId,
      type: "mcp_server",
      capabilities: validCapabilities,
      transport_type: mcpTransportType,
    };

    // Add optional fields
    if (mcpDescription) mcpServerConfig.description = mcpDescription;
    if (mcpTimeout) mcpServerConfig.timeout = parseFloat(mcpTimeout);
    if (mcpRegistrationTimeout) mcpServerConfig.registration_timeout = parseFloat(mcpRegistrationTimeout);
    if (mcpRoutingWeight) mcpServerConfig.routing_weight = parseFloat(mcpRoutingWeight);

    // Add transport-specific fields
    if (mcpTransportType === 'stdio' && mcpServerPath) {
      mcpServerConfig.server_path = mcpServerPath;
    } else if (mcpTransportType === 'http_stream' && mcpHttpEndpoint) {
      mcpServerConfig.http_endpoint = mcpHttpEndpoint;
      if (mcpHeaders.length > 0) {
        const headersObj: Record<string, string> = {};
        mcpHeaders.forEach(header => {
          if (header.key && header.value) {
            headersObj[header.key] = header.value;
          }
        });
        if (Object.keys(headersObj).length > 0) {
          mcpServerConfig.headers = headersObj;
        }
      }
    } else if (mcpTransportType === 'local' && mcpCommand) {
      mcpServerConfig.command = mcpCommand;
      if (mcpArgs.length > 0 && mcpArgs.some(arg => arg.trim())) {
        mcpServerConfig.args = mcpArgs.filter(arg => arg.trim());
      }
    }

    console.log('💾 Saving MCP server config:', mcpServerConfig);

    if (editMode && mcpNameParam) {
      // Edit mode - update existing MCP server
      updateMCPClient.mutate({
        filename: mcpNameParam,
        config: mcpServerConfig
      }, {
        onSuccess: () => {
          console.log('✅ MCP server updated successfully');
          navigate('/mcp-clients');
        },
        onError: (error) => {
          console.error('❌ Failed to update MCP server:', error);
        }
      });
    } else {
      // Create mode - create new MCP server
      createMCPServer.mutate({
        name: mcpClientId,
        config: mcpServerConfig
      }, {
        onSuccess: () => {
          console.log('✅ New MCP server created successfully');
          navigate('/mcp-clients');
        },
        onError: (error) => {
          console.error('❌ Failed to create MCP server:', error);
        }
      });
    }
  };

  const handleDelete = () => {
    setShowDeleteConfirmation(true);
  };

  const confirmDelete = () => {
    if (mcpNameParam) {
      deleteMCPClient.mutate(mcpNameParam, {
        onSuccess: () => {
          setShowDeleteConfirmation(false);
          navigate('/mcp-clients');
        }
      });
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Main Content */}
      <div className="flex-1 flex flex-col relative">
        {/* Main Content Area */}
        <main className="flex-1 flex flex-col px-6 pt-12 pb-8">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="w-full max-w-4xl mx-auto space-y-8"
          >
            {/* Header */}
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate('/mcp-clients')}
                className="w-9 h-9"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <h1 className="text-3xl font-bold text-primary">
                {editMode ? 'Edit MCP Server' : 'Build New MCP Server'}
              </h1>
            </div>

            {/* Basic Configuration Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              <h2 className="text-lg font-semibold text-primary">Basic Configuration</h2>
              
              {/* Loading State for MCP Config */}
              {mcpClientConfigLoading && editMode && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading MCP server configuration...
                </div>
              )}
              
              {/* Server Name */}
              <div className="space-y-2">
                <Label htmlFor="server-name" className="text-sm font-medium text-foreground">Server Name *</Label>
                <Input
                  id="server-name"
                  placeholder="e.g., weather_server"
                  value={mcpClientId}
                  onChange={(e) => setMcpClientId(e.target.value)}
                  className="text-base"
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description" className="text-sm font-medium text-foreground">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Brief description of what this server provides"
                  value={mcpDescription}
                  onChange={(e) => setMcpDescription(e.target.value)}
                  className="min-h-[80px] resize-none"
                />
              </div>

              {/* Capabilities */}
              <div className="space-y-2">
                <Label htmlFor="capabilities" className="text-sm font-medium text-foreground">Capabilities *</Label>
                <Input
                  id="capabilities"
                  placeholder="tools, prompts, resources (comma-separated)"
                  value={mcpCapabilities}
                  onChange={(e) => setMcpCapabilities(e.target.value)}
                  className="text-base"
                />
                <p className="text-xs text-muted-foreground">Valid options: tools, prompts, resources</p>
              </div>
            </motion.div>

            {/* Transport Configuration Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              <h2 className="text-lg font-semibold text-primary">Transport Configuration</h2>
              
              {/* Transport Type */}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">Transport Type *</Label>
                <Select value={mcpTransportType} onValueChange={(value: 'stdio' | 'http_stream' | 'local') => setMcpTransportType(value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select transport type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="stdio">Stdio (Python script)</SelectItem>
                    <SelectItem value="http_stream">HTTP Stream (Web endpoint)</SelectItem>
                    <SelectItem value="local">Local (Command execution)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Stdio Transport Fields */}
              {mcpTransportType === 'stdio' && (
                <div className="space-y-4 p-4 bg-muted/20 rounded-lg">
                  <h3 className="text-sm font-medium text-foreground">Stdio Configuration</h3>
                  <div className="space-y-2">
                    <Label htmlFor="server-path" className="text-sm font-medium text-foreground">Server Path *</Label>
                    <Input
                      id="server-path"
                      placeholder="e.g., src/packaged_servers/weather_server.py"
                      value={mcpServerPath}
                      onChange={(e) => setMcpServerPath(e.target.value)}
                      className="text-base"
                    />
                  </div>
                </div>
              )}

              {/* HTTP Stream Transport Fields */}
              {mcpTransportType === 'http_stream' && (
                <div className="space-y-4 p-4 bg-muted/20 rounded-lg">
                  <h3 className="text-sm font-medium text-foreground">HTTP Stream Configuration</h3>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="http-endpoint" className="text-sm font-medium text-foreground">HTTP Endpoint *</Label>
                      <Input
                        id="http-endpoint"
                        placeholder="e.g., https://api.example.com/mcp"
                        value={mcpHttpEndpoint}
                        onChange={(e) => setMcpHttpEndpoint(e.target.value)}
                        className="text-base"
                        type="url"
                      />
                    </div>
                    
                    {/* Headers */}
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-foreground">Headers</Label>
                      {mcpHeaders.map((header, index) => (
                        <div key={index} className="flex gap-2">
                          <Input
                            placeholder="Header name"
                            value={header.key}
                            onChange={(e) => {
                              const newHeaders = [...mcpHeaders];
                              newHeaders[index] = { ...header, key: e.target.value };
                              setMcpHeaders(newHeaders);
                            }}
                            className="flex-1"
                          />
                          <Input
                            placeholder="Header value"
                            value={header.value}
                            onChange={(e) => {
                              const newHeaders = [...mcpHeaders];
                              newHeaders[index] = { ...header, value: e.target.value };
                              setMcpHeaders(newHeaders);
                            }}
                            className="flex-1"
                          />
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const newHeaders = mcpHeaders.filter((_, i) => i !== index);
                              setMcpHeaders(newHeaders);
                            }}
                          >
                            Remove
                          </Button>
                        </div>
                      ))}
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setMcpHeaders([...mcpHeaders, { key: '', value: '' }]);
                        }}
                      >
                        Add Header
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {/* Local Transport Fields */}
              {mcpTransportType === 'local' && (
                <div className="space-y-4 p-4 bg-muted/20 rounded-lg">
                  <h3 className="text-sm font-medium text-foreground">Local Command Configuration</h3>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="command" className="text-sm font-medium text-foreground">Command *</Label>
                      <Input
                        id="command"
                        placeholder="e.g., ./my-server"
                        value={mcpCommand}
                        onChange={(e) => setMcpCommand(e.target.value)}
                        className="text-base"
                      />
                    </div>
                    
                    {/* Arguments */}
                    <div className="space-y-2">
                      <Label className="text-sm font-medium text-foreground">Arguments</Label>
                      {mcpArgs.map((arg, index) => (
                        <div key={index} className="flex gap-2">
                          <Input
                            placeholder="Argument"
                            value={arg}
                            onChange={(e) => {
                              const newArgs = [...mcpArgs];
                              newArgs[index] = e.target.value;
                              setMcpArgs(newArgs);
                            }}
                            className="flex-1"
                          />
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const newArgs = mcpArgs.filter((_, i) => i !== index);
                              setMcpArgs(newArgs);
                            }}
                          >
                            Remove
                          </Button>
                        </div>
                      ))}
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setMcpArgs([...mcpArgs, '']);
                        }}
                      >
                        Add Argument
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>

            {/* Advanced Settings Card */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="bg-card border border-border rounded-lg p-6 space-y-6"
            >
              <h2 className="text-lg font-semibold text-primary">Advanced Settings</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Timeout */}
                <div className="space-y-2">
                  <Label htmlFor="timeout" className="text-sm font-medium text-foreground">Timeout (seconds)</Label>
                  <Input
                    id="timeout"
                    placeholder="10.0"
                    value={mcpTimeout}
                    onChange={(e) => setMcpTimeout(e.target.value)}
                    className="text-base"
                    type="number"
                    step="0.1"
                  />
                </div>

                {/* Registration Timeout */}
                <div className="space-y-2">
                  <Label htmlFor="registration-timeout" className="text-sm font-medium text-foreground">Registration Timeout (seconds)</Label>
                  <Input
                    id="registration-timeout"
                    placeholder="30.0"
                    value={mcpRegistrationTimeout}
                    onChange={(e) => setMcpRegistrationTimeout(e.target.value)}
                    className="text-base"
                    type="number"
                    step="0.1"
                  />
                </div>

                {/* Routing Weight */}
                <div className="space-y-2">
                  <Label htmlFor="routing-weight" className="text-sm font-medium text-foreground">Routing Weight</Label>
                  <Input
                    id="routing-weight"
                    placeholder="1.0"
                    value={mcpRoutingWeight}
                    onChange={(e) => setMcpRoutingWeight(e.target.value)}
                    className="text-base"
                    type="number"
                    step="0.1"
                  />
                </div>
              </div>
            </motion.div>

            {/* Action Buttons */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="flex justify-between"
            >
              {/* Delete Button - Only show in edit mode */}
              {editMode && (
                <Button 
                  variant="destructive"
                  className="px-6"
                  onClick={handleDelete}
                  disabled={deleteMCPClient.isPending}
                >
                  {deleteMCPClient.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Deleting...
                    </>
                  ) : (
                    'Delete MCP Server'
                  )}
                </Button>
              )}
              
              {/* Spacer for alignment when no delete button */}
              {!editMode && <div />}
              
              <Button 
                className="px-8"
                onClick={handleSubmit}
                disabled={(updateMCPClient.isPending || createMCPServer.isPending) || !mcpClientId || !mcpCapabilities || 
                  (mcpTransportType === 'stdio' && !mcpServerPath) ||
                  (mcpTransportType === 'http_stream' && !mcpHttpEndpoint) ||
                  (mcpTransportType === 'local' && !mcpCommand)
                }
              >
                {(updateMCPClient.isPending || createMCPServer.isPending) ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    {editMode ? 'Updating...' : 'Creating...'}
                  </>
                ) : (
                  editMode ? 'Update MCP Server' : 'Save MCP Server'
                )}
              </Button>
            </motion.div>
          </motion.div>
        </main>
      </div>

      {/* Delete Confirmation Dialog */}
      <AnimatePresence>
        {showDeleteConfirmation && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowDeleteConfirmation(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border rounded-lg p-6 max-w-md mx-4 space-y-4"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-foreground">
                Delete MCP Server
              </h3>
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete the MCP server "{mcpClientId}"? This action cannot be undone.
              </p>
              <div className="flex gap-3 justify-end">
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteConfirmation(false)}
                  disabled={deleteMCPClient.isPending}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={confirmDelete}
                  disabled={deleteMCPClient.isPending}
                >
                  {deleteMCPClient.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Deleting...
                    </>
                  ) : (
                    'Delete'
                  )}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
