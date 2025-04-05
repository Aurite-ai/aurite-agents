# Agent Testing Infrastructure Implementation Plan

This document outlines a comprehensive plan for implementing a robust testing infrastructure for AI agents and workflows in the Aurite framework.

## Overview

The agent testing infrastructure will consist of several key components:

1. **Testing Environment Setup**: Configuring pytest properly
2. **Agent Evaluation Framework**: Building a specialized evaluation agent
3. **Rubric-Based Assessment**: Supporting configurable evaluation criteria
4. **Statistical Validation**: Averaging multiple evaluations for reliable results
5. **Integration with Workflow**: Making evaluation a standard part of agent development

## 1. Testing Environment Setup

### 1.1 Pytest Configuration

We'll update the existing `pyproject.toml` configuration to better support agent testing:

- Add test markers for agent evaluation
- Configure test output formatting
- Set up test data fixtures

### 1.2 Create conftest.py

Implement a conftest.py file to:

- Define common fixtures for testing agents
- Set up and tear down test environments
- Provide standard mock responses for LLM interactions

## 2. Agent Evaluation Framework

### 2.1 Evaluation Server

Enhance the initial `evaluation_server.py` to include:

- Tool for evaluating agent outputs against a rubric
- Tool for scoring agent performance
- Tool for generating detailed analysis reports
- Prompts for guiding the evaluation process

### 2.2 Evaluation Workflow

Create an `EvaluationWorkflow` that:

- Accepts an agent's output and a rubric as input
- Runs a thorough evaluation using various assessment methods
- Generates numerical scores and qualitative feedback
- Returns structured evaluation results

### 2.3 Core Components

1. **EvaluatorAgent**: The main agent responsible for conducting evaluations
2. **RubricProcessor**: Processes and validates rubric specifications
3. **ScoreAggregator**: Combines multiple evaluation scores
4. **ReportGenerator**: Creates detailed evaluation reports

## 3. Rubric-Based Assessment

### 3.1 Rubric Model

Define a structured rubric model that includes:

- Evaluation criteria with weights
- Scoring scales (e.g., 1-5, pass/fail)
- Category groupings (e.g., accuracy, coherence, etc.)
- Criterion-specific evaluation instructions

### 3.2 Standard Rubrics

Create standard rubrics for common agent types:

- Q&A Agent Rubric
- Planning Agent Rubric
- Analysis Agent Rubric
- Creative Agent Rubric

### 3.3 Custom Rubric Support

Support customization through:

- Rubric templates
- Criterion libraries
- Weight adjustments
- Custom scoring functions

## 4. Statistical Validation

### 4.1 Multi-Run Evaluation

Implement mechanisms for:

- Running the same evaluation multiple times
- Controlling randomness in evaluations
- Aggregating results across runs

### 4.2 Statistical Analysis

Add statistical analysis of results:

- Mean and median scores
- Standard deviation for reliability assessment
- Confidence intervals
- Outlier detection

### 4.3 Benchmarking

Create a benchmarking framework for:

- Comparing against baseline performance
- Tracking improvement over time
- Cross-model comparisons

## 5. Integration With Workflow System

### 5.1 Evaluation Step

Create a standard `EvaluationStep` that can be added to any workflow for:

- Self-assessment
- Output validation
- Quality control

### 5.2 Testing Utilities

Develop testing utilities for:

- Automated workflow testing
- Regression testing for agent behavior
- A/B testing of different agent configurations

### 5.3 CI/CD Integration

Plan for CI/CD integration to:

- Run agent evaluations on PRs
- Track evaluation metrics over time
- Prevent quality regression

## FastAPI Server Testing (Newman)

This section describes how to run integration tests against the main FastAPI server (`src/main.py`) using Newman and the Postman collection.

### Prerequisites

1.  **Node.js and npm:** Ensure Node.js and npm are installed.
2.  **Newman:** Install Newman globally: `npm install -g newman`
3.  **Running Server:** The FastAPI server must be running locally. Start it from the project root (`aurite-agents` directory):
    ```bash
    # Ensure required environment variables are set (e.g., in .env file)
    # API_KEY=your_api_key
    # HOST_CONFIG_PATH=path/to/your/host_config.json
    # ANTHROPIC_API_KEY=your_anthropic_key (if needed by host)
    # ... other env vars ...

    python aurite-mcp/src/main.py
    ```

### Running Tests

1.  **Navigate to Project Root:** Ensure your terminal is in the `aurite-agents` directory.
2.  **Create/Update Environment File:** Ensure the Postman environment file (`aurite-mcp/docs/testing/main_server.postman_environment.json`) exists and contains the correct `base_url` (usually `http://localhost:8000`) and the valid `api_key` matching the `API_KEY` environment variable used by the server.
3.  **Execute Newman:** Run the following command:
    ```bash
    newman run aurite-mcp/docs/testing/main_server.postman_collection.json -e aurite-mcp/docs/testing/main_server.postman_environment.json
    ```

Newman will execute the requests defined in the collection against the running server and report any test failures.

## Implementation Phases

### Phase 1: Core Infrastructure

1. Update pytest configuration in `pyproject.toml`
2. Create `conftest.py` with basic fixtures
3. Enhance `evaluation_server.py` with basic evaluation tools
4. Implement `evaluation_workflow.py` with core evaluation functionality
5. Create basic rubric models and standard rubrics

### Phase 2: Advanced Features

1. Add multi-run evaluation and statistical analysis
2. Implement advanced rubric processing
3. Create detailed report generation
4. Build evaluation step for workflow integration
5. Develop testing utilities for automated testing

### Phase 3: User Experience & Integration

1. Add CLI for running evaluations
2. Create visualization for evaluation results
3. Implement CI/CD integration
4. Build evaluation history and comparison tools
5. Develop documentation and usage examples

## Conclusion

This testing infrastructure will provide a robust framework for evaluating AI agents and workflows, ensuring:

- Consistent quality assessment
- Reproducible evaluation results
- Quantitative performance metrics
- Detailed qualitative feedback
- Continuous improvement tracking

By implementing this system, we will establish a solid foundation for agent development, enabling data-driven refinement of agent capabilities and behavior.
