# ✨ Aurite Framework Frontend

A comprehensive TypeScript/JavaScript frontend ecosystem for the Aurite Framework, providing both a production-ready API client and a modern web interface for building and managing AI agents, workflows, and configurations.

## Overview

This frontend workspace contains TypeScript packages and tools for developers building applications with the Aurite Framework. It includes both programmatic access through the API client and a visual interface through Aurite Studio.

### Packages

- **[@aurite/api-client](packages/api-client/)** - Production-ready TypeScript client for the Aurite API
- **[@aurite/aurite-studio](packages/aurite-studio/)** - Modern React web interface for managing agents and workflows

## Architecture

```
frontend/
├── packages/
│   ├── api-client/          # TypeScript API client package
│   └── aurite-studio/       # React web application
├── .env.example             # Environment configuration template
├── package.json             # Workspace configuration
└── tsconfig.json           # TypeScript project references
```

## Quick Start

### Prerequisites

- Node.js >= 18.0.0
- npm >= 8.0.0
- Running Aurite Framework API server

### Installation

```bash
# Clone the repository
git clone https://github.com/aurite-ai/aurite-agents.git
cd aurite-agents/frontend

# Install dependencies for all packages
npm install

# Build all packages (required before starting development)
npm run build

# Set up environment variables for the workspace
cp .env.example .env
# Edit .env with your API configuration

# Set up environment variables for Aurite Studio
cp packages/aurite-studio/.env.example packages/aurite-studio/.env
# Edit packages/aurite-studio/.env with your React app configuration
```

### Environment Configuration

Create a `.env` file in the frontend root:

```bash
# API Configuration
API_KEY=your_api_key_here
AURITE_API_URL=http://localhost:8000

# React App Configuration (for Aurite Studio)
REACT_APP_API_URL=http://localhost:8000
REACT_APP_API_KEY=your_api_key_here

# Environment
NODE_ENV=development
```

Create a `.env` file in the aurite-studio package directory:

```bash
# packages/aurite-studio/.env
# API Server URL - where the Aurite API server is running
REACT_APP_API_BASE_URL=http://localhost:8000

# API Key for authentication with the Aurite API server
REACT_APP_API_KEY=your-key-here
```

### Quick Start Options

#### Option 1: Use Aurite Studio (Web Interface)

```bash
# Option A: Start from frontend root (recommended)
npm start

# Option B: Start from package directory
cd packages/aurite-studio
npm start

# Open browser to http://localhost:3000
```

#### Option 2: Use API Client (Programmatic)

```bash
# Run API client examples
npm run example --workspace=packages/api-client

# Or build and use in your project
npm run build:api-client
```

## Packages

### @aurite/aurite-studio

A modern, intuitive React web application for managing and executing AI agents, workflows, and configurations in the Aurite Framework.

**Key Features:**

- 🤖 **Agent Management**: Create, configure, and execute AI agents with real-time streaming
- 🔄 **Workflow Design**: Build linear sequential workflows and custom Python workflows
- 🔧 **MCP Server Configuration**: Manage Model Context Protocol servers and tools
- ⚙️ **LLM Configuration**: Configure multiple language model providers
- 🎨 **Modern Interface**: Clean, responsive design with dark/light themes
- 📱 **Mobile-Friendly**: Responsive layout that works on all devices

**Technology Stack:**

- React 19 with TypeScript
- Tailwind CSS with custom design system
- Framer Motion for animations
- Radix UI components
- TanStack Query for state management

**Quick Usage:**

```bash
cd packages/aurite-studio
npm start
# Navigate to http://localhost:3000
```

### @aurite/api-client

A production-ready TypeScript client for the Aurite Framework API with comprehensive error handling, retry logic, and full type safety.

**Key Features:**

- 🔒 **Type Safety**: Full TypeScript support with comprehensive type definitions
- 🔄 **Retry Logic**: Intelligent retry mechanisms for network failures
- 🛡️ **Error Handling**: Comprehensive error categorization and handling
- 📊 **Streaming Support**: Real-time streaming for agent responses
- 🧪 **Testing**: Extensive unit and integration test coverage
- 📖 **Examples**: Comprehensive examples for all API endpoints

**Quick Usage:**

```typescript
import { createAuriteClient } from '@aurite/api-client';

const client = createAuriteClient(
  process.env.AURITE_API_URL || 'http://localhost:8000',
  process.env.API_KEY || 'your-api-key'
);

// Run an agent
const result = await client.execution.runAgent('Weather Agent', {
  user_message: 'What is the weather in San Francisco?',
});

console.log(result.final_response?.content);
```

## Development

### Workspace Commands

```bash
# Build all packages
npm run build

# Start Aurite Studio (from frontend root)
npm start

# Run tests across all packages
npm run test

# Lint all packages
npm run lint

# Format code across all packages
npm run format

# Type check all packages
npm run typecheck

# Validate all packages (lint + format + test)
npm run validate

# Development mode (watch mode for all packages)
npm run dev
```

### Package-Specific Commands

#### API Client

```bash
# Build API client
npm run build:api-client

# Run API client examples
npm run example --workspace=packages/api-client

# Run integration tests
npm run test:integration --workspace=packages/api-client

# Development mode
npm run dev --workspace=packages/api-client
```

#### Aurite Studio

```bash
# Start development server
npm start --workspace=packages/aurite-studio

# Build for production
npm run build --workspace=packages/aurite-studio

# Run tests
npm run test --workspace=packages/aurite-studio
```

### Development Workflow

1. **Setup**: Install dependencies and configure environment
2. **Development**: Use `npm run dev` for watch mode development across all packages
3. **Testing**: Run `npm run test` for comprehensive testing
4. **Validation**: Use `npm run validate` before committing
5. **Building**: Run `npm run build` for production builds

## Examples and Usage

### API Client Examples

The API client includes comprehensive examples for all functionality:

```bash
# Run basic examples
npm run example --workspace=packages/api-client

# Run integration tests (requires running API server)
npm run example:integration --workspace=packages/api-client
```

**Example Categories:**

- **Configuration Management**: List, create, update configurations
- **Agent Execution**: Run agents with streaming support
- **Workflow Management**: Execute linear and custom workflows
- **MCP Server Management**: Register and manage MCP servers
- **Tool Execution**: Direct tool invocation
- **System Operations**: Health checks and system information

### Aurite Studio Usage

#### Creating Your First Agent

1. Navigate to the Home page in Aurite Studio
2. Describe your agent in the main text area
3. Configure advanced options (optional):
   - Set a custom agent name
   - Select an LLM model configuration
   - Choose MCP servers for additional capabilities
4. Click "Create Agent" to save your configuration

#### Building Workflows

- **Linear Workflows**: Chain agents in sequence using the visual interface
- **Custom Workflows**: Create Python classes for complex logic and execution

#### Managing Configurations

- **MCP Servers**: Configure stdio, HTTP, and local transport types
- **LLM Configurations**: Set up multiple providers with custom parameters

## Testing

### Test Structure (TODO)

```
packages/
├── api-client/tests/
│   ├── unit/           # Unit tests for API client components
│   ├── integration/    # Integration tests with live API
│   └── fixtures/       # Test data and mock responses
└── aurite-studio/src/
    └── __tests__/      # React component tests
```

### Running Tests

```bash
# Run all tests
npm run test

# Run only unit tests
npm run test:unit

# Run only integration tests (requires API server)
npm run test:integration

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui
```

## Code Quality

### Linting and Formatting

The workspace uses ESLint and Prettier for code quality:

```bash
# Lint all packages
npm run lint

# Fix linting issues
npm run lint:fix

# Format code
npm run format

# Check formatting
npm run format:check
```

### Pre-commit Hooks

The workspace includes Husky for pre-commit hooks:

- **Lint-staged**: Automatically formats and lints staged files
- **Type checking**: Ensures TypeScript compilation
- **Test validation**: Runs relevant tests

## TypeScript Configuration

The workspace uses TypeScript project references for efficient builds:

- **Root config**: `tsconfig.json` - Project references only
- **Package configs**: Individual TypeScript configurations per package
- **Test configs**: Separate configurations for testing environments

## Environment Variables

### Required Variables

- `AURITE_API_URL`: Base URL for the Aurite API server
- `API_KEY`: Authentication key for API access

### Aurite Studio Specific

- `REACT_APP_API_URL`: API URL for React app (defaults to http://localhost:8000)
- `REACT_APP_API_KEY`: API key for React app authentication

### Optional Variables

- `NODE_ENV`: Environment mode (development, test, production)
- `REACT_APP_ENVIRONMENT`: Environment for React app
- `REACT_APP_DEBUG_MODE`: Enable debug mode for React app

## Deployment

### API Client (NPM Package)

```bash
# Build for publication
npm run build:api-client

# Publish to NPM (from api-client directory)
cd packages/api-client
npm publish
```

### Aurite Studio (Web Application)

#### Production Build

```bash
# Build optimized production bundle
npm run build --workspace=packages/aurite-studio

# Serve static files (example with serve)
npx serve -s packages/aurite-studio/build -l 3000
```

#### Docker Deployment

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY frontend/package*.json ./
COPY frontend/packages/aurite-studio/package*.json ./packages/aurite-studio/
RUN npm ci --only=production
COPY frontend/ .
RUN npm run build --workspace=packages/aurite-studio

FROM nginx:alpine
COPY --from=build /app/packages/aurite-studio/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Environment-Specific Configuration

For different environments, create environment-specific `.env` files:

- `.env.development` - Development settings
- `.env.staging` - Staging environment
- `.env.production` - Production configuration

## Contributing

### Development Setup

1. Fork and clone the repository
2. Install dependencies: `npm install`
3. Set up environment variables
4. Run tests to ensure everything works: `npm run test`
5. Start development: `npm run dev`

### Code Standards

- **TypeScript**: All code must be written in TypeScript
- **Testing**: Maintain test coverage above 80%
- **Documentation**: Update documentation for new features
- **Linting**: Follow ESLint configuration
- **Formatting**: Use Prettier for consistent formatting

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with appropriate tests
3. Run `npm run validate` to ensure quality
4. Submit a pull request with clear description

## Troubleshooting

### Common Issues

#### Build Failures

```bash
# Clean and rebuild all packages
npm run clean
npm run build
```

#### Test Failures

```bash
# Ensure API server is running for integration tests
# Check environment variables are set correctly
# Verify network connectivity to API server
```

#### TypeScript Cache Issues

**Problem:** You encounter TypeScript errors like:

```
ERROR in src/services/agents.service.ts:339:29
TS2339: Property 'session_id' does not exist on type 'AgentRunResult'.
```

Even though the property exists in the type definition, TypeScript compilation cache can become stale when type definitions change between packages in the monorepo.

**Solution:** Use the cache-clearing rebuild scripts:

```bash
# Standard cache-clearing rebuild (most common solution)
npm run rebuild

# Nuclear option - clears all caches including bundler caches
npm run rebuild:fresh

# TypeScript-specific cache clearing
npm run clean:cache
```

**Why This Works:**

- Deletes stale compiled type information in `/dist` folders
- Forces fresh compilation of all cross-package type dependencies
- Clears inconsistent cached state in TypeScript's incremental build system

**When to Use Each Script:**

- `npm run rebuild` - First try for most TypeScript cache issues
- `npm run rebuild:fresh` - When `rebuild` doesn't resolve the issue
- `npm run clean:cache` - For TypeScript-only cache problems without full rebuild

#### Type Errors

```bash
# Regenerate TypeScript declarations
npm run build
```

#### Aurite Studio Issues

**Connection Refused:**

- Ensure the API server is running on the correct port
- Check that `REACT_APP_API_URL` matches your server configuration
- Verify firewall settings allow connections

**Authentication Errors:**

- Verify your API key is correctly set in `.env`
- Check that the API server has authentication enabled
- Ensure the API key has necessary permissions

#### Windows Setup Issues

If you're experiencing build or script execution issues on Windows, this is likely due to Windows-specific npm workspace binary path resolution problems.

**Quick Fix:**

1. Use PowerShell instead of Command Prompt
2. Ensure all environment variables are properly set
3. Run `npm install` from the frontend root directory

**Expected fixes in package.json files:**

```json
// api-client/package.json
"clean": "npx rimraf dist"

// aurite-studio/package.json
"build": "npx craco build"

// root package.json
"prepare": "npx husky install 2>nul || echo 'Husky install skipped'"
```

### Getting Help

- **Documentation**: Check the `docs/` directory in the repository root
- **API Client Examples**: Review the `examples/` directory in the api-client package
- **Aurite Studio Guide**: See the [Aurite Studio README](packages/aurite-studio/README.md)
- **Issues**: Report bugs on [GitHub Issues](https://github.com/aurite-ai/aurite-agents/issues)
- **Discussions**: Join discussions on [GitHub Discussions](https://github.com/aurite-ai/aurite-agents/discussions)

## License

MIT License - see [LICENSE](../LICENSE) file for details.

## Links

- **Repository**: [https://github.com/aurite-ai/aurite-agents](https://github.com/aurite-ai/aurite-agents)
- **Documentation**: [https://github.com/aurite-ai/aurite-agents](https://github.com/aurite-ai/aurite-agents)
- **API Reference**: [API Documentation](../docs/usage/api_reference.md)
- **Aurite Studio**: [Studio Documentation](packages/aurite-studio/README.md)
- **API Client**: [Client Documentation](packages/api-client/README.md)
- **Issues**: [GitHub Issues](https://github.com/aurite-ai/aurite-agents/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aurite-ai/aurite-agents/discussions)
