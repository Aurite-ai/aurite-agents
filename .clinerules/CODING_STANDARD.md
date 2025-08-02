# Aurite Framework Coding Standard

**Document Type:** Core Development Standard
**When to Use:** For all code organization decisions in the framework

## The 3-Layer Rule

The Aurite Framework follows a clear 3-layer architecture:

```
src/aurite/
├── lib/        # Data Access Layer - "Reads and provides information"
├── execution/  # Runtime Layer - "Executes and orchestrates"
└── bin/        # Interface Layer - "User-facing entrypoints"
```

### Layer Responsibilities

| Layer        | Purpose                                                   | Examples                                                   |
| ------------ | --------------------------------------------------------- | ---------------------------------------------------------- |
| `lib/`       | Read configurations, manage storage, provide data access  | `config_manager.py`, `db_manager.py`, `session_manager.py` |
| `execution/` | Execute components, orchestrate workflows, manage runtime | `aurite_engine.py`, `mcp_host.py`, `agent.py`              |
| `bin/`       | CLI commands, TUI apps, API routes, user interfaces       | `cli.py`, `tui.py`, `api.py`                               |

**Golden Rule:** `lib/` provides → `execution/` uses → `bin/` exposes

---

## Naming Conventions

### Files and Directories

- **Files:** `snake_case.py`
- **Directories:** `snake_case/`
- **Classes:** `PascalCase`
- **Functions/Variables:** `snake_case`

### Special Patterns

- **Route files:** `{domain}_routes.py` (e.g., `config_routes.py`, `execution_routes.py`)
- **Model files:** `{purpose}.py` (e.g., `requests.py`, `responses.py`, `components.py`)
- **Test files:** `test_{module}.py`
- **Init templates:** Keep original structure for user familiarity

---

## Directory Organization Rules

### When to Create Subdirectories

| Scenario                       | Action                  | Example                                      |
| ------------------------------ | ----------------------- | -------------------------------------------- |
| 1-2 related files              | Keep flat               | `lib/config/config_manager.py`               |
| 3+ related files               | Create subdirectory     | `lib/components/agent/`                      |
| Different concerns             | Separate directories    | `lib/storage/db/` vs `lib/storage/sessions/` |
| Large single file (>500 lines) | Split into subdirectory | `bin/cli/commands/`                          |

### Domain-First Organization

Organize by **domain first, then by purpose**:

✅ **Good:** `lib/components/agent/agent.py`
❌ **Avoid:** `lib/models/agent_models.py`

✅ **Good:** `lib/storage/db/db_manager.py`
❌ **Avoid:** `lib/managers/db_storage_manager.py`

### Resource Collocation

Keep related resources together:

- CSS files with TUI apps: `bin/tui/styles/`
- Templates with init logic: `lib/init_templates/`
- Test fixtures with tests: `tests/fixtures/`

---

## Import and Export Patterns

### Clean Public APIs

Use `__init__.py` files to create clean import paths:

```python
# lib/models/__init__.py
from .api.requests import *
from .api.responses import *
from .config.components import *

# Usage in other files
from aurite.lib.models import AgentConfig, AgentRunResult
```

### Avoid Deep Imports

❌ **Avoid:**

```python
from aurite.lib.storage.sessions.session_manager import SessionManager
```

✅ **Prefer:**

```python
from aurite.lib.storage import SessionManager
```

### Layer Import Rules

- `bin/` can import from `execution/` and `lib/`
- `execution/` can import from `lib/` only
- `lib/` should be self-contained (minimal external dependencies)

---

## Common Scenarios

### Adding a New Component Type

1. **Create domain directory:** `lib/components/{component_type}/`
2. **Add main class:** `lib/components/{component_type}/{component_type}.py`
3. **Add config model:** `lib/models/config/components.py`
4. **Add API models:** `lib/models/api/requests.py` and `responses.py`
5. **Update exports:** `lib/components/__init__.py` and `lib/models/__init__.py`

### Adding a New CLI Command

1. **Create command file:** `bin/cli/commands/{command_name}.py`
2. **Register in main:** `bin/cli/cli.py`
3. **Add completion if needed:** `bin/cli/commands/{command_name}.py`

### Adding a New API Endpoint

1. **Create route file:** `bin/api/routes/{domain}_routes.py`
2. **Register router:** `bin/api/routes/__init__.py`
3. **Add request/response models:** `lib/models/api/`

### Splitting a Large File

When a file grows beyond ~500 lines:

1. **Identify logical groups** of related functions/classes
2. **Create subdirectory** with the original filename
3. **Split into focused modules** (e.g., `manager.py`, `validator.py`, `utils.py`)
4. **Create `__init__.py`** that exports the public API
5. **Update imports** in dependent files

---

## File Size Guidelines

| File Type              | Recommended Max | Action When Exceeded                |
| ---------------------- | --------------- | ----------------------------------- |
| Single-purpose module  | 300 lines       | Consider splitting responsibilities |
| Multi-purpose module   | 500 lines       | Split into subdirectory             |
| Main application files | 800 lines       | Extract components/screens          |
| Configuration files    | No limit        | Keep as-is for clarity              |

---

## Examples from Codebase

### Well-Organized Structure

```
lib/components/agent/
├── __init__.py           # Exports Agent, AgentTurnProcessor
├── agent.py             # Main Agent class
└── agent_turn_processor.py  # Supporting logic

lib/storage/
├── __init__.py          # Exports all managers
├── db/                  # Database concerns
│   ├── db_manager.py
│   └── db_models.py
└── sessions/            # Session concerns
    ├── session_manager.py
    └── cache_manager.py
```

### Clean Import Pattern

```python
# In execution/aurite_engine.py
from ..lib.components import Agent, LinearWorkflowExecutor
from ..lib.config import ConfigManager
from ..lib.storage import SessionManager, StorageManager
```

---

## Quick Decision Tree

**"Where does my new file go?"**

1. **Is it a user interface?** → `bin/`
2. **Does it execute/orchestrate components?** → `execution/`
3. **Does it read/manage data?** → `lib/`

**"Should I create a subdirectory?"**

1. **Do I have 3+ related files?** → Yes, create subdirectory
2. **Are there different concerns?** → Yes, separate directories
3. **Is the file >500 lines?** → Yes, split into subdirectory

**"How should I name it?"**

1. **Domain first:** `components/agent/` not `models/agent_models/`
2. **Purpose second:** `agent.py` and `agent_turn_processor.py`
3. **Follow patterns:** `{domain}_routes.py`, `{purpose}.py`

---

## Validation Checklist

Before committing code, verify:

- [ ] File is in the correct layer (`lib/`, `execution/`, or `bin/`)
- [ ] Directory follows domain-first organization
- [ ] Naming follows snake_case conventions
- [ ] Imports use clean paths via `__init__.py` exports
- [ ] Related files are grouped together
- [ ] No circular dependencies between layers

---

This standard evolves with the framework. When in doubt, follow existing patterns in the codebase and prioritize clarity and consistency.
