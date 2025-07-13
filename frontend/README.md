# Aurite Framework Frontend

A comprehensive TypeScript/JavaScript frontend ecosystem for the Aurite Framework, providing type-safe clients and development tools for building applications that interact with Aurite agents and workflows.

## Overview

This frontend workspace contains TypeScript packages and tools for developers building applications with the Aurite Framework. The primary package is the `@aurite/api-client`, which provides a production-ready TypeScript client for the Aurite API.

## Architecture

```
frontend/
├── packages/
│   └── api-client/          # TypeScript API client package
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
git clone https://github.com/aurite/aurite-agents.git
cd aurite-agents/frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your API configuration
```

### Environment Configuration

Create a `.env` file in the frontend root:

```bash
# API Configuration
API_KEY=your_api_key_here
AURITE_API_URL=http://localhost:8000

# Environment
NODE_ENV=development
```

## Packages

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
```

### Package-Specific Commands

```bash
# Work with the API client specifically
npm run build:api-client
npm run example --workspace=packages/api-client
npm run test:integration --workspace=packages/api-client
```

### Development Workflow

1. **Setup**: Install dependencies and configure environment
2. **Development**: Use `npm run dev` for watch mode development
3. **Testing**: Run `npm run test` for comprehensive testing
4. **Validation**: Use `npm run validate` before committing
5. **Building**: Run `npm run build` for production builds

## API Client Examples

The API client includes comprehensive examples for all functionality:

```bash
# Run basic examples
npm run example --workspace=packages/api-client

# Run integration tests (requires running API server)
npm run example:integration --workspace=packages/api-client
```

### Example Categories

- **Configuration Management**: List, create, update configurations
- **Agent Execution**: Run agents with streaming support
- **Workflow Management**: Execute simple and custom workflows
- **MCP Server Management**: Register and manage MCP servers
- **Tool Execution**: Direct tool invocation
- **System Operations**: Health checks and system information

## Testing

### Test Structure

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests with live API
└── fixtures/       # Test data and mock responses
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

### Optional Variables

- `NODE_ENV`: Environment mode (development, test, production)

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

**Build Failures:**
```bash
# Clean and rebuild
npm run clean
npm run build
```

**Test Failures:**
```bash
# Ensure API server is running for integration tests
# Check environment variables are set correctly
# Verify network connectivity to API server
```

**Type Errors:**
```bash
# Regenerate TypeScript declarations
npm run build:types
```

### Getting Help

- **Documentation**: Check the `docs/` directory in the repository root
- **Examples**: Review the `examples/` directory in the api-client package
- **Issues**: Report bugs on [GitHub Issues](https://github.com/aurite/aurite-agents/issues)
- **Discussions**: Join discussions on [GitHub Discussions](https://github.com/aurite/aurite-agents/discussions)

## License

MIT License - see [LICENSE](../LICENSE) file for details.

## Links

- **Repository**: [https://github.com/aurite/aurite-agents](https://github.com/aurite/aurite-agents)
- **Documentation**: [https://aurite.dev](https://aurite.dev)
- **API Reference**: [API Documentation](../docs/usage/api_reference.md)
- **Issues**: [GitHub Issues](https://github.com/aurite/aurite-agents/issues)
