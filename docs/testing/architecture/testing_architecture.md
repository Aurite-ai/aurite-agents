# Testing Implementation Architecture

## Overview

The Aurite Testing Framework implements a three-level orchestration architecture that provides clear separation of concerns while enabling comprehensive testing across Quality Assurance (QA) and Security domains. This architecture supports both framework-agnostic and framework-specific testing, allowing validation of AI components independent of the specific agent framework being used.

The framework integrates seamlessly with Aurite's existing configuration system and maintains a clean, focused structure that prioritizes the most essential components while keeping specialized features appropriately organized.

## Final File Structure

```
src/aurite/testing/
├── __init__.py
├── README.md
├── test_engine.py               # Level 1: Main orchestrator
├── test_models.py               # Shared models between QA and Security
│
├── cache/                       # Test result caching
│   ├── __init__.py
│   └── result_cache.py
│
├── runners/                     # Component execution (includes framework adapters)
│   ├── __init__.py
│   ├── llm_guard.py            # LLM Guard tool
│   ├── mcp_test_host.py        # MCP testing host
│   ├── agent_runner.py         # Generic agent execution
│   └── adapters/               # Framework adapters
│       ├── __init__.py
│       ├── aurite_adapter.py       # Native Aurite execution
│       ├── langchain_adapter.py    # LangChain framework execution
│       └── autogen_adapter.py      # AutoGen framework execution
│
├── qa/                          # QA Domain
│   ├── __init__.py
│   ├── qa_engine.py            # Level 2: QA orchestrator
│   ├── qa_models.py            # QA-specific models (includes framework field)
│   ├── base_qa_tester.py       # Base class for QA testers
│   └── components/             # Level 3: QA component testers
│       ├── __init__.py
│       ├── llm_qa_tester.py
│       ├── mcp_qa_tester.py
│       ├── agent_qa_tester.py
│       └── workflow_qa_tester.py
│
└── security/                    # Security Domain
    ├── __init__.py
    ├── security_engine.py      # Level 2: Security orchestrator
    ├── security_models.py      # Security-specific models
    ├── base_security_tester.py # Base class for Security testers
    ├── components/             # Level 3: Security component testers
    │   ├── __init__.py
    │   ├── llm_security_tester.py
    │   ├── mcp_security_tester.py
    │   ├── agent_security_tester.py
    │   └── workflow_security_tester.py
    └── runtime/                # Runtime security monitoring
        ├── __init__.py
        ├── monitor.py
        ├── filters.py
        └── alerts.py
```

## Three-Level Architecture

### Level 1: System Integration (`test_engine.py`)

**Primary Responsibility:** Entry point for all testing requests and system integration.

**Specific Responsibilities:**

- **API Integration:** Handle all incoming requests from Aurite's API routes
- **Request Routing:** Route requests to appropriate domain engines (QA or Security)
- **Framework Coordination:** Select and coordinate framework adapters/runners for cross-framework testing
- **Result Storage:** Manage test result caching and database storage
- **Session Management:** Track test sessions and execution state
- **Cross-Domain Coordination:** Handle requests that require both QA and Security testing
- **Metrics Aggregation:** Collect and aggregate metrics across all test types
- **Configuration Integration:** Interface with Aurite's ConfigManager for test configurations

**Key Methods:**

```python
class TestEngine:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.qa_engine = QAEngine()
        self.security_engine = SecurityEngine()

    async def run_evaluation(self, eval_config_id: str) -> EvaluationResult
    async def run_security_assessment(self, security_config_id: str) -> SecurityResult
    async def get_test_status(self, test_id: str) -> TestStatus
    def cache_result(self, test_id: str, result: TestResult) -> None
```

### Level 2: Domain Orchestration

#### QA Engine (`qa/qa_engine.py`)

**Primary Responsibility:** Orchestrate quality assurance testing across all component types.

**Specific Responsibilities:**

- **Component Test Routing:** Route QA requests to appropriate component testers
- **Test Case Management:** Distribute and manage test cases across components
- **Schema Validation:** Handle JSON schema validation for structured outputs
- **QA Metrics Aggregation:** Calculate quality scores using weighted averages
- **Multi-Component Evaluation:** Handle evaluations that span multiple components
- **Framework Runner Coordination:** Select appropriate runners based on framework requirements

**Key Methods:**

```python
class QAEngine:
    async def evaluate_component(self, request: QATestRequest) -> QAResult:
        # Get the appropriate runner based on framework
        runner = self.get_runner(request.framework)

        # Runner handles framework-specific execution (or existing run function method etc.)
        results = await runner.execute_component(
            request.component_type,
            request.component_config
        )

        # Engine handles framework-agnostic evaluation
        return self.evaluate_results(results, request.test_cases)

    async def validate_schema(self, output: dict, schema: dict) -> ValidationResult
    def aggregate_qa_scores(self, results: list) -> float
```

#### Security Engine (`security/security_engine.py`)

**Primary Responsibility:** Orchestrate security assessments across all component types.

**Specific Responsibilities:**

- **Security Test Routing:** Route security requests to appropriate component testers
- **Threat Analysis:** Perform cross-component threat analysis
- **Security Score Calculation:** Calculate security scores using minimum (weakest link) approach
- **Alert Generation:** Generate and escalate security alerts based on threat levels
- **Compliance Checking:** Validate compliance with security policies
- **Concurrent Assessment Management:** Manage multiple concurrent security assessments
- **Cross-Component Vulnerability Detection:** Identify vulnerabilities that span components
- **Runtime Monitoring Coordination:** Interface with runtime security monitoring

**Key Methods:**

```python
class SecurityEngine:
    async def assess_component_security(self, component_type: str, config: dict) -> SecurityResult
    async def assess_full_configuration(self, config: dict) -> dict[str, SecurityResult]
    async def analyze_cross_component_threats(self, results: dict) -> list[SecurityThreat]
    def calculate_security_score(self, results: list) -> float
    async def generate_alerts(self, threats: list) -> list[Alert]
```

### Level 3: Component Testing

#### Component Testers

**Primary Responsibility:** Execute specific tests for their component type.

**Specific Responsibilities:**

- **Test Category Management:** Manage multiple test categories within the component
- **Test Execution:** Execute individual test methods for each category
- **Runner Integration:** Use appropriate runners for component execution
- **Result Standardization:** Return results in standardized formats
- **Component-Specific Logic:** Handle component-specific testing requirements
- **Configuration Validation:** Validate component configurations before testing

**Base Classes:**

```python
# qa/base_qa_tester.py
class BaseQATester:
    async def test_component(self, config: dict, test_cases: list) -> QATestResult
    def aggregate_qa_scores(self, results: list) -> float  # Weighted average
    def validate_config(self, config: dict) -> bool

# security/base_security_tester.py
class BaseSecurityTester:
    async def assess_security(self, config: dict) -> SecurityTestResult
    def calculate_security_score(self, results: list) -> float  # Minimum (weakest link)
    def generate_threats(self, results: list) -> list[SecurityThreat]
```

## Framework Integration Strategy

### Framework Adapters as Runners

Framework adapters are specialized runners that handle framework-specific execution while maintaining framework-agnostic interfaces:

```python
# In qa_models.py
class QATestRequest(BaseModel):
    component_type: str
    component_config: dict
    test_cases: List[TestCase]
    framework: Optional[str] = "aurite"  # Specifies which runner/adapter to use

# In runners/langchain_adapter.py
class LangChainAdapter:
    async def execute_agent(self, config: dict) -> ExecutionResult:
        # 1. Translate Aurite config to LangChain format
        langchain_config = self.translate_to_langchain(config)

        # 2. Execute in LangChain
        langchain_result = await self.run_langchain_agent(langchain_config)

        # 3. Translate result back to Aurite format
        return self.translate_from_langchain(langchain_result)
```

### Benefits of This Approach

- **Framework-Agnostic Engines:** QA and Security engines remain framework-independent
- **Specialized Execution:** Framework adapters handle framework-specific details
- **Simple Integration:** Users specify framework via configuration field
- **Shared Runners:** Both QA and Security can use the same framework adapters

## Configuration Integration

### Leveraging Aurite's Configuration System

Instead of creating a separate configuration system, the testing framework integrates with Aurite's existing ConfigManager:

**Configuration Models** (in `src/aurite/lib/models/config/components.py`):

```python
# Existing - QA Testing
class EvaluationConfig(BaseComponentConfig):
    type: Literal["evaluation"] = "evaluation"
    eval_name: Optional[str]
    eval_type: Optional[str]
    test_cases: List[EvaluationCase]
    review_llm: Optional[str]
    expected_schema: Optional[dict]
    framework: Optional[str] = "aurite"  # NEW: Framework specification

# New - Security Testing
class SecurityAssessmentConfig(BaseComponentConfig):
    type: Literal["security_assessment"] = "security_assessment"
    component_name: str
    component_type: str  # "llm", "mcp", "agent", "workflow"
    security_tests: List[str]  # Which tests to run
    threat_thresholds: Dict[str, float]
    alert_settings: Optional[AlertSettings]
    framework: Optional[str] = "aurite"  # Framework specification
```

**User Configuration Example:**

```yaml
# config/testing/llm_security.yaml
- type: security_assessment
  name: claude-security-check
  description: Security assessment for Claude LLM
  component_name: claude-3-sonnet
  component_type: llm
  framework: aurite
  security_tests:
    - prompt_injection_basic
    - toxicity_detection
    - secrets_detection
  threat_thresholds:
    critical: 0.9
    high: 0.7
    medium: 0.5
```

## Data Flow

### Standard Test Request Flow

```
1. API Request
   POST /testing/security/assess
   {
     "security_config_id": "claude-security-check"
   }
   ↓

2. TestEngine.run_security_assessment()
   - Gets config from Aurite's ConfigManager
   - Validates request
   - Checks cache for existing results
   - Routes to SecurityEngine
   ↓

3. SecurityEngine.assess_component_security()
   - Determines component tester needed
   - Instantiates LLMSecurityTester
   - Manages assessment execution
   ↓

4. LLMSecurityTester.assess_security()
   - Uses appropriate runner (based on framework field)
   - Runs prompt_injection_basic()
   - Runs toxicity_detection()
   - Runs secrets_detection()
   - Aggregates results
   ↓

5. Results flow back up
   LLMSecurityTester → SecurityEngine → TestEngine → API Response

6. TestEngine caches results and stores in database
```

### Framework-Specific Execution Flow

```
1. QA Test Request (framework: "langchain")
   ↓

2. QAEngine receives request
   ↓

3. QAEngine.get_runner("langchain")
   - Returns LangChainAdapter from runners/
   ↓

4. AgentQATester.test_component()
   - Uses LangChainAdapter for execution
   - LangChainAdapter translates config
   - Executes in LangChain environment
   - Translates results back
   ↓

5. QAEngine evaluates results (framework-agnostic)
   ↓

6. Results returned with framework metadata
```

## Component Responsibility Matrix

| Level | Component                | Primary Responsibilities                                      | Key Integrations                      |
| ----- | ------------------------ | ------------------------------------------------------------- | ------------------------------------- |
| **1** | `TestEngine`             | API integration, request routing, caching, session management | Aurite API, ConfigManager, Database   |
| **2** | `QAEngine`               | QA test orchestration, schema validation, LLM evaluation      | Component QA Testers, Runners         |
| **2** | `SecurityEngine`         | Security orchestration, threat analysis, alert generation     | Component Security Testers, Runtime   |
| **3** | `LLMQATester`            | LLM quality tests, performance evaluation, accuracy testing   | Runners, Evaluation metrics           |
| **3** | `LLMSecurityTester`      | LLM security tests, prompt injection, toxicity detection      | Runners, LLM Guard, Security scanners |
| **3** | `MCPQATester`            | MCP server quality tests, API compliance, performance         | MCP Test Host, API validators         |
| **3** | `MCPSecurityTester`      | MCP server security tests, authentication, input validation   | Security scanners, Auth validators    |
| **3** | `AgentQATester`          | Agent quality tests, goal achievement, tool usage             | Agent Runner, Framework adapters      |
| **3** | `AgentSecurityTester`    | Agent security tests, permission boundaries, action auth      | Security policies, Auth systems       |
| **3** | `WorkflowQATester`       | Workflow quality tests, business logic, end-to-end success    | Multiple agents, Business validators  |
| **3** | `WorkflowSecurityTester` | Workflow security tests, data isolation, audit compliance     | Audit systems, Data validators        |

## Integration Points

### API Integration

**New API Routes:**

```python
# Main testing endpoints
POST /testing/qa/evaluate
POST /testing/qa/evaluate/{evaluation_config_id}
POST /testing/security/assess
POST /testing/security/assess/{security_config_id}
GET  /testing/results/{test_id}
GET  /testing/status/{test_id}

# Component-specific endpoints
POST /testing/qa/llm/{llm_id}/test
POST /testing/security/agent/{agent_id}/assess
POST /testing/security/runtime/monitor/start
```

### Database Integration

**New Tables:**

- `test_sessions` - Track test execution sessions
- `test_results` - Store detailed test results
- `security_threats` - Log detected security threats
- `qa_evaluations` - Store QA evaluation results

## Migration Guide

### Existing Code Mapping

| Current Location                                       | New Location                                          | Migration Notes                                |
| ------------------------------------------------------ | ----------------------------------------------------- | ---------------------------------------------- |
| `src/aurite/lib/components/evaluation/evaluator.py`    | `src/aurite/testing/qa/qa_engine.py`                  | Core evaluation logic moves to QA engine       |
| `src/aurite/lib/components/evaluation/agent_runner.py` | `src/aurite/testing/runners/agent_runner.py`          | Becomes shared runner for both QA and Security |
| `src/aurite/security/core/security_engine.py`          | `src/aurite/testing/security/security_engine.py`      | Moves to Level 2 security orchestration        |
| `src/aurite/security/components/llm_security/`         | `src/aurite/testing/security/components/`             | Flattened structure, moves to Level 3          |
| `src/aurite/security/core/base_tester.py`              | `src/aurite/testing/security/base_security_tester.py` | Becomes security-specific base class           |
| `src/aurite/testing/mcp/testing_mcp_host.py`           | `src/aurite/testing/runners/mcp_test_host.py`         | Becomes shared runner for MCP testing          |
| `src/aurite/testing/cache/`                            | `src/aurite/testing/cache/`                           | Moves to root level of testing framework       |

### Migration Steps

1. **Create new directory structure**
2. **Move and refactor Blake's evaluation code:**
   - Extract orchestration logic to `qa/qa_engine.py`
   - Move `agent_runner.py` to `runners/`
   - Create `qa/base_qa_tester.py`
3. **Move and refactor Jiten's security code:**
   - Extract orchestration logic to `security/security_engine.py`
   - Move component testers to `security/components/`
   - Create `security/base_security_tester.py`
   - Move `llm_guard.py` to `runners/`
4. **Create new `test_engine.py` as main orchestrator**
5. **Move existing cache to `testing/cache/`**
6. **Update imports and API routes**
7. **Add `SecurityAssessmentConfig` to components.py**
8. **Test integration with existing Aurite framework**

### API Route Updates

**Current:**

```python
POST /execution/evaluate
POST /execution/evaluate/{evaluation_config_id}
```

**New:**

```python
POST /testing/qa/evaluate
POST /testing/qa/evaluate/{evaluation_config_id}
POST /testing/security/assess
POST /testing/security/assess/{security_config_id}
```

## Benefits of This Architecture

1. **Clean Root Directory:** Only essential files and folders at the top level
2. **Clear Separation of Concerns:** Each level has distinct responsibilities
3. **Framework Integration:** Seamless integration with Aurite's configuration system
4. **Shared Resources:** Runners and cache are accessible to both QA and Security
5. **Maintainable:** Easy to modify individual components without affecting others
6. **Testable:** Each level can be unit tested independently
7. **Extensible:** New test types can be added at the appropriate level
8. **Scalable:** Can handle increasing complexity without architectural changes
9. **Framework-Ready:** Prepared for extraction to separate repository
10. **Practical Focus:** Root contains what developers interact with most

## Runtime Security Monitoring

Runtime monitoring is specifically focused on security concerns and is organized under `security/runtime/`:

```python
# security/runtime/monitor.py
class SecurityMonitor:
    async def monitor_llm_request(self, request: LLMRequest) -> SecurityResult
    async def monitor_agent_execution(self, agent_id: str) -> SecurityResult
    def start_monitoring(self, component_type: str, component_id: str)

# security/runtime/filters.py
class SecurityFilters:
    async def filter_prompt_injection(self, input_text: str) -> FilterResult
    async def filter_toxic_content(self, content: str) -> FilterResult
    async def filter_secrets(self, text: str) -> FilterResult
```

This approach keeps runtime monitoring focused and avoids the complexity of trying to make it generic across QA and Security when 99% of runtime testing will be security-focused.

## Future Considerations

- **Microservice Extraction:** The entire `testing/` directory can be moved to a separate repository
- **API Versioning:** Testing APIs can be versioned independently
- **Plugin Architecture:** Component testers can be developed as plugins
- **Distributed Testing:** Architecture supports distributed test execution
- **Framework Expansion:** Easy to add support for new agent frameworks through new runners
- **QA Runtime Features:** If needed, can add `qa/runtime/` or refactor security runtime to be shared
