# Planning Module

This module provides a complete implementation of a planning system using FastMCP and workflow patterns.

## Components

### Planning Server (planning_server.py)

A FastMCP server that provides:
- Tool for saving plans to disk (`save_plan`)
- Tool for listing available plans (`list_plans`)
- Prompt for structured plan creation (`planning_prompt`)
- Prompt for plan analysis (`plan_analysis_prompt`)
- Resource endpoint for retrieving plans (`planning://plan/{plan_name}`)

### Planning Workflow (planning_workflow.py)

A workflow implementation that demonstrates:
- Using prompt-based execution for AI-powered plan creation
- Tool-based plan saving
- Plan analysis
- Plan listing with filtering

The workflow includes several specialized steps:
- `PlanCreationStep`: Creates a plan using AI via the planning prompt
- `PlanSaveStep`: Saves the created plan using the save_plan tool
- `PlanAnalysisStep`: Analyzes an existing plan using the plan analysis prompt
- `PlanListStep`: Lists available plans, optionally filtered by tag

### Test Files

- **Unit Tests** (`tests/agents/test_planning_workflow.py`): Comprehensive tests for all components
- **Direct MCP Test** (`test_planning_direct.py`): Tests direct connection to the planning server
- **Host Integration Test** (`test_planning_workflow.py`): Tests integration with the host system

## Usage

### Create a Plan

```python
from src.agents.planning import PlanningWorkflow

# Initialize workflow with host and tool_manager
workflow = PlanningWorkflow(tool_manager=host.tools, host=host)
await workflow.initialize()

# Create a plan
result = await workflow.create_plan(
    task="Design and implement a note-taking application",
    plan_name="note_app_project",
    timeframe="1 month",
    resources=["Frontend developer", "Backend developer", "UI/UX designer"]
)

# Access the plan content
plan_content = result["data"]["plan_content"]
plan_path = result["data"]["plan_path"]
```

### Analyze a Plan

```python
# Analyze an existing plan
analysis_result = await workflow.analyze_plan("note_app_project")

# Access the analysis
analysis_report = analysis_result["data"]["analysis_report"]
```

### List Plans

```python
# List all plans
list_result = await workflow.list_plans()

# List plans filtered by tag
filtered_result = await workflow.list_plans(filter_tag="frontend")
```

## Implementation Notes

- All tools and prompts are implemented using FastMCP decorators
- Plans are stored in the `plans/` directory as text files with JSON metadata
- The module provides in-memory caching for faster access to plans
- The workflow supports conditional execution and error handling
- All components are thoroughly tested at different levels of integration