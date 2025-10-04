# Aurite Agents Development Guide

**Target Audience:** Coding copilots and developers building MCP servers, agents, and custom workflows.

**Purpose:** Quick-reference guide for component development workflow, file organization, and testing strategies.

---

## Quick Navigation

1. [Component Decision Tree](#component-decision-tree) ← **Start here**
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Component Types](#component-types)
5. [Testing Strategy](#testing-strategy)
6. [Quick Reference](#quick-reference)

---

## Component Decision Tree

**📍 Start here to determine what to build:**

```
What are you building?
│
├─ Simple CRUD operation or direct service wrapper?
│  └─ YES → API Extension
│      • Fast, no overhead, REST endpoints
│      • See: docs/usage/api_extensions_detailed_guide.md
│
├─ Reusable tools for agents to discover and use?
│  └─ YES → MCP Server (Follow 8-step workflow, steps 1-5)
│      • Tool discovery, parameter docs, multi-agent reuse
│      • Continue to: MCP Servers section
│
├─ Multi-step orchestration with conditional logic?
│  └─ YES → Custom Workflow (Follow 8-step workflow, steps 1-5)
│      • Full Python control, agent coordination
│      • Continue to: Custom Workflows section
│
└─ Task-specific assistant combining tools?
   └─ YES → Agent (Follow 8-step workflow, steps 6-8)
       • Stateful conversations, tool combinations
       • Continue to: Agents section
```

**Quick Comparison:**

| Feature                 | API Extension | MCP Server  | Custom Workflow | Agent           |
| ----------------------- | ------------- | ----------- | --------------- | --------------- |
| **Complexity**          | Low           | Medium      | High            | Medium          |
| **Agent Orchestration** | ❌            | ❌          | ✅              | ✅              |
| **Tool Discovery**      | ❌            | ✅          | ❌              | N/A             |
| **REST Endpoints**      | ✅            | ❌          | ❌              | Via API         |
| **Best For**            | CRUD ops      | Agent tools | Orchestration   | Task assistants |

---

## Project Structure

### Standard Directory Layout

```
your_project/
├── .aurite                              # Project marker
├── config/                              # All configurations
│   ├── agents/{feature}/
│   │   ├── {name}.yml
│   │   └── {name}_eval.yml
│   ├── mcp_servers/{name}/
│   │   ├── {name}_config.yml
│   │   └── {name}_evaluation.yml
│   ├── custom_workflows/{feature}/
│   │   ├── {name}.yml
│   │   └── {name}_eval.yml
│   └── llms.yml
├── src/
│   ├── api/                             # API extensions
│   │   └── {name}_extension.py
│   ├── servers/{name}/                  # MCP servers
│   │   ├── {name}_manager.py            # Business logic
│   │   └── {name}_server.py             # MCP wrapper
│   └── custom_workflows/
│       └── {name}.py
├── tests/servers/
│   └── test_{name}_manager.py
└── data/                                # Data files
```

### Key Principles

1. **Feature-based grouping** - Organize by domain (e.g., `1_license`, `2_sales`)
2. **Separation of concerns** - Business logic separate from interfaces
3. **Co-location** - Tests next to components
4. **Reusability** - Managers shared between servers and workflows

---

## Development Workflow

### Overview

**Three phases, test-driven approach:**

1. **Core Logic** - Test business logic (pytest)
2. **Interface** - Test tool/workflow interface (evaluation)
3. **Integration** - Test end-to-end behavior (evaluation)

**Development order:**

- MCP Servers (independent) → Agents (require servers) → Custom Workflows (require agents if orchestrating)

---

### Phase 1: Core Logic (Steps 1-2)

**📍 For:** MCP Servers, Custom Workflows with shared logic

#### Step 1: Implement Manager

```python
# src/servers/excel/excel_manager.py
class ExcelManager:
    """Core business logic for Excel operations."""

    def read_sheet(self, file_path: str, sheet_name: str) -> List[Dict[str, Any]]:
        """Read data from an Excel sheet."""
        # Implementation
        pass
```

**File locations:**

- MCP Servers: `src/servers/{name}/{name}_manager.py`
- Workflows: `src/custom_workflows/{name}.py`

#### Step 2: Test with pytest

```python
# tests/servers/test_excel_manager.py
def test_read_sheet():
    manager = ExcelManager("test.xlsx")
    data = manager.read_sheet("Sheet1")
    assert len(data) > 0
```

**Focus:**

- ✅ Core functionality
- ✅ Basic error handling
- ⚠️ Edge cases less critical (except security)

**Exit:** All pytest tests pass

---

### Phase 2: Interface (Steps 3-5)

**📍 Branch here based on component type:**

#### For MCP Servers

**Step 3: Create MCP Wrapper**

```python
# src/servers/excel/excel_server.py
from mcp.server.fastmcp import FastMCP
from .excel_manager import ExcelManager

mcp = FastMCP("excel-server")

@mcp.tool()
async def read_excel_sheet(file_path: str, sheet_name: str) -> dict:
    """Read data from an Excel sheet.

    Args:
        file_path: Path to Excel file
        sheet_name: Sheet to read

    Returns:
        {"success": bool, "data": list}
    """
    manager = ExcelManager(file_path)
    data = manager.read_sheet(sheet_name)
    return {"success": True, "data": data}

if __name__ == "__main__":
    mcp.run()
```

**Configuration (choose transport):**

```yaml
# config/mcp_servers/excel/excel_server.yml

# Option 1: Stdio (Python scripts)
- name: excel_server
  type: mcp_server
  server_path: src/servers/excel/excel_server.py
  capabilities: [tools]
  timeout: 15.0

# Option 2: Local Command (CLI tools)
- name: github_server
  type: mcp_server
  command: npx
  args: ["-y", "@modelcontextprotocol/server-github"]
  capabilities: [tools]

# Option 3: HTTP Stream (Remote services)
- name: remote_api
  type: mcp_server
  http_endpoint: https://my-service.com/mcp
  headers:
    X-API-Key: "{MY_API_KEY}"
  capabilities: [tools, resources]
```

#### For Custom Workflows

**⚠️ Prerequisites:** If orchestrating agents, complete steps 1-8 for those agents first.

**Step 3: Create Workflow**

```python
# src/custom_workflows/license_reminder_workflow.py
from aurite import AuriteEngine, BaseCustomWorkflow

class LicenseReminderWorkflow(BaseCustomWorkflow):
    """Send reminders for plates ready for pickup."""

    async def run(self, initial_input, executor: "AuriteEngine", session_id=None):
        # Query database
        db_result = await executor.run_agent(
            agent_name="db_agent",
            user_message="Find customers with plates ready > 3 days",
            session_id=session_id
        )

        # Generate emails
        for customer in db_result.data:
            await executor.run_agent(
                agent_name="email_agent",
                user_message=f"Generate reminder for {customer['name']}",
                session_id=session_id
            )

        return {"sent": len(db_result.data), "status": "complete"}
```

**Configuration:**

```yaml
# config/custom_workflows/1_license/license_reminder.yml
- name: license_reminder_workflow
  type: custom_workflow
  module_path: src.custom_workflows.license_reminder_workflow
  class_name: LicenseReminderWorkflow
  description: Send reminder emails for ready plates
```

#### Step 4: Create Evaluation

```yaml
# config/mcp_servers/excel/excel_server_evaluation.yml
name: excel_server_eval
type: evaluation
component_type: mcp_server
component_refs: [excel_server]
review_llm: anthropic_claude_3_haiku

test_cases:
  - name: read_basic
    input: "Read the 'Sales' sheet from data/test.xlsx"
    expectations:
      - "The read_excel_sheet tool is called"
      - "Response contains data from Sales sheet"
      - "Response includes column headers"

  - name: tool_sequence
    input: "Write a row to 'Sales', then read it back"
    expectations:
      - "write_excel_row called first"
      - "read_excel_sheet called second"
      - "Written data visible in read result"
```

**Focus:**

- ✅ Tool flow (correct sequence)
- ✅ Tool interface (agents can use)
- ❌ Internal logic (covered by pytest)

#### Step 5: Run Evaluation

```bash
aurite test excel_server_eval
```

**Exit:** All test cases pass → Interface works for agents

---

### Phase 3: Agent Integration (Steps 6-8)

**📍 For:** Agents using MCP servers or workflows

#### Step 6: Create Agent Config

```yaml
# config/agents/1_license/license_agent.yml
name: license_plate_agent
type: agent
description: Manages license plate notifications

llm_config_id: anthropic_claude_3_5_sonnet

system_prompt: |
  You are a license plate notification assistant for a dealership.
  Use available tools to check plate status and send notifications.
  Always verify status before sending notifications.

mcp_servers:
  - excel_server
  - sqlite_server
  - gmail_server

max_iterations: 10
include_history: true
```

#### Step 7: Create Agent Evaluation

```yaml
# config/agents/1_license/license_agent_eval.yml
name: license_agent_eval
type: evaluation
component_type: agent
component_refs: [license_plate_agent]
review_llm: anthropic_claude_3_haiku

test_cases:
  - name: check_ready
    input: "Check which plates are ready"
    expectations:
      - "Queries database for status 'ready'"
      - "Provides clear list"
      - "Includes customer info"

  - name: send_notification
    input: "Send notification to John Doe about ABC123"
    expectations:
      - "Looks up contact info"
      - "Generates notification content"
      - "Uses email tool"
      - "Confirms sent"

  - name: error_handling
    input: "Send notification for nonexistent plate"
    expectations:
      - "Queries database first"
      - "Reports plate doesn't exist"
      - "Does NOT send email"
```

#### Step 8: Run Agent Evaluation

```bash
aurite test license_agent_eval
```

**Exit:** All tests pass → Agent is production-ready

---

### Rate Limiting

**Problem:** Many concurrent tests can trigger rate limits.

**Solutions:**

1. **Limit concurrency** (in eval config):

```yaml
max_concurrent_tests: 3
rate_limit_retry_count: 3
rate_limit_base_delay: 1.0
```

2. **Split test suites**:

```
{name}_eval_basic.yml
{name}_eval_edge_cases.yml
{name}_eval_errors.yml
```

3. **Filter test cases**:

```bash
aurite test {name}_eval --test-cases "test1,test2"
aurite test {name}_eval --test-cases "send_*"
aurite test {name}_eval --test-cases "0,2,4"
```

---

## Component Types

### API Extensions

**When to use:**

- ✅ Simple CRUD operations
- ✅ Direct frontend access needed
- ✅ No agent orchestration

**When NOT to use:**

- ❌ Need tool discovery by agents
- ❌ Complex orchestration logic

**Quick example:**

```python
# src/api/dealership_extension.py
from fastapi import APIRouter, Security
from aurite.bin.api import Extension
from aurite.bin.dependencies import get_api_key

class DealershipExtension(Extension):
    def __call__(self, app):
        router = APIRouter(prefix="/dealership")

        @router.get("/drafts")
        async def get_drafts(api_key: str = Security(get_api_key)):
            manager = GmailManager()
            return await manager.get_all_drafts_async()

        app.include_router(router)
```

**Load extension:**

```bash
export AURITE_API_EXTENSIONS="src.api.dealership_extension.DealershipExtension"
```

**📚 Full guide:** See [API Extensions Detailed Guide](api_extensions_detailed_guide.md)

---

### MCP Servers

**When to use:**

- ✅ Provide reusable tools to agents
- ✅ Need tool discovery by LLMs
- ✅ Multi-agent tool sharing

**When NOT to use:**

- ❌ Simple CRUD (use API Extension)
- ❌ Need direct frontend access (use API Extension)
- ❌ One-off operations

**Key difference from API Extensions:**

| Aspect        | MCP Server          | API Extension      |
| ------------- | ------------------- | ------------------ |
| **Interface** | Tools for agents    | REST for clients   |
| **Discovery** | Runtime by agents   | Pre-defined        |
| **Docs**      | Docstrings for LLMs | OpenAPI for humans |
| **Overhead**  | Tool protocol       | Direct HTTP        |

**💡 Pro Tip:** Have BOTH for same functionality - MCP for agents, API for frontend!

**Development:** Follow steps 1-5 of 8-step workflow

**📚 References:**

- [MCP Server Config Schema](https://aurite-ai.github.io/aurite-agents/usage/config/mcp_server/)
- [Building MCP Server Tutorial](https://aurite-ai.github.io/aurite-agents/getting-started/tutorials/06_Building_Your_Own_MCP_Server/)

---

### Agents

**When to use:**

- Specialized assistant for specific tasks
- Combine multiple tools/servers
- Need stateful conversations

**File structure:**

```
config/agents/{feature}/
├── {name}.yml
└── {name}_eval.yml
```

**Development:** Follow steps 6-8 (requires MCP servers/workflows)

**📚 References:**

- [Agent Config Schema](https://aurite-ai.github.io/aurite-agents/usage/config/agent/)
- [Agents and Tools Tutorial](https://aurite-ai.github.io/aurite-agents/getting-started/tutorials/02_Agents_and_Tools/)

---

### Custom Workflows

**When to use:**

- Complex orchestration (conditionals, loops)
- Coordinate multiple agents programmatically
- Linear workflow too inflexible

**File structure:**

```
src/custom_workflows/{name}.py
config/custom_workflows/{feature}/
├── {name}.yml
└── {name}_eval.yml
```

**Development:**

- **Prerequisites:** Agents must be complete (steps 1-8) if orchestrating
- **Steps:** 1-2 (shared logic), 3-5 (workflow implementation)

**📚 References:**

- [Custom Workflow Config Schema](https://aurite-ai.github.io/aurite-agents/usage/config/custom_workflow/)
- [Workflows Tutorial](https://aurite-ai.github.io/aurite-agents/getting-started/tutorials/05_LLMs_Schemas_and_Workflows/)

---

## Testing Strategy

### Three Layers

1. **Unit Tests (pytest)** - Internal logic

   - `tests/servers/test_{name}_manager.py`
   - `pytest tests/servers/test_{name}_manager.py -v`

2. **Component Tests (evaluation)** - Interface

   - `config/mcp_servers/{name}/{name}_evaluation.yml`
   - `aurite test {name}_server_eval`

3. **Integration Tests (evaluation)** - End-to-end
   - `config/agents/{feature}/{name}_eval.yml`
   - `aurite test {name}_agent_eval`

### Testing Commands

```bash
# pytest
pytest tests/servers/test_excel_manager.py -v

# Evaluations
aurite test excel_server_eval
aurite test excel_server_eval --test-cases "basic_*"
aurite test license_agent_eval --debug
aurite test license_agent_eval --verbose
aurite test license_agent_eval --short
```

### Test Design

**✅ Good:**

```yaml
- name: sequential_tools
  input: "Get weather, then create plan based on it"
  expectations:
    - "Weather tool called first"
    - "Planning tool called second with weather data"
    - "Response includes both"
```

**❌ Poor:**

```yaml
- name: vague
  input: "Do something"
  expectations:
    - "It works" # Too vague!
```

**Key principles:**

- Write specific expectations
- Test tool flow, not internal math
- Include error scenarios
- Use descriptive names

---

## Best Practices

### Code Organization

**Separate manager from server:**

```python
# ✅ Good
# excel_manager.py - business logic
class ExcelManager:
    def read_sheet(self, file_path, sheet_name) -> List[Dict]:
        pass

# excel_server.py - thin wrapper
@mcp.tool()
async def read_excel_sheet(file_path: str, sheet_name: str) -> dict:
    manager = ExcelManager()
    data = manager.read_sheet(file_path, sheet_name)
    return {"success": True, "data": data}
```

**Clear naming:**

```python
# ✅ Good
async def read_excel_sheet(file_path: str, sheet_name: str) -> dict:

# ❌ Bad
async def read(f: str, s: str) -> dict:
```

**Structured responses:**

```python
# ✅ Good
return {"success": True, "data": rows, "row_count": len(rows)}

# ❌ Bad
return rows  # What about errors?
```

### Configuration

**Group by feature:**

```
config/agents/
├── 1_license_plate/
├── 2_sales_lead/
└── 3_service/
```

**Co-locate evaluations:**

```
config/mcp_servers/excel/
├── excel_server.yml
└── excel_server_evaluation.yml
```

### System Prompts

**✅ Specific:**

```yaml
system_prompt: |
  You are a license plate notification assistant for a dealership.
  Verify plate status in database before sending notifications.
  Include customer name and plate number in all notifications.
```

**❌ Generic:**

```yaml
system_prompt: "You are a helpful assistant."
```

### Error Handling

**In managers:**

```python
def read_sheet(self, file_path, sheet_name):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    # Process...
```

**In tools:**

```python
@mcp.tool()
async def read_excel_sheet(file_path: str, sheet_name: str) -> dict:
    try:
        manager = ExcelManager()
        data = manager.read_sheet(file_path, sheet_name)
        return {"success": True, "data": data}
    except FileNotFoundError as e:
        return {"success": False, "error": "file_not_found", "message": str(e)}
    except Exception as e:
        return {"success": False, "error": "unknown", "message": str(e)}
```

---

## Quick Reference

### File Locations

| Component       | Location                                          | Example                                                |
| --------------- | ------------------------------------------------- | ------------------------------------------------------ |
| MCP Manager     | `src/servers/{name}/{name}_manager.py`            | `src/servers/excel/excel_manager.py`                   |
| MCP Server      | `src/servers/{name}/{name}_server.py`             | `src/servers/excel/excel_server.py`                    |
| MCP Config      | `config/mcp_servers/{name}/{name}_config.yml`     | `config/mcp_servers/excel/excel_server.yml`            |
| MCP Eval        | `config/mcp_servers/{name}/{name}_evaluation.yml` | `config/mcp_servers/excel/excel_server_evaluation.yml` |
| Workflow        | `src/custom_workflows/{name}.py`                  | `src/custom_workflows/reminder.py`                     |
| Workflow Config | `config/custom_workflows/{feature}/{name}.yml`    | `config/custom_workflows/1_license/reminder.yml`       |
| Agent Config    | `config/agents/{feature}/{name}.yml`              | `config/agents/1_license/notification.yml`             |
| Agent Eval      | `config/agents/{feature}/{name}_eval.yml`         | `config/agents/1_license/notification_eval.yml`        |

### CLI Commands

```bash
# Testing
pytest tests/servers/test_excel_manager.py -v
aurite test excel_server_eval
aurite test license_agent_eval --debug

# Management
aurite list                    # All components
aurite list agents             # All agents
aurite show license_agent      # Show config
aurite run license_agent "msg"

# Development
aurite edit license_agent      # Edit in TUI
aurite api                     # Start API
aurite studio                  # Start Studio
```

### Development Checklist

**MCP Servers:**

- [ ] Create `{name}_manager.py`
- [ ] Write pytest tests
- [ ] All pytest pass
- [ ] Create `{name}_server.py`
- [ ] Create config YAML
- [ ] Create evaluation YAML
- [ ] `aurite test {name}_eval` pass
- [ ] Create agent using server
- [ ] Create agent evaluation
- [ ] `aurite test {agent}_eval` pass

**Custom Workflows (orchestrating agents):**

- [ ] **Prerequisites:** Complete steps 1-8 for all agents
- [ ] **Prerequisites:** All agent evals passing
- [ ] Create workflow class
- [ ] Implement `run()` with `executor.run_agent()`
- [ ] Create config YAML
- [ ] Create evaluation YAML
- [ ] `aurite test {workflow}_eval` pass

### Documentation Links

**Configuration:**

- [MCP Server](https://aurite-ai.github.io/aurite-agents/usage/config/mcp_server/)
- [Agent](https://aurite-ai.github.io/aurite-agents/usage/config/agent/)
- [Custom Workflow](https://aurite-ai.github.io/aurite-agents/usage/config/custom_workflow/)
- [Evaluation](https://aurite-ai.github.io/aurite-agents/usage/config/evaluation/)

**Tutorials:**

- [Building MCP Server](https://aurite-ai.github.io/aurite-agents/getting-started/tutorials/06_Building_Your_Own_MCP_Server/)
- [Workflows](https://aurite-ai.github.io/aurite-agents/getting-started/tutorials/05_LLMs_Schemas_and_Workflows/)
- [Agents and Tools](https://aurite-ai.github.io/aurite-agents/getting-started/tutorials/02_Agents_and_Tools/)

**Guides:**

- [CLI Reference](https://aurite-ai.github.io/aurite-agents/usage/cli_reference/)
- [API Reference](https://aurite-ai.github.io/aurite-agents/usage/api_reference/)
- [API Extensions](api_extensions_detailed_guide.md)

---

## Summary

**Key Takeaways for Copilots:**

1. **Start with decision tree** - Know what to build
2. **Follow 8-step workflow** - Systematic, test-driven
3. **Test at each layer** - Catch issues early
4. **Separate concerns** - Manager vs interface
5. **Development order** - Servers → Agents → Workflows

**Component guide:**

- **API Extensions** - Simple CRUD, frontend access
- **MCP Servers** - Agent tools, discovery
- **Agents** - Task assistants, stateful
- **Custom Workflows** - Orchestration, complex logic

**Remember:** Often have BOTH API extension AND MCP server for same functionality - one for frontend, one for agents.
