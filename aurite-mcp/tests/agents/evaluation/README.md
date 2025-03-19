# Evaluation Workflow Tests

This directory contains tests for the Evaluation Workflow component of the Aurite MCP framework.

## Current Status

✅ The tests are now working and passing! The initialization compatibility issues have been resolved.

## Implementation Changes

The `EvaluationWorkflow` class has been updated with the following changes:

1. **Fixed `EvaluationWorkflow.__init__` Method**: The initialization method now properly matches the BaseWorkflow parameter signature:

```python
def __init__(
    self, 
    host,
    name: str = "evaluation_workflow", 
    client_config: Optional[ClientConfig] = None,
    workflow_config: Optional[Dict[str, Any]] = None
):
    """Initialize the evaluation workflow."""
    super().__init__(host=host, name=name, client_config=client_config, workflow_config=workflow_config)
```

2. **Updated Tool Execution**: The workflow steps now use `context.host.tools` instead of `context.tool_manager` to execute tools, which is compatible with the host-based testing framework.

## Testing Strategy

These tests follow the same pattern as the Planning Workflow tests:

1. Each test uses the `test_mcp_host` fixture from `conftest.py` to create a test environment.
2. Tests are isolated and mock API calls and tool executions to avoid external dependencies.
3. Tests cover workflow initialization, registration, step execution, and error handling.
4. Convenience methods are tested separately to verify their behavior.

## Running the Tests

When the initialization issues are resolved, tests can be run with:

```bash
cd aurite-mcp
python -m pytest tests/agents/evaluation/test_evaluation_workflow.py -v
```

To skip specific tests:

```bash
python -m pytest tests/agents/evaluation/test_evaluation_workflow.py -v -k "not test_name_to_skip"
```