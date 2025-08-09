import {
  MCPServerConfig,
  MCPServerStdioConfig,
  MCPServerHttpConfig,
  MCPServerLocalConfig,
  MCPServerFormFields,
} from '../types';

// Type guards for transport validation
export function isStdioConfig(config: MCPServerConfig): config is MCPServerStdioConfig {
  return config.transport_type === 'stdio' && !!config.server_path;
}

export function isHttpConfig(config: MCPServerConfig): config is MCPServerHttpConfig {
  return config.transport_type === 'http_stream' && !!config.http_endpoint;
}

export function isLocalConfig(config: MCPServerConfig): config is MCPServerLocalConfig {
  return config.transport_type === 'local' && !!config.command;
}

// Validation function
export function validateMCPServerConfig(config: MCPServerConfig): string[] {
  const errors: string[] = [];

  // Required fields
  if (!config.name) {
    errors.push('Name is required');
  }
  if (!config.capabilities || config.capabilities.length === 0) {
    errors.push('At least one capability is required');
  }

  // Transport-specific validation
  if (config.transport_type === 'stdio') {
    if (!config.server_path) {
      errors.push('server_path is required for stdio transport');
    }
    if (config.http_endpoint) {
      errors.push('http_endpoint not allowed for stdio transport');
    }
    if (config.command) {
      errors.push('command not allowed for stdio transport');
    }
  } else if (config.transport_type === 'http_stream') {
    if (!config.http_endpoint) {
      errors.push('http_endpoint is required for http_stream transport');
    }
    if (config.server_path) {
      errors.push('server_path not allowed for http_stream transport');
    }
    if (config.command) {
      errors.push('command not allowed for http_stream transport');
    }
  } else if (config.transport_type === 'local') {
    if (!config.command) {
      errors.push('command is required for local transport');
    }
    if (config.server_path) {
      errors.push('server_path not allowed for local transport');
    }
    if (config.http_endpoint) {
      errors.push('http_endpoint not allowed for local transport');
    }
  }

  // Numeric validations
  if (config.timeout !== undefined && config.timeout <= 0) {
    errors.push('timeout must be positive');
  }
  if (config.registration_timeout !== undefined && config.registration_timeout <= 0) {
    errors.push('registration_timeout must be positive');
  }
  if (config.routing_weight !== undefined && config.routing_weight <= 0) {
    errors.push('routing_weight must be positive');
  }

  return errors;
}

// Convert form data to API format
export function formToMCPServerConfig(form: MCPServerFormFields): MCPServerConfig {
  const base: MCPServerConfig = {
    name: form.name,
    type: 'mcp_server',
    capabilities: form.capabilities,
    description: form.description || undefined,
    transport_type: form.transport_type,
    timeout: form.timeout || undefined,
    registration_timeout: form.registration_timeout || undefined,
    routing_weight: form.routing_weight || undefined,
    exclude: form.exclude.length > 0 ? form.exclude : undefined,
  };

  // Add transport-specific fields
  if (form.transport_type === 'stdio') {
    return { ...base, server_path: form.server_path };
  } else if (form.transport_type === 'http_stream') {
    const headers = form.headers.reduce(
      (acc, { key, value }) => {
        if (key && value) {
          acc[key] = value;
        }
        return acc;
      },
      {} as Record<string, string>
    );

    return {
      ...base,
      http_endpoint: form.http_endpoint,
      headers: Object.keys(headers).length > 0 ? headers : undefined,
    };
  } else if (form.transport_type === 'local') {
    return {
      ...base,
      command: form.command,
      args: form.args.length > 0 ? form.args : undefined,
    };
  }

  return base;
}

// Convert API config to form data
export function mcpServerConfigToForm(config: MCPServerConfig): MCPServerFormFields {
  return {
    name: config.name,
    description: config.description || '',
    capabilities: config.capabilities,
    transport_type: config.transport_type || 'stdio',
    server_path: config.server_path || '',
    http_endpoint: config.http_endpoint || '',
    headers: config.headers
      ? Object.entries(config.headers).map(([key, value]) => ({ key, value }))
      : [],
    command: config.command || '',
    args: config.args || [],
    timeout: config.timeout || 10.0,
    registration_timeout: config.registration_timeout || 30.0,
    routing_weight: config.routing_weight || 1.0,
    exclude: config.exclude || [],
  };
}

// Migration helper for existing configurations
export function migrateClientConfig(oldConfig: any): MCPServerConfig {
  return {
    name: oldConfig.name,
    type: 'mcp_server',
    capabilities: oldConfig.capabilities || ['tools'],
    description: undefined,
    transport_type: oldConfig.server_path ? 'stdio' : undefined,
    server_path: oldConfig.server_path,
    timeout: oldConfig.timeout,
    registration_timeout: 30.0, // Default value
    routing_weight: oldConfig.routing_weight,
    exclude: oldConfig.exclude,
    roots: oldConfig.roots?.map((root: any) => ({
      uri: root.uri || root,
      name: root.name || root,
      capabilities: root.capabilities || ['tools'],
    })),
  };
}

// Get default form values for new MCP server
export function getDefaultMCPServerForm(): MCPServerFormFields {
  return {
    name: '',
    description: '',
    capabilities: ['tools'],
    transport_type: 'stdio',
    server_path: '',
    http_endpoint: '',
    headers: [],
    command: '',
    args: [],
    timeout: 10.0,
    registration_timeout: 30.0,
    routing_weight: 1.0,
    exclude: [],
  };
}

// Validate form fields
export function validateMCPServerForm(form: MCPServerFormFields): Record<string, string> {
  const errors: Record<string, string> = {};

  // Basic validation
  if (!form.name.trim()) {
    errors.name = 'Name is required';
  }

  if (form.capabilities.length === 0) {
    errors.capabilities = 'At least one capability is required';
  }

  // Transport-specific validation
  if (form.transport_type === 'stdio' && !form.server_path.trim()) {
    errors.server_path = 'Server path is required for stdio transport';
  }

  if (form.transport_type === 'http_stream' && !form.http_endpoint.trim()) {
    errors.http_endpoint = 'HTTP endpoint is required for http_stream transport';
  }

  if (form.transport_type === 'local' && !form.command.trim()) {
    errors.command = 'Command is required for local transport';
  }

  // Numeric validation
  if (form.timeout <= 0) {
    errors.timeout = 'Timeout must be positive';
  }

  if (form.registration_timeout <= 0) {
    errors.registration_timeout = 'Registration timeout must be positive';
  }

  if (form.routing_weight <= 0) {
    errors.routing_weight = 'Routing weight must be positive';
  }

  return errors;
}
