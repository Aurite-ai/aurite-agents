# Claude Assistant Guide for Aurite Agents

This document provides Claude with essential context about the Aurite Agents framework to enable effective code assistance, feature development, and testing.

## Project Overview

Aurite Agents is a Python framework for building AI agents using the Model Context Protocol (MCP). The framework provides a layered architecture for orchestrating LLM-powered agents with external tools and resources.

### Key Technologies
- **Backend**: Python 3.11+, FastAPI, Pydantic, SQLAlchemy
- **Frontend**: React, TypeScript, Vite, TailwindCSS
- **Testing**: pytest, pytest-asyncio, pytest-mock
- **Package Management**: pip, pyproject.toml
- **Development Tools**: pre-commit, ruff, mypy

## Repository Structure

```
aurite-agents/
├── src/aurite/              # Main package source code
│   ├── bin/                 # Entrypoints (API, CLI, Worker)
│   ├── components/          # Core components (agents, workflows)
│   ├── config/              # Configuration management
│   ├── execution/           # Execution facade and executors
│   ├── host/                # MCP host implementation
│   ├── packaged/            # Templates for 'aurite init' command
│   └── storage/             # Database persistence layer
├── frontend/                # React frontend application
├── tests/                   # Comprehensive test suite
├── docs/                    # Documentation
├── config/                  # Example configurations
└── .clinerules/             # Development rules and workflows
```

## Essential Documentation

Before making any changes, Claude should consult these key documents:

1. **`.clinerules/MUST_READ_FIRST.md`** - Core project rules and architecture overview
2. **`.clinerules/documentation_guide.md`** - Maps tasks to relevant documentation
3. **`.clinerules/framework_development_rules.md`** - Multi-phase development workflow
4. **`docs/layers/framework_overview.md`** - Detailed architectural documentation

## Development Workflow

### Phase 1: Discovery & Context Retrieval
1. Review `.clinerules/documentation_guide.md` to identify relevant documents
2. Read component-specific documentation in `docs/components/`
3. Consult layer documents in `docs/layers/` for implementation details
4. Review source code and corresponding tests

### Phase 2: Planning & Design
1. Create implementation plans for complex tasks
2. Include testing in every implementation step
3. Plan for documentation updates as the final step

### Phase 3: Implementation
1. Follow the implementation plan step-by-step
2. Run tests after each change
3. Update documentation when implementation is complete

## Code Style and Standards

### Python Code
- Follow PEP 8 with 120-character line limit
- Use type hints for all function signatures
- Docstrings required for all public functions/classes
- Imports organized: standard library, third-party, local

### Frontend Code
- TypeScript with strict mode enabled
- React functional components with hooks
- TailwindCSS for styling
- Component files use PascalCase

## Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/orchestration/agent/test_agent.py

# Run specific test
pytest tests/orchestration/agent/test_agent.py::test_agent_creation

# Run with coverage
pytest --cov=src/aurite --cov-report=html

# Run tests in parallel
pytest -n auto
```

### Test Structure
- Unit tests: Test individual components in isolation
- Integration tests: Test component interactions
- Functional tests: End-to-end testing with real MCP servers

### Writing Tests
1. Place tests in the corresponding directory under `tests/`
2. Use descriptive test names: `test_<component>_<behavior>`
3. Use fixtures from `tests/fixtures/` for common test data
4. Mock external dependencies (LLMs, MCP servers) appropriately

## Common Development Tasks

### Adding a New Agent Configuration
1. Create/update JSON in `config/agents/`
2. Update `docs/components/agent.md` if adding new fields
3. Write tests in `tests/orchestration/agent/`

### Modifying API Endpoints
1. Update route in `src/aurite/bin/api/routes/`
2. Update `docs/layers/1_entrypoints.md`
3. Add/update tests in `tests/api/`
4. Update frontend if endpoint is consumed there

### Adding MCP Server Support
1. Test server with `tests/functional_mcp_client.py`
2. Add configuration to `src/aurite/packaged/component_configs/mcp_servers/`
3. Create documentation in `docs/toolbox/servers/`
4. Update `docs/toolbox/mcp_server_directory.md`

### Frontend Development
1. Components go in `frontend/src/components/`
2. Features go in `frontend/src/features/`
3. Update `frontend/README.md` for structural changes
4. Run frontend tests with `yarn test`

## Package Development

### Building the Package
```bash
# Install in development mode
pip install -e .

# Build distribution
python -m build

# Test the built package
pip install dist/aurite-*.whl
```

### Testing `aurite init`
```bash
# After making changes to src/aurite/packaged/
pip install -e .
cd /tmp
aurite init test_project
# Verify scaffolded files
```

## Configuration Management

### Project Configuration (`aurite_config.json`)
- Central configuration file for all components
- Located at project root
- References other configuration files
- See `docs/components/PROJECT.md` for details

### Component Configurations
- **Agents**: `config/agents/*.json`
- **LLMs**: `config/llms/*.json`
- **MCP Servers**: `config/mcp_servers/*.json`
- **Workflows**: `config/workflows/*.json`

## Error Handling Patterns

### API Errors
```python
from fastapi import HTTPException

# Use appropriate status codes
raise HTTPException(status_code=404, detail="Resource not found")
```

### Async Error Handling
```python
try:
    result = await async_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    # Handle gracefully
```

## Debugging Tips

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### MCP Server Debugging
```bash
# Test MCP server directly
python tests/functional_mcp_client.py '{"command": "npx", "args": ["server-name"]}' "test query"
```

### API Debugging
- Use Postman collections in `tests/api/`
- Check API logs for detailed error messages
- Use FastAPI's automatic `/docs` endpoint

## Important Conventions

### File Naming
- Python files: `snake_case.py`
- React components: `PascalCase.tsx`
- Test files: `test_<module_name>.py`
- Documentation: `lowercase_with_underscores.md`

### Import Organization
```python
# Standard library
import os
import sys

# Third-party
import pytest
from fastapi import FastAPI

# Local
from aurite.components.agents import Agent
from aurite.config import ConfigManager
```

### Async/Await Usage
- All MCP operations are async
- Use `asyncio.run()` for synchronous entry points
- Prefer `async with` for resource management

## Documentation Updates

After making changes, update relevant documentation:

1. Check `.clinerules/documentation_guide.md` for affected documents
2. Update component docs in `docs/components/` for config changes
3. Update layer docs in `docs/layers/` for architectural changes
4. Update `README.md` for user-facing changes
5. Update `README_packaged.md` for package-related changes

## Security Considerations

- Never commit `.env` files
- Use environment variables for sensitive data
- Validate all user inputs
- Sanitize file paths to prevent directory traversal
- Use parameterized queries for database operations

## Performance Considerations

- Use connection pooling for database operations
- Implement caching where appropriate
- Lazy-load large configurations
- Use streaming for large responses
- Profile code with `cProfile` for bottlenecks

## Useful Commands

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy src/

# Run pre-commit hooks
pre-commit run --all-files

# Start development servers
# Backend
cd src && python -m aurite.bin.api.main

# Frontend
cd frontend && yarn dev

# Run worker
python -m aurite.bin.worker.main
```

## Getting Help

- Review error messages carefully - they often contain the solution
- Check test files for usage examples
- Consult layer documentation for architectural questions
- Use the functional MCP client for testing server integrations

Remember: Always follow the three-phase development workflow (Discovery, Planning, Implementation) and ensure all tests pass before considering a task complete.
