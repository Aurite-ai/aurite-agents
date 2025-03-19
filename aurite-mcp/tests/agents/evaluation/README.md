# Evaluation Workflow Tests

This directory contains tests for the Evaluation Workflow component of the Aurite MCP framework.

## Current Status

The tests are currently structured and ready, but are **skipped** due to initialization compatibility issues between the `EvaluationWorkflow` class and the testing framework.

## Known Issues

1. **Initialization Parameter Conflict**: The `EvaluationWorkflow.__init__` method and its parent `BaseWorkflow.__init__` method have conflicting parameter usage, which causes a "multiple values for argument 'host'" error when trying to run tests.

2. **Parameter Naming Inconsistency**: In `EvaluationWorkflow`, the `tool_manager` is being passed as the first positional argument to `BaseWorkflow.__init__`, which expects a `host` parameter first. This leads to parameter confusion.

## Implementation TODO

To make these tests work, one of the following solutions needs to be implemented:

1. **Fix `EvaluationWorkflow.__init__`** - The initialization method should be updated to properly handle the parameters and pass them correctly to the parent class.

2. **Create a Test Adapter** - A test-specific adapter for the workflow could be created to handle the initialization properly.

3. **Update Test Framework** - The testing approach could be modified to accommodate the current workflow initialization pattern.

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