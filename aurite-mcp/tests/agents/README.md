# Agent and Workflow Testing

This directory contains tests for the Aurite agents and workflows, focusing on testing with the JSON configuration system.

## Testing Infrastructure

The tests in this directory use the `test_mcp_host` fixture from `conftest.py`, which initializes a full MCPHost instance from the JSON configuration system. This fixture provides:

- A fully configured host with servers, tools, prompts, and resources loaded from JSON configuration
- Access to tools, prompts, and resources through the host's managers
- Proper initialization and shutdown of the host components
- Ability to register and test workflows with the host system

## Test Organization

The tests are organized by agent/workflow type:

- `planning/` - Tests for the planning workflow and related components
- `evaluation/` - Tests for the evaluation workflow and related components
- `test_workflow_manager.py` - Tests for the workflow manager system

## Writing Workflow Tests

When writing tests for workflows with the new testing infrastructure, follow these best practices:

1. **Use the `test_mcp_host` fixture**: This provides a fully initialized host with access to all registered components
   ```python
   @pytest.mark.asyncio
   async def test_my_workflow(test_mcp_host):
       # Test using the host...
   ```

2. **Test workflow registration**: Ensure workflows can be registered with the host
   ```python
   workflow_name = await test_mcp_host.register_workflow(MyWorkflow)
   assert test_mcp_host.workflows.has_workflow(workflow_name)
   ```

3. **Test workflow execution through the host**: Use the workflow manager to execute workflows
   ```python
   result_context = await test_mcp_host.workflows.execute_workflow(
       workflow_name=workflow_name,
       input_data=input_data
   )
   ```

4. **Mock external tool calls**: To avoid calling actual external systems or LLMs
   ```python
   with patch.object(test_mcp_host.tools, "execute_tool") as mock_tool:
       mock_tool.return_value = [types.TextContent(type="text", text="Result")]
       # Execute workflow...
   ```

5. **Check for tool availability**: Skip tests that require tools not available in the current configuration
   ```python
   if not await test_mcp_host.tools.has_tool("required_tool"):
       pytest.skip("required_tool not available in test host")
   ```

6. **Check step status**: Verify each step completed as expected
   ```python
   assert result_context.step_results["step_name"].status == StepStatus.COMPLETED
   ```

7. **Verify outputs**: Check that the context contains the expected outputs
   ```python
   data_dict = result_context.get_data_dict()
   assert "expected_key" in data_dict
   ```

## Writing Tests for Specific Steps

When testing individual workflow steps, create the step with the proper configuration and provide it with a context connected to the host:

```python
# Create the step
step = MyWorkflowStep(client_id="my_client")

# Create a context with required inputs
context = AgentContext()
context.set("input_key", "input_value")

# Attach the host to the context
context.host = test_mcp_host

# Execute the step
result = await step.execute(context)
```

## Handling Errors in Tests

Workflow tests should verify error handling. Test that steps and workflows handle errors gracefully:

```python
# Mock a tool or method to raise an error
with patch.object(test_mcp_host.tools, "execute_tool") as mock_tool:
    mock_tool.side_effect = ValueError("Test error")
    
    # Execute workflow with expected error
    result_context = await workflow.execute(input_data)
    
    # Verify step failed but didn't crash the workflow
    assert result_context.step_results["step_name"].status == StepStatus.FAILED
    assert "Test error" in str(result_context.step_results["step_name"].error)
```