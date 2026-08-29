# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build/Test Commands

**Run single test file:**

```bash
pytest tests/unit/path/test_file.py
```

## Critical Patterns

**3-Layer Architecture (CRITICAL):**

- `lib/` = Data access (configs, storage, models)
- `execution/` = Runtime orchestration (engine, workflows)
- `bin/` = User interfaces (CLI, API, TUI)
- Import flow: `bin/` → `execution/` → `lib/` (never reverse)

**MCP Server Registration:**

- Servers are registered Just-In-Time (JIT) during agent execution
- Registration status cached in `MCPHost` to prevent race conditions

**Config Discovery:**

- Config Source Priority: project → workspace → other projects → user (~/.aurite)
- Component names must be unique across ALL types in a config source (enforced by validation)

**Import Patterns:**

- Use `from aurite.lib.models import AgentConfig` (via **init**.py exports)
- Avoid: `from aurite.lib.models.config.components import AgentConfig`

## Code Style (Non-Standard)

- **Domain-first organization:** `lib/components/agent/` NOT `lib/models/agent_models.py`
- **3+ files trigger subdirectory:** Keep flat until 3 related files exist
- **Route files pattern:** `{domain}_routes.py` (e.g., `config_routes.py`)
