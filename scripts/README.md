# Aurite Framework Scripts Directory

This directory contains various scripts and utilities for developing, testing, building, and maintaining the Aurite Framework. The scripts are organized by purpose to improve discoverability and maintainability.

## Directory Structure

```
scripts/
├── README.md                    # This file - index of all scripts
├── build/                       # Build and release automation
├── setup/                       # Environment and project setup
├── dev/                         # Development utilities
├── test/                        # Testing utilities and runners
└── utils/                       # Standalone utilities
```

## Build Scripts (`build/`)

Scripts for building, packaging, and releasing the framework.

### `build_frontend.py`
**Purpose:** Build React frontend packages for distribution with the Python package  
**Usage:** `python scripts/build/build_frontend.py`  
**Description:** Builds the React frontend and copies static assets to the appropriate location in the Python package structure. Enhanced for CI/CD environments with better error reporting and validation.

### `release.py`
**Purpose:** Streamlined release script for Aurite framework  
**Usage:** 
- `python scripts/build/release.py 0.3.27` (specific version)
- `python scripts/build/release.py patch` (auto-increment patch)
- `python scripts/build/release.py minor` (auto-increment minor)
- `python scripts/build/release.py major` (auto-increment major)

**Description:** Automates local preparation steps for a new release including version updates, frontend builds, tests, package building, and git tagging.

### `test_wheel_install.py`
**Purpose:** Test script to simulate pip wheel installation and verify static asset detection  
**Usage:** `python scripts/build/test_wheel_install.py`  
**Description:** Creates a temporary virtual environment, installs the built wheel package, and verifies that static assets are properly bundled and detectable.

### `test_static_detection.py`
**Purpose:** Test script to debug static asset detection in the wheel package  
**Usage:** `python scripts/build/test_static_detection.py`  
**Description:** Tests if static assets can be detected correctly in both development and packaged environments.

## Setup Scripts (`setup/`)

Scripts for environment setup and project initialization.

### `setup.sh` / `setup.bat`
**Purpose:** Cross-platform setup scripts for the Aurite Framework  
**Usage:** 
- Linux/macOS: `./scripts/setup/setup.sh`
- Windows: `scripts\setup\setup.bat`

**Description:** Handles Docker setup, environment configuration, dependency installation, and service startup. Includes interactive configuration for API keys and project settings.

### `create_postman_env.py`
**Purpose:** Generate Postman environment files from .env configuration  
**Usage:** `python scripts/setup/create_postman_env.py`  
**Description:** Reads a .env file and creates a Postman environment JSON file for API testing.

### `.bash_aurite`
**Purpose:** Bash functions and aliases for streamlined development and testing  
**Usage:** `source scripts/setup/.bash_aurite` (add to ~/.bashrc or ~/.zshrc)  
**Description:** Provides convenient functions for running tests, starting services, and common development tasks. Includes functions like `testaurite`, `testapi`, `testauritecomp`, etc.

## Development Utilities (`dev/`)

Tools for code maintenance, debugging, and development workflow.

### `fix_all_imports.py`
**Purpose:** Fix incorrect config_models imports throughout the codebase  
**Usage:** `python scripts/dev/fix_all_imports.py`  
**Description:** Automatically updates import statements to use the correct module paths after refactoring.

### `convert_obsidian_links.py`
**Purpose:** Convert Obsidian-style links to standard Markdown links  
**Usage:** `python scripts/dev/convert_obsidian_links.py`  
**Description:** Recursively finds Markdown files and converts `[[file|text]]` links to `[text](file)` format.

### `regen_openapi_specs.py`
**Purpose:** Regenerate OpenAPI specification files  
**Usage:** `python scripts/dev/regen_openapi_specs.py`  
**Description:** Fetches the OpenAPI schema from a running server and converts it to YAML format.

### `debug_registration.py`
**Purpose:** Debug script for testing component registration  
**Usage:** `python scripts/dev/debug_registration.py`  
**Description:** Tests LLM and agent registration functionality with detailed logging for troubleshooting.

## Testing Scripts (`test/`)

Comprehensive testing utilities organized by test type.

### `test_runner.py`
**Purpose:** Advanced test runner with optimization strategies  
**Usage:** `python scripts/test/test_runner.py [strategy] [--report]`  
**Strategies:** fast, integration, mcp, orchestration, smoke, parallel, comprehensive, performance  
**Description:** Provides optimized test execution with comprehensive reporting and performance monitoring.

### Integration Tests (`test/integration/`)

Scripts for testing integration between components and external services.

#### `test_langfuse_integration.py`
**Purpose:** Test Langfuse integration with proper spans and sessions  
**Usage:** `python scripts/test/integration/test_langfuse_integration.py`  
**Description:** Verifies Langfuse tracing functionality with agent execution and session management.

#### `test_system_routes.py`
**Purpose:** Test System Management API routes  
**Usage:** `python scripts/test/integration/test_system_routes.py`  
**Description:** Tests all `/system/*` endpoints including health checks, metrics, and environment management.

#### `test_shutdown_fix.py`
**Purpose:** Test async shutdown fixes for litellm client  
**Usage:** `python scripts/test/integration/test_shutdown_fix.py`  
**Description:** Verifies clean shutdown without AttributeError or unclosed session warnings.

#### `test_mcp_timeout_error.py`
**Purpose:** Test MCP server timeout error handling  
**Usage:** `python scripts/test/integration/test_mcp_timeout_error.py`  
**Description:** Creates test MCP server configurations with short timeouts to verify structured error responses.

### Component Tests (`test/component/`)

Tests for specific framework components.

#### Config Tests (`test/component/config/`)
- Various configuration testing scripts for validation, file paths, and API endpoints
- Tests for LLM validation, invalid types, and configuration management

#### Facade Tests (`test/component/facade/`)
- Facade/API testing scripts for session management, history endpoints, and workflow execution
- Tests for cache persistence, cleanup endpoints, and message content handling

#### Host Tests (`test/component/host/`)
- MCP host testing scripts for server registration and route handling
- Simple MCP tests and host functionality verification

### Manual Tests (`test/manual/`)

Scripts for manual testing and debugging specific scenarios.

#### `temp_agent_runner.py`
**Purpose:** Simple agent execution test  
**Usage:** `python scripts/test/manual/temp_agent_runner.py`  
**Description:** Runs the Weather Agent and prints results for manual verification.

#### `langfuse_test.py`
**Purpose:** Basic Langfuse integration test  
**Usage:** `python scripts/test/manual/langfuse_test.py`  
**Description:** Simple test for Langfuse tracing functionality.

#### `db_api_test.py` / `db_crud_test.py`
**Purpose:** Database API and CRUD operation tests  
**Usage:** 
- `python scripts/test/manual/db_api_test.py`
- `python scripts/test/manual/db_crud_test.py`

**Description:** Test database operations in both API and direct CRUD modes.

## Utilities (`utils/`)

Standalone utility scripts for various maintenance tasks.

### `test_import_fix.py`
**Purpose:** Test script to verify import fix resolves ModuleNotFoundError  
**Usage:** `python scripts/utils/test_import_fix.py`  
**Description:** Tests specific functionality that was failing due to import issues and verifies the fix works correctly.

## Usage Guidelines

### Running Scripts

1. **Always run from project root:** Most scripts expect to be run from the project root directory
2. **Check dependencies:** Some scripts require specific environment variables or running services
3. **Use appropriate Python environment:** Ensure you're in the correct virtual environment

### Development Workflow

1. **Setup:** Use `scripts/setup/setup.sh` for initial project setup
2. **Development:** Use `scripts/dev/` utilities for code maintenance
3. **Testing:** Use `scripts/test/test_runner.py` for comprehensive testing
4. **Building:** Use `scripts/build/` scripts for packaging and release

### Adding New Scripts

When adding new scripts:

1. **Choose the right category** based on the script's primary purpose
2. **Follow naming conventions** (snake_case.py)
3. **Add documentation** to this README
4. **Include usage examples** and clear descriptions
5. **Add appropriate shebang** (`#!/usr/bin/env python3`) for executable scripts

## Environment Variables

Many scripts rely on environment variables. Key variables include:

- `API_KEY`: For API authentication in tests
- `AURITE_ENABLE_DB`: Enable database mode for testing
- `LANGFUSE_*`: Langfuse integration credentials
- `ANTHROPIC_API_KEY`: For LLM provider testing

## Contributing

When modifying scripts:

1. **Test thoroughly** before committing changes
2. **Update documentation** in this README
3. **Follow the existing code style** and patterns
4. **Consider backward compatibility** for widely-used scripts
5. **Add error handling** and clear error messages

## Troubleshooting

### Common Issues

1. **Import errors:** Ensure you're running from the project root and in the correct Python environment
2. **Permission errors:** Some scripts may need execute permissions (`chmod +x script.py`)
3. **Missing dependencies:** Check if required services (API server, database) are running
4. **Environment variables:** Verify all required environment variables are set

### Getting Help

- Check script docstrings and help text (`python script.py --help` where available)
- Review the script source code for detailed implementation
- Check the main project documentation for context
- Look at similar scripts for usage patterns
