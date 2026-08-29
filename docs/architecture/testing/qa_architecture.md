# QA Testing Architecture

**Last Updated:** September 30, 2025
**Version:** 2.0 (Post-Refactoring)

## Overview

The QA (Quality Assurance) testing system in Aurite Agents provides comprehensive evaluation capabilities for agents, workflows, and MCP servers. The architecture follows a unified design with clear separation of concerns, enabling efficient testing with LLM-as-judge evaluation, multi-level caching, and parallel execution.

## Core Design Principles

1. **Single Responsibility Principle (SRP)**: Each class has one well-defined purpose
2. **Unified Orchestration**: Single QAEngine handles all component types
3. **Dependency Injection**: Clean integration with FastAPI and SessionManager
4. **Component-Agnostic Testing**: Same testing framework works for all component types

## Architecture Components

### 1. QAEngine (`qa_engine.py`)

**Purpose:** Unified orchestration and execution of QA evaluations

**Responsibilities:**

- Process evaluation requests (single and multi-component)
- Execute components across all evaluation modes
- Manage parallel test execution with rate limiting
- Integrate with QASessionManager for caching
- Analyze outputs using LLM-as-judge
- Pre-register MCP servers to avoid race conditions

**Key Methods:**

```python
# Public Interface
async def evaluate_component(request: EvaluationConfig, executor: AuriteEngine) -> Dict[str, QAEvaluationResult]
async def evaluate_by_config_id(evaluation_config_id: str, executor: AuriteEngine, test_cases_filter: str) -> Dict[str, QAEvaluationResult]

# Core Evaluation
async def _test_component(request: EvaluationConfig, executor: AuriteEngine) -> QAEvaluationResult
async def _evaluate_single_case(case: EvaluationCase, llm_client: LiteLLMClient, request: EvaluationConfig, executor: AuriteEngine) -> CaseEvaluationResult
async def _evaluate_multiple_components(request: EvaluationConfig, executor: AuriteEngine) -> Dict[str, QAEvaluationResult]

# Business Logic
async def _execute_component(case: EvaluationCase, request: EvaluationConfig, executor: AuriteEngine) -> Any
async def _analyze_expectations(case: EvaluationCase, output: Any, llm_client: LiteLLMClient, component_context: Dict) -> ExpectationAnalysisResult

# Helpers
async def _get_llm_client(request: EvaluationConfig, executor: AuriteEngine) -> LiteLLMClient
async def _pre_register_mcp_servers(request: EvaluationConfig, executor: AuriteEngine) -> None
def aggregate_scores(results: List[CaseEvaluationResult]) -> float
```

### 2. QASessionManager (`qa_session_manager.py`)

**Purpose:** Dedicated cache and session management for QA operations

**Responsibilities:**

- Generate deterministic cache keys
- Store and retrieve cached case results
- Store and retrieve cached evaluation results
- Persist test results to SessionManager
- Handle cache expiration (TTL)

**Key Methods:**

```python
# Cache Key Generation
def generate_case_cache_key(case_input: str, component_config: Dict, evaluation_config_id: str, review_llm: str, expectations: List[str]) -> str
def generate_evaluation_cache_key(evaluation_config_id: str, test_cases: List, review_llm: str) -> str

# Case-Level Cache Operations
async def get_cached_case_result(cache_key: str, cache_ttl: int) -> Optional[CaseEvaluationResult]
async def store_cached_case_result(cache_key: str, result: CaseEvaluationResult) -> bool

# Evaluation-Level Cache Operations
async def get_cached_evaluation_result(cache_key: str, cache_ttl: int) -> Optional[QAEvaluationResult]
async def store_cached_evaluation_result(cache_key: str, result: QAEvaluationResult) -> bool

# Result Persistence
def save_test_result(result_data: Dict, config_id: str) -> Optional[str]
```

### 3. Utility Functions (`qa_utils.py`)

**Purpose:** Pure utility functions with no side effects

**Functions:**

- `validate_schema(output: Any, expected_schema: Dict) -> SchemaValidationResult` - JSON schema validation
- `clean_llm_output(output: str) -> str` - Extract JSON from LLM responses
- `format_agent_conversation_history(result) -> str` - Format agent conversation for evaluation

### 4. Data Models (`qa_models.py`)

**Purpose:** Define evaluation results and related data structures

**Models:**

- `QAEvaluationResult` - Complete evaluation results for a component
- `CaseEvaluationResult` - Results for a single test case
- `ExpectationAnalysisResult` - LLM analysis of expectations
- `SchemaValidationResult` - Schema validation results

## Component Interactions

```
┌─────────────────────────────────────────────────────────┐
│                    Testing Routes                        │
│              (testing_routes.py)                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ FastAPI Dependency Injection
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌──────────┐  ┌─────────────┐  ┌────────────┐
│ConfigMgr │  │SessionMgr   │  │AuriteEngine│
└────┬─────┘  └──────┬──────┘  └─────┬──────┘
     │               │                │
     │               │                │
     │       ┌───────▼────────┐       │
     │       │QASessionManager│       │
     │       │  (caching)     │       │
     │       └───────┬────────┘       │
     │               │                │
     └───────────────┼────────────────┘
                     │
                     ▼
            ┌────────────────┐
            │    QAEngine    │
            │  (orchestrator)│
            └────────┬───────┘
                     │
       ┌─────────────┼─────────────┐
       │             │             │
       ▼             ▼             ▼
  ┌─────────┐  ┌─────────┐  ┌──────────┐
  │Component│  │  LLM    │  │  Cache   │
  │Execution│  │Analysis │  │Operations│
  └─────────┘  └─────────┘  └──────────┘
```

## Evaluation Modes

The QA system supports three distinct evaluation modes:

### 1. Aurite Mode (`mode: "aurite"`)

**Purpose:** Test Aurite framework components using built-in execution

**Characteristics:**

- Uses AuriteEngine to execute agents, workflows, or MCP servers
- Automatic MCP server pre-registration
- Full integration with framework features

**Example:**

```yaml
name: weather_agent_eval
type: evaluation
mode: aurite
component_type: agent
component_refs: ["Weather Agent"]
```

### 2. Manual Mode (`mode: "manual"`)

**Purpose:** Evaluate pre-recorded outputs without execution

**Characteristics:**

- Test cases include `output` field with pre-recorded responses
- No component execution occurs
- Useful for regression testing and comparison

**Example:**

```yaml
name: manual_eval
type: evaluation
mode: manual
test_cases:
  - input: "What's the weather?"
    output: "The weather is sunny, 72°F"
    expectations: ["Contains temperature"]
```

### 3. Function Mode (`mode: "function"`)

**Purpose:** Use custom execution functions for framework-agnostic testing

**Characteristics:**

- Specify custom Python function via `run_agent` parameter
- Full control over component execution
- Enables testing of non-Aurite components

**Example:**

```yaml
name: custom_eval
type: evaluation
mode: function
run_agent: "path/to/custom_runner.py"
run_agent_kwargs:
  api_key: "..."
```

**Mode Resolution:** If `mode` is not explicitly set, it's auto-detected:

- Has `output` in test cases → Manual mode
- Has `run_agent` → Function mode
- Has `component_refs` → Aurite mode

## Performance Features

### 1. Multi-Level Caching

**Case-Level Cache:**

- Individual test case results cached based on input, config, and expectations
- Enables fast re-runs when only some tests change
- TTL-based expiration (default: 1 hour)

**Evaluation-Level Cache:**

- Complete evaluation results cached
- Used when entire configuration is unchanged
- Significantly faster than individual case lookup

**Cache Key Generation:**

```python
# Case-level: Hash of input + config + expectations
qa_case_{md5(input+config+expectations)}

# Evaluation-level: Hash of config ID + all test cases
qa_eval_{md5(config_id+test_cases)}
```

### 2. Rate Limiting & Parallel Execution

**Semaphore-Based Concurrency:**

- Controls max concurrent test execution (default: 3)
- Prevents API rate limit errors
- Configurable via `max_concurrent_tests`

**Exponential Backoff Retry:**

- Automatic retry on rate limit errors
- Exponential delay: `base_delay * (2 ** attempt)`
- Random jitter to prevent thundering herd
- Configurable retry count and base delay

**Configuration:**

```yaml
max_concurrent_tests: 3 # Max parallel tests
rate_limit_retry_count: 3 # Retry attempts
rate_limit_base_delay: 1.0 # Base delay in seconds
```

### 3. MCP Server Pre-Registration

**Problem:** Parallel test execution can cause race conditions when multiple tests try to register the same MCP server simultaneously.

**Solution:** Pre-register all required MCP servers before starting parallel execution:

```python
async def _pre_register_mcp_servers(request: EvaluationConfig, executor: AuriteEngine):
    # Extract MCP server names from agent config or direct refs
    # Register each server once before tests run
    # Track failed servers to prevent retry attempts
```

## API Integration

### Dependency Injection

The QAEngine is provided to API routes via FastAPI dependency injection:

```python
# dependencies.py
async def get_qa_engine(
    config_manager: ConfigManager = Depends(get_config_manager),
    session_manager: SessionManager = Depends(get_session_manager),
) -> QAEngine:
    qa_session_manager = QASessionManager(session_manager=session_manager)
    return QAEngine(
        config_manager=config_manager,
        session_manager=qa_session_manager
    )

# testing_routes.py
@router.post("/evaluate")
async def evaluate_component(
    request: EvaluationConfig,
    qa_engine: QAEngine = Depends(get_qa_engine),
    engine: AuriteEngine = Depends(get_execution_facade),
):
    results = await qa_engine.evaluate_component(request, engine)
    return {name: result.model_dump() for name, result in results.items()}
```

### Endpoints

- `POST /testing/evaluate` - Evaluate with inline configuration
- `POST /testing/evaluate/{config_id}` - Evaluate using saved configuration
- `GET /testing/qa/results/{result_id}` - Retrieve specific test result
- `GET /testing/qa/results` - List test results with filtering

## Design Decisions

### Why Merge QAEngine and ComponentQATester?

**Problem:** Originally had QAEngine (orchestrator) and ComponentQATester (executor) as separate classes, assuming multiple testers would be needed for different component types.

**Reality:** QA evaluation with LLM-as-judge is component-agnostic—all components are tested the same way (blackbox testing).

**Solution:** Merged into single QAEngine class with:

- Public interface methods for API/CLI integration
- Core evaluation logic for test execution
- Business logic for component execution and analysis
- Helper methods for LLM clients and MCP server management

**Benefits:**

- Eliminated unnecessary delegation
- Clearer code flow
- Easier to understand and maintain
- Better performance (fewer indirections)

### Why Create QASessionManager?

**Problem:** Cache management logic was scattered across multiple files (qa_utils.py, component_qa_tester.py).

**Solution:** Dedicated QASessionManager class following SRP:

- All cache operations in one place
- Clear interface for cache key generation
- Wraps SessionManager for QA-specific operations
- Easy to test and maintain

**Benefits:**

- Single responsibility (cache management)
- Reusable across different QA components
- Testable in isolation
- Clear dependency injection path

### Why Simplify qa_utils.py?

**Problem:** Originally 750+ lines mixing cache logic, component execution, LLM analysis, and true utilities.

**Solution:** Reduced to only pure utility functions (150 lines):

- `validate_schema()` - JSON schema validation
- `clean_llm_output()` - Text processing
- `format_agent_conversation_history()` - Output formatting

**Benefits:**

- Clear separation between utilities and business logic
- No side effects or state management
- Easy to test
- Obvious what belongs where

## Evolution History

### Version 1.0 (Pre-Refactoring)

- 3 models: EvaluationConfig, EvaluationRequest, ComponentQAConfig
- 3 classes: QAEngine (orchestrator), ComponentQATester (executor), utilities scattered
- Implicit mode handling via conditional logic
- 750+ lines of mixed-concern utilities

### Version 2.0 (Post-Refactoring)

- 1 model: EvaluationConfig (with explicit mode field)
- 2 classes: QAEngine (unified), QASessionManager (dedicated caching)
- 3 pure utility functions
- Explicit mode handling with auto-detection fallback
- ~1350 lines total, well-organized by responsibility

**Improvements:**

- ✅ 66% reduction in models (3 → 1)
- ✅ Single source of truth for evaluation logic
- ✅ Clear separation of concerns (SRP)
- ✅ Better testability
- ✅ Easier to maintain and extend
- ✅ Improved performance (fewer indirections)

## Testing Strategy

### Unit Tests

- Test individual methods in isolation
- Mock dependencies (SessionManager, AuriteEngine)
- Test cache key generation logic
- Test mode resolution

### Integration Tests

- Test complete evaluation flows
- Test all three evaluation modes
- Test caching behavior
- Test rate limiting and parallel execution
- Location: `tests/integration/testing/test_qa_evaluation_config.py`

### Functional Tests

- End-to-end tests with real components
- CLI testing (`aurite test <config_name>`)
- API endpoint testing

## Future Enhancements

Potential areas for expansion:

1. **Advanced Metrics**: Beyond pass/fail, track latency, token usage, cost
2. **Benchmark Comparisons**: Compare multiple components side-by-side
3. **Trend Analysis**: Track evaluation scores over time
4. **Custom Evaluators**: Plugin system for domain-specific evaluation logic
5. **Streaming Support**: Real-time evaluation results for long-running tests
6. **Report Generation**: Automated HTML/PDF reports with visualizations

## Related Documentation

- **User Guide:** `/docs/usage/config/evaluation.md` - How to configure evaluations
- **API Reference:** `/docs/usage/api_reference.md` - Testing API endpoints
- **CLI Reference:** `/docs/usage/cli_reference.md` - `aurite test` command
- **SessionManager:** `/docs/architecture/flow/session_management_flow.md` - Session management details
