# Aurite Agents Codebase Reference
## About Aurite

Aurite is an AI Infrastructure company focused on developing and managing enterprise-grade AI agent systems. Our core technology revolves around building robust frameworks for AI agent orchestration, including:

- Tool and prompt management
- Agent development and deployment
- Intelligent agent routing and coordination
- Integration with Model Context Protocol (MCP)

Our agent framework provides a comprehensive solution for creating, deploying, and managing AI agents at scale. Built around Anthropic's Model Context Protocol (MCP), we enable seamless integration between language models and specialized tools while maintaining enterprise-level reliability and security.

The framework in this repository implements core agent capabilities including:
- MCP server development and management
- Agent routing and orchestration
- Tool integration and discovery
- Prompt engineering and management
- Storage and state management

## Build & Test Commands
- Must be in the `aurite-mcp` directory to run these commands
- Install: `pip install -e .`
- Testing: `python -m pytest`
- Start MCP: `mcp-server`

## Code Style Guidelines
### Python
- Imports: stdlib first, then third-party, then local
- Types: Type annotations, DataClasses for structured data
- Naming: PascalCase (classes), snake_case (functions), UPPER_SNAKE_CASE (constants)
- Error handling: Specific exception catching with structured responses and logging
- File Structure: `src/` for source code, `tests/` for tests, `examples/` for examples. File names must be descriptive like `postgres_server.py` instead of `server.py` and directory structure defines import hierarchy (e.g. storage_router.py uses postgres_server.py and mysql_server.py located in a storage/sql/ subfolder).

## Current Direction

### Implementing Storage Solution MCP Servers and a Storage Router to route between them
Currently implementing a suite of storage-focused MCP servers to provide database access and management capabilities:

1. **PostgreSQL MCP Server**
   - Direct database interaction through MCP tools
   - Schema introspection and query capabilities
   - Read-only transaction safety
   - Resource listing for database tables

2. **Storage Router MCP Server**
   - Central routing for multiple storage solutions
   - Dynamic tool and prompt switching based on storage type
   - Similar architecture to meta.server.ts for hot-swapping
   - Will support PostgreSQL, MySQL, and vector databases

3. **Future Storage Implementations**
   - MySQL MCP Server with similar capabilities to PostgreSQL
   - Vector database support for embedding storage
   - Potential for other specialized storage solutions

The Storage Router will act as an intelligent layer between Client Interfaces and specific storage implementations, selecting appropriate tools and system prompts based on the user's needs and the target storage system.
