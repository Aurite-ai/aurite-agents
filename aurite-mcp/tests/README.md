# Aurite Agent Testing Guide

This document explains how to use the testing infrastructure to evaluate Aurite agents, workflows, and MCP servers.

## Introduction

The Aurite testing framework allows you to:

1. Evaluate agent outputs against configurable rubrics
2. Run multiple evaluations to get statistically significant results
3. Generate detailed feedback for improving agent performance
4. Test workflows end-to-end with mock dependencies
5. Test MCP servers for tool, prompt, and resource functionality
6. Verify server configurations and component accessibility

## MCP Server Testing

### Testing MCP Server Components

The framework includes a standardized way to test MCP servers for accessibility and functionality of their components:

```python
import pytest
from tests.servers.test_mcp_functional import MCPServerTester

# Path to the server
SERVER_PATH = Path("src/your_module/your_server.py")

@pytest.mark.asyncio
async def test_server_tools(test_mcp_host):
    """Test that the server's tools are accessible."""
    # Create a tester with the JSON-configured host
    tester = MCPServerTester(SERVER_PATH, host=test_mcp_host)
    
    # Discover components
    components = await tester.discover_components()
    tools = components["tools"]
    
    # Verify expected tools exist
    expected_tools = ["your_tool_name", "another_tool"]
    for tool_name in expected_tools:
        tool_exists = any(t["name"] == tool_name for t in tools)
        assert tool_exists, f"Expected tool '{tool_name}' not found"
```

### Testing Prompts and Resources

Similar tests for prompts and resources:

```python
@pytest.mark.asyncio
async def test_server_prompts(test_mcp_host):
    """Test that the server's prompts are accessible."""
    tester = MCPServerTester(SERVER_PATH, host=test_mcp_host)
    
    # Discover components
    components = await tester.discover_components()
    prompts = components["prompts"]
    
    # Verify expected prompts exist
    expected_prompts = ["your_prompt_name"]
    for prompt_name in expected_prompts:
        prompt_exists = any(p.name == prompt_name for p in prompts)
        assert prompt_exists, f"Expected prompt '{prompt_name}' not found"

@pytest.mark.asyncio
async def test_server_resources(test_mcp_host):
    """Test that the server's resources are accessible."""
    tester = MCPServerTester(SERVER_PATH, host=test_mcp_host)
    
    # Discover and verify resource capabilities
    components = await tester.discover_components()
    
    # Instead of direct client config access, verify through tool functionality
    client_tools = [t for t in tester.tools if t["name"] in ["your_expected_tools"]]
    assert len(client_tools) > 0, "No tools found for resource verification"
```

### Automatic Server Discovery

The framework includes automatic discovery of all MCP servers listed in configuration:

```python
@pytest.mark.parametrize("server_path", get_all_server_paths())
@pytest.mark.asyncio
async def test_all_mcp_servers(server_path, test_mcp_host):
    """Run functional tests on each MCP server."""
    results = await run_mcp_server_test(server_path, shared_host=test_mcp_host)
    
    # Make assertions
    assert results["tools"] or results["prompts"] or results["resources"]["found"]
```

### Host Configuration for Testing

The testing framework uses the new configuration system to initialize a shared host for all tests:

```python
@pytest.fixture(scope="function")
async def test_mcp_host():
    """Create a real MCPHost for testing using the JSON configuration."""
    # Load host configuration from JSON
    host = MCPHost(config_name="aurite_host")
    
    try:
        await host.initialize()
        yield host
    finally:
        await host.shutdown()
```

## Agent Testing

### Basic Agent Testing

To test a basic agent, follow these steps:

```python
import pytest
from src.agents.evaluation.evaluation_workflow import EvaluationWorkflow
from src.agents.planning.planning_workflow import PlanningWorkflow

@pytest.mark.asyncio
async def test_planning_agent(mock_tool_manager, mock_mcp_host):
    # 1. Set up the agent you want to test
    planning_agent = PlanningWorkflow(tool_manager=mock_tool_manager, host=mock_mcp_host)
    await planning_agent.initialize()
    
    # 2. Set up the evaluation agent
    evaluator = EvaluationWorkflow(tool_manager=mock_tool_manager, host=mock_mcp_host)
    await evaluator.initialize()
    
    # 3. Execute the agent under test
    test_task = "Create a marketing plan for a new product launch"
    agent_result = await planning_agent.create_plan(
        task=test_task,
        plan_name="test_plan"
    )
    
    # 4. Extract the agent's output
    agent_output = agent_result["data"]["plan_content"]
    
    # 5. Evaluate the output using an appropriate rubric
    eval_result = await evaluator.evaluate_agent(
        agent_output=agent_output,
        rubric="planning",  # Use planning-specific rubric
        detailed_feedback=True
    )
    
    # 6. Verify evaluation meets expectations
    assert eval_result["success"] is True
    evaluation = eval_result["data"]["evaluation_result"]
    assert evaluation["score"] >= 3.5  # Require minimum quality score
    
    # 7. You can also check specific criteria
    assert evaluation["criterion_scores"]["feasibility"]["score"] >= 3.0
```

### Multi-Run Evaluation

For more statistically reliable results, use multi-run evaluation:

```python
# Run the evaluation multiple times and aggregate results
multi_run_result = await evaluator.evaluate_multi_run(
    agent_output=agent_output,
    rubric="planning",
    num_runs=5  # Run 5 evaluations
)

# Check aggregated statistics
aggregated = multi_run_result["data"]["aggregated_result"]
assert aggregated["mean_score"] >= 3.5
assert aggregated["std_deviation"] < 0.5  # Ensure consistency
```

## Available Rubrics

The framework includes several pre-configured rubrics:

1. **Standard Rubric**: General-purpose evaluation (accuracy, relevance, coherence, completeness)
2. **QA Rubric**: For question-answering agents (accuracy, comprehensiveness, clarity, directness)
3. **Planning Rubric**: For planning agents (completeness, feasibility, structure, specificity, adaptability)
4. **Analysis Rubric**: For data analysis agents (accuracy, depth, methodology, communication)
5. **Creative Rubric**: For creative writing agents (originality, coherence, engagement, technical quality)

## Creating Custom Rubrics

For specialized agent testing, you can create custom rubrics:

```python
from src.agents.evaluation.models import (
    EvaluationRubric, 
    EvaluationCriterion,
    ScoringScale
)

# Define a custom rubric
custom_rubric = EvaluationRubric(
    name="api_integration_rubric",
    description="Evaluates API integration capabilities",
    criteria={
        "endpoint_handling": EvaluationCriterion(
            description="Correctly handles API endpoints",
            weight=0.3,
            scoring={
                "1": "Incorrect endpoint usage",
                "2": "Multiple endpoint errors",
                "3": "Minor endpoint issues",
                "4": "Correct endpoint usage with minor improvements possible",
                "5": "Perfect endpoint usage"
            }
        ),
        "authentication": EvaluationCriterion(
            description="Properly implements authentication",
            weight=0.3,
            scoring={
                "1": "No authentication implemented",
                "2": "Authentication with major security issues",
                "3": "Authentication with minor issues",
                "4": "Proper authentication with minor improvements possible",
                "5": "Perfect secure authentication"
            }
        ),
        "error_handling": EvaluationCriterion(
            description="Handles API errors gracefully",
            weight=0.2,
            scoring={
                "1": "No error handling",
                "2": "Basic error catching without proper handling",
                "3": "Adequate error handling for common cases",
                "4": "Comprehensive error handling",
                "5": "Perfect error handling with recovery strategies"
            }
        ),
        "response_processing": EvaluationCriterion(
            description="Correctly processes API responses",
            weight=0.2,
            scoring={
                "1": "Fails to process responses",
                "2": "Processes only basic responses",
                "3": "Adequate response processing",
                "4": "Thorough response processing",
                "5": "Perfect response processing with edge cases"
            }
        )
    },
    scale=ScoringScale(min=1, max=5, increment=1),
    passing_threshold=3.0
)

# Use the custom rubric in evaluation
eval_result = await evaluator.evaluate_agent(
    agent_output=agent_output,
    rubric=custom_rubric.model_dump()
)
```

## Testing Workflows

To test a complete workflow:

```python
@pytest.mark.asyncio
async def test_data_analysis_workflow(mock_tool_manager, mock_mcp_host):
    # 1. Set up the workflow to test
    workflow = DataAnalysisWorkflow(tool_manager=mock_tool_manager, host=mock_mcp_host)
    await workflow.initialize()
    
    # 2. Create input data
    input_data = {
        "dataset": "sales_data.csv",
        "analysis_type": "trend",
        "time_period": "2024-Q1"
    }
    
    # 3. Execute the workflow
    result_context = await workflow.execute(input_data)
    
    # 4. Verify workflow completion
    assert result_context.is_complete()
    assert all(
        result.status != StepStatus.FAILED 
        for result in result_context.step_results.values()
    )
    
    # 5. Extract workflow outputs for evaluation
    analysis_result = result_context.get("analysis_result")
    
    # 6. Evaluate the workflow output
    evaluator = EvaluationWorkflow(tool_manager=mock_tool_manager, host=mock_mcp_host)
    await evaluator.initialize()
    
    eval_result = await evaluator.evaluate_agent(
        agent_output=analysis_result,
        rubric="analysis"
    )
    
    # 7. Check evaluation results
    assert eval_result["data"]["evaluation_result"]["score"] >= 4.0
```

## Running Tests

Run tests using pytest:

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/agents/test_planning_workflow.py

# Run tests for a specific server
python -m pytest tests/servers/test_planning_server.py

# Run all server tests
python -m pytest tests/servers/

# Run with verbose output
python -m pytest -v
```

## Interpreting Evaluation Results

Evaluation results include:

1. **Overall Score**: Weighted average across all criteria (1-5 scale)
2. **Criterion Scores**: Individual scores for each criterion
3. **Justifications**: Explanations for each score
4. **Strengths**: Identified positive aspects
5. **Areas for Improvement**: Suggested enhancements
6. **Summary Feedback**: Overall assessment

For multi-run evaluations, additional statistics include:
- Mean, median, min, and max scores
- Standard deviation of scores
- Common strengths and areas for improvement

## Best Practices

### For Agent Testing

1. **Use Domain-Specific Rubrics**: Choose rubrics that match your agent's purpose
2. **Run Multiple Evaluations**: Use `evaluate_multi_run` for statistical reliability
3. **Test Edge Cases**: Include challenging inputs in your test suite
4. **Evolve Rubrics**: Refine rubrics as your agents improve
5. **Combine with Unit Tests**: Use traditional unit tests for specific functionalities

### For MCP Server Testing

1. **Test Component Accessibility**: Verify tools, prompts, and resources are properly registered
2. **Use JSON Configurations**: Leverage the configuration system for host setup
3. **Separate Discovery from Execution**: First verify components exist, then test their functionality
4. **Test with Realistic Arguments**: Use representative arguments when testing tools
5. **Test Resources through Tools**: Verify resource access by using tools that access them
6. **Test with Shared Host**: Use the `test_mcp_host` fixture for consistent testing

## Testing Architecture

The testing framework uses a layered approach:

1. **Shared Host Setup**: A common host is initialized using the configuration system
2. **Component Discovery**: Server components are discovered and validated
3. **Functional Testing**: Tool and prompt functionality is tested with representative inputs
4. **Integration Testing**: Resources are tested through tool execution
5. **Automatic Testing**: All registered servers are automatically discovered and tested

The tests leverage the same JSON configuration files used in production, ensuring that the tests reflect the actual behavior of the system.