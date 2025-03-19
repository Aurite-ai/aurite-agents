# Evaluation Workflow

The Evaluation Workflow provides a powerful system for assessing agent outputs using configurable rubrics. This workflow can be used to evaluate outputs from any workflow or agent in the system, making it a versatile tool for quality assessment, testing, and continuous improvement.

## Features

- **Flexible Rubric System**: Includes standard rubrics for various tasks (standard, QA, planning, analysis, creative) with the ability to create custom rubrics
- **Single and Multi-run Evaluation**: Support for both single evaluations and multi-run evaluations with statistical aggregation
- **Integration with Other Workflows**: Seamlessly evaluate outputs from any workflow or agent
- **Detailed Feedback**: Generate strengths, areas for improvement, and criterion-level assessments
- **Utility Functions**: Helper utilities for common evaluation scenarios

## Usage

### Basic Usage

```python
from src.agents.evaluation.evaluation_workflow import EvaluationWorkflow
from src.agents.evaluation.models import create_planning_rubric

# Register the workflow with the host
eval_workflow_name = await host.register_workflow(
    EvaluationWorkflow, name="evaluation_workflow"
)
evaluation_workflow = host.workflows.get_workflow(eval_workflow_name)

# Get a standard rubric
planning_rubric = create_planning_rubric().model_dump()

# Evaluate content
result = await evaluation_workflow.evaluate_agent(
    agent_output=plan_content,
    rubric=planning_rubric,
    detailed_feedback=True
)

# Access evaluation data
eval_data = result["data"]["evaluation_result"]
score = eval_data["score"]
strengths = eval_data["strengths"]
areas = eval_data["areas_for_improvement"]
```

### Multi-run Evaluation

```python
# Run multiple evaluations and aggregate results
result = await evaluation_workflow.evaluate_multi_run(
    agent_output=content,
    rubric=planning_rubric,
    num_runs=3
)

# Access aggregated results
agg_data = result["data"]["aggregated_result"]
mean_score = agg_data["mean_score"]
std_dev = agg_data["std_deviation"]
common_strengths = agg_data["common_strengths"]
```

### Using the Utility Functions

```python
from src.agents.evaluation.evaluation_utils import evaluate_workflow_output

# Evaluate any workflow output with configurable rubric
eval_result = await evaluate_workflow_output(
    evaluation_workflow=evaluation_workflow,
    workflow_name="planning",
    workflow_output=plan_content,
    rubric_type="planning",  # or "standard", "qa", "analysis", "creative"
    run_count=1  # Use >1 for multi-run evaluation
)

# Summarize results
from src.agents.evaluation.evaluation_utils import summarize_evaluation_result
summary = summarize_evaluation_result(eval_result)
```

## Available Rubrics

- **Standard Rubric**: General-purpose evaluation with balanced criteria
- **QA Rubric**: Specialized for question-answering tasks
- **Planning Rubric**: Designed for evaluating plans and roadmaps
- **Analysis Rubric**: Targeted at data analysis and reports
- **Creative Rubric**: For evaluating creative writing and content

## Integration with Other Workflows

The evaluation workflow is designed to be used with any other workflow in the system. This allows for:

1. Automated testing of workflow outputs
2. Quality control in production systems
3. Comparative analysis of different agents
4. Continuous improvement through feedback loops

See `tests/agents/evaluation/test_evaluation_workflow_integration.py` for an example of integration between the planning and evaluation workflows.

## Customization

You can create custom rubrics by following the model structure in `models.py`. The key components are:

1. **Criteria**: Specific aspects to evaluate with weights that sum to 1.0
2. **Scoring Scale**: Min, max, and increment values
3. **Scoring Guidelines**: Description of what each score level means for each criterion

## Testing

Unit tests are available in `tests/agents/evaluation/test_evaluation_workflow.py` and integration tests in `tests/agents/evaluation/test_evaluation_workflow_integration.py`.