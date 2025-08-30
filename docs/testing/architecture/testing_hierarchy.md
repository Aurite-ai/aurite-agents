# Testing Hierarchy and Flow

## Overview

This document visualizes the complete testing hierarchy and flow for the Kahuna Testing & Security Framework, showing how components build upon each other and how test results flow through the system across multiple agent frameworks.

The testing hierarchy now operates in three dimensions:

1. **Testing Categories** (Quality vs Security)
2. **Testing Phases** (Development vs Runtime)
3. **Framework Scope** (Framework-Agnostic vs Framework-Specific)

This three-dimensional approach enables testing of AI components independent of specific agent frameworks while also supporting framework-specific validation.

## Complete Testing Hierarchy

```mermaid
flowchart TD
    Start[Testing Framework] --> Split{Test Category}

    Split -->|Quality| QA[Quality Assurance]
    Split -->|Security| SEC[Security Testing]

    %% Quality Branch
    QA --> QPhase{Testing Phase}
    QPhase -->|Development| QDev[Development-Time Quality]
    QPhase -->|Runtime| QRun[Runtime Quality Monitoring]

    %% Security Branch
    SEC --> SPhase{Testing Phase}
    SPhase -->|Development| SDev[Development-Time Security]
    SPhase -->|Runtime| SRun[Runtime Security Monitoring]

    %% Framework Scope Split
    QDev --> QScope{Framework Scope}
    QRun --> QRScope{Framework Scope}
    SDev --> SScope{Framework Scope}
    SRun --> SRScope{Framework Scope}

    %% Framework-Agnostic Path
    QScope -->|Agnostic| QAgnostic[Universal Quality Tests]
    QScope -->|Specific| QSpecific[Framework Quality Tests]
    SScope -->|Agnostic| SAgnostic[Universal Security Tests]
    SScope -->|Specific| SSpecific[Framework Security Tests]

    %% Component Testing Hierarchy - Agnostic
    QAgnostic --> LLM_Q[LLM Quality Tests<br/>100% Agnostic]
    QAgnostic --> MCP_Q[MCP Server Quality Tests<br/>100% Agnostic]
    SAgnostic --> LLM_S[LLM Security Tests<br/>100% Agnostic]
    SAgnostic --> MCP_S[MCP Server Security Tests<br/>100% Agnostic]

    %% Component Testing - Mixed
    LLM_Q --> Agent_Q[Agent Quality Tests<br/>60% Agnostic]
    MCP_Q --> Agent_Q
    LLM_S --> Agent_S[Agent Security Tests<br/>60% Agnostic]
    MCP_S --> Agent_S
    QSpecific --> Agent_Q
    SSpecific --> Agent_S

    %% Business Layer
    Agent_Q --> WF_Q[Workflow Quality Tests<br/>20% Agnostic]
    Agent_S --> WF_S[Workflow Security Tests<br/>20% Agnostic]

    %% Results Flow
    WF_Q --> Results[Test Results]
    WF_S --> Results
    QRScope --> Metrics[Runtime Metrics]
    SRScope --> Metrics

    Results --> Kahuna_Exec[Kahuna Executive Mode]
    Metrics --> Kahuna_Exec

    %% Input from Manager Mode
    Kahuna_Mgr[Kahuna Manager Mode] --> Requirements[Business Requirements<br/>+ Target Frameworks]
    Requirements --> Start

    style Start fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style QA fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style SEC fill:#F44336,stroke:#C62828,stroke-width:2px,color:#fff
    style QAgnostic fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style SAgnostic fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style Results fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style Metrics fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style Kahuna_Exec fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style Kahuna_Mgr fill:#00BCD4,stroke:#0097A7,stroke-width:2px,color:#fff
```

## Framework-Agnostic Testing Flow

```mermaid
flowchart TD
    Start[Test Request] --> Detect{Detect Framework}

    Detect -->|Aurite| Native[Native Execution]
    Detect -->|LangChain| LC_Adapter[LangChain Adapter]
    Detect -->|AutoGen| AG_Adapter[AutoGen Adapter]
    Detect -->|Other| Generic_Adapter[Generic Adapter]

    LC_Adapter --> Translate[Translate to Aurite Format]
    AG_Adapter --> Translate
    Generic_Adapter --> Translate
    Native --> Categorize{Categorize Component}

    Translate --> Categorize

    Categorize -->|LLM/MCP| Universal[Universal Tests<br/>100% Agnostic]
    Categorize -->|Agent| Hybrid[Hybrid Tests<br/>60% Agnostic]
    Categorize -->|Workflow| Specific[Specific Tests<br/>20% Agnostic]

    Universal --> Cache_Universal[Cache Universal Results]
    Hybrid --> Split_Tests{Split Tests}
    Specific --> Framework_Tests[Framework-Specific Tests]

    Split_Tests -->|Agnostic| Agnostic_Tests[Run Agnostic Tests]
    Split_Tests -->|Specific| Framework_Tests

    Agnostic_Tests --> Cache_Agnostic[Cache Agnostic Results]
    Framework_Tests --> Cache_Specific[Cache Framework Results]

    Cache_Universal --> Aggregate[Aggregate Results]
    Cache_Agnostic --> Aggregate
    Cache_Specific --> Aggregate

    Aggregate --> Normalize[Normalize to Standard Format]
    Normalize --> Report[Generate Report]

    style Start fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style Universal fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style Hybrid fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style Specific fill:#F44336,stroke:#C62828,stroke-width:2px,color:#fff
    style Report fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
```

## Test Execution Flow

```mermaid
flowchart TD
    Start[Start Testing] --> Check{Check Dependencies}

    Check -->|No Dependencies| Foundation[Test Foundation Components]
    Check -->|Has Dependencies| Wait[Wait for Dependencies]

    Foundation --> Cache1[Cache LLM Results<br/>Universal Cache]
    Foundation --> Cache2[Cache MCP Results<br/>Universal Cache]

    Cache1 --> Ready1[LLM Tests Complete]
    Cache2 --> Ready2[MCP Tests Complete]

    Ready1 --> AgentTest{Agent Testing}
    Ready2 --> AgentTest

    Wait --> DepCheck{Dependencies Ready?}
    DepCheck -->|No| Wait
    DepCheck -->|Yes| AgentTest

    AgentTest --> Inherit[Inherit Foundation Results<br/>Cross-Framework]
    Inherit --> AgentSpecific[Run Agent Tests<br/>60% Agnostic, 40% Specific]
    AgentSpecific --> CacheAgent[Cache Agent Results]

    CacheAgent --> ReadyAgent[Agent Tests Complete]

    ReadyAgent --> WorkflowTest{Workflow Testing}

    WorkflowTest --> InheritAll[Inherit All Agent Results<br/>Cross-Framework]
    InheritAll --> WFSpecific[Run Workflow Tests<br/>20% Agnostic, 80% Specific]
    WFSpecific --> FinalResults[Generate Final Results]

    FinalResults --> Report[Generate Reports]
    Report --> End[Testing Complete]

    style Start fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style End fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style Foundation fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style AgentTest fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style WorkflowTest fill:#E91E63,stroke:#C2185B,stroke-width:2px,color:#fff
    style FinalResults fill:#00BCD4,stroke:#0097A7,stroke-width:2px,color:#fff
```

## Quality vs Security Score Propagation

```mermaid
flowchart TD
    subgraph Quality[Quality Score Propagation]
        Q_LLM[LLM Quality: 0.94] --> Q_Calc1[Weighted Average]
        Q_MCP[MCP Quality: 0.96] --> Q_Calc1
        Q_Agent_Specific[Agent Quality: 0.90] --> Q_Calc1
        Q_Calc1 --> Q_Agent[Agent Quality: 0.93]

        Q_Agent --> Q_Calc2[Weighted Average]
        Q_WF_Specific[Workflow Quality: 0.95] --> Q_Calc2
        Q_Calc2 --> Q_WF[Workflow Quality: 0.94]
    end

    subgraph Security[Security Score Propagation]
        S_LLM[LLM Security: 0.96] --> S_Calc1[Take Minimum]
        S_MCP[MCP Security: 0.99] --> S_Calc1
        S_Agent_Specific[Agent Security: 0.92] --> S_Calc1
        S_Calc1 --> S_Agent[Agent Security: 0.92]

        S_Agent --> S_Calc2[Take Minimum]
        S_WF_Specific[Workflow Security: 0.95] --> S_Calc2
        S_Calc2 --> S_WF[Workflow Security: 0.92]
    end

    style Q_Calc1 fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style Q_Calc2 fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style S_Calc1 fill:#F44336,stroke:#C62828,stroke-width:2px,color:#fff
    style S_Calc2 fill:#F44336,stroke:#C62828,stroke-width:2px,color:#fff
```

## Development vs Runtime Testing Flow

```mermaid
flowchart LR
    subgraph Development[Development-Time Testing]
        D1[Comprehensive Tests] --> D2[All Edge Cases]
        D2 --> D3[Performance Benchmarks]
        D3 --> D4[Security Audits]
        D4 --> D5[Generate Baselines]
    end

    subgraph Runtime[Runtime Monitoring]
        R1[Selective Tests] --> R2[Critical Checks Only]
        R2 --> R3[Real-time Filtering]
        R3 --> R4[Anomaly Detection]
        R4 --> R5[Alert on Deviations]
    end

    D5 -->|Deploy| Prod[Production Environment]
    Prod --> Runtime

    Runtime -->|Feedback| Improve[Improve Tests]
    Improve -->|Update| Development

    style Development fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style Runtime fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style Prod fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
```

## Test Result Caching Strategy

```mermaid
flowchart TD
    Test[Run Test] --> Result[Test Result]
    Result --> Scope{Framework Scope?}

    Scope -->|Agnostic| Universal_Cache[Universal Cache<br/>Shared Across Frameworks]
    Scope -->|Specific| Framework_Cache[Framework Cache<br/>Isolated per Framework]

    Universal_Cache --> Meta_U[Store Metadata<br/>• Component ID<br/>• Version<br/>• Timestamp<br/>• TTL<br/>• Framework: ANY]
    Framework_Cache --> Meta_F[Store Metadata<br/>• Component ID<br/>• Version<br/>• Timestamp<br/>• TTL<br/>• Framework: Specific]

    Meta_U --> TTL_U{Check TTL}
    Meta_F --> TTL_F{Check TTL}

    Request[New Test Request] --> Framework_Check{Which Framework?}

    Framework_Check --> CheckCache{Check Cache}

    CheckCache -->|Universal Found| TTL_U
    CheckCache -->|Framework Found| TTL_F
    CheckCache -->|Not Found| Test

    TTL_U -->|Valid| UseCache[Use Cached Result<br/>Cross-Framework]
    TTL_F -->|Valid| UseCache
    TTL_U -->|Expired| Test
    TTL_F -->|Expired| Test

    UseCache --> Inherit[Inherit to Dependent]

    Update[Component Update] --> Invalidate{Which Cache?}
    Invalidate -->|LLM/MCP| Invalidate_Universal[Invalidate Universal<br/>All Frameworks Affected]
    Invalidate -->|Agent/Workflow| Invalidate_Specific[Invalidate Specific<br/>Single Framework]

    Invalidate_Universal --> Cascade[Cascade Invalidation]
    Invalidate_Specific --> Cascade
    Cascade --> Deps[Invalidate All Dependents]

    style Test fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style UseCache fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style Universal_Cache fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style Framework_Cache fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style Invalidate_Universal fill:#F44336,stroke:#C62828,stroke-width:2px,color:#fff
```

## Integration with Kahuna Ecosystem

```mermaid
flowchart TD
    subgraph Manager[Kahuna Manager Mode]
        BW[Business Workflow] --> Req[Requirements]
        PD[Project Document] --> Req
        Req --> Context[Project Context]
    end

    subgraph Developer[Kahuna Developer Mode]
        Context --> Testing[Testing Framework]
        Testing --> QTests[Quality Tests]
        Testing --> STests[Security Tests]

        QTests --> DevTime[Development Testing]
        STests --> DevTime

        DevTime --> Deploy[Deployment]
        Deploy --> RunTime[Runtime Monitoring]

        QTests --> RunTime
        STests --> RunTime
    end

    subgraph Executive[Kahuna Executive Mode]
        RunTime --> Metrics[Metrics Collection]
        Metrics --> QMetrics[Quality Metrics]
        Metrics --> SMetrics[Security Metrics]
        Metrics --> BMetrics[Business KPIs]

        QMetrics --> Dashboard[Executive Dashboard]
        SMetrics --> Dashboard
        BMetrics --> Dashboard
    end

    style Manager fill:#00BCD4,stroke:#0097A7,stroke-width:2px,color:#fff
    style Developer fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style Executive fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style Testing fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style Dashboard fill:#E91E63,stroke:#C2185B,stroke-width:2px,color:#fff
```

## Tabular Representations

### Component Test Inheritance Matrix

| Component      | Framework Scope | Depends On      | Inherits From                                      | Cross-Framework Inheritance | New Tests                                                        | Inheritance Benefit       |
| -------------- | --------------- | --------------- | -------------------------------------------------- | --------------------------- | ---------------------------------------------------------------- | ------------------------- |
| **LLM**        | 100% Agnostic   | None            | None                                               | All results shared          | • Prompt injection<br>• Content safety<br>• Response quality     | Foundation (0% inherited) |
| **MCP Server** | 100% Agnostic   | None            | None                                               | All results shared          | • API security<br>• Performance<br>• Availability                | Foundation (0% inherited) |
| **Agent**      | 60% Agnostic    | LLM + MCP       | • LLM security scores<br>• MCP performance metrics | 60% cross-framework         | • Tool selection<br>• Goal achievement<br>• Multi-turn coherence | ~60% inherited            |
| **Workflow**   | 20% Agnostic    | Multiple Agents | • All agent scores<br>• All foundation scores      | 20% cross-framework         | • Business logic<br>• End-to-end flow<br>• Data consistency      | ~70% inherited            |

### Quality vs Security Score Calculation

| Aspect                | Quality Scoring  | Security Scoring       | Rationale                                                |
| --------------------- | ---------------- | ---------------------- | -------------------------------------------------------- |
| **Method**            | Weighted Average | Minimum (Weakest Link) | Quality can be averaged; Security fails at weakest point |
| **LLM Score**         | 0.94             | 0.96                   | Foundation scores                                        |
| **MCP Score**         | 0.96             | 0.99                   | Foundation scores                                        |
| **Agent-Specific**    | 0.90             | 0.92                   | New agent tests                                          |
| **Agent Final**       | 0.93 (weighted)  | 0.92 (minimum)         | Combined result                                          |
| **Workflow-Specific** | 0.95             | 0.95                   | New workflow tests                                       |
| **Workflow Final**    | 0.94 (weighted)  | 0.92 (minimum)         | Final scores                                             |

### Development vs Runtime Testing Comparison

| Aspect                | Development Testing                            | Runtime Testing                                                | Time Allocation                       |
| --------------------- | ---------------------------------------------- | -------------------------------------------------------------- | ------------------------------------- |
| **Coverage**          | 100% - All test cases                          | 10-20% - Critical only                                         | Dev: 100%, Runtime: Sampling          |
| **Execution Time**    | Minutes to hours                               | Milliseconds to seconds                                        | Dev: Thorough, Runtime: Fast          |
| **Test Types**        | • Edge cases<br>• Stress tests<br>• Benchmarks | • Security filters<br>• Quality scoring<br>• Anomaly detection | Dev: Comprehensive, Runtime: Targeted |
| **Frequency**         | On-Demand, Per deployment                      | Per request/response                                           | Dev: Once, Runtime: Continuous        |
| **Action on Failure** | Block deployment                               | Log, alert, or block                                           | Dev: Prevent, Runtime: Respond        |

### Test Categories by Component

| Component      | Framework Scope | Quality Tests (Agnostic)                                                           | Quality Tests (Specific)                       | Security Tests (Agnostic)                                                         | Security Tests (Specific)                           | Inherited | New | Total |
| -------------- | --------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------- | --------- | --- | ----- |
| **LLM**        | 100% Agnostic   | • Coherence<br>• Instruction following<br>• Format compliance<br>• Quality scoring | N/A                                            | • Prompt injection<br>• Content safety<br>• Data leakage<br>• Real-time filtering | N/A                                                 | 0         | 8   | 8     |
| **MCP Server** | 100% Agnostic   | • API compliance<br>• Performance<br>• Error handling<br>• Availability            | N/A                                            | • Authentication<br>• Input validation<br>• Rate limiting<br>• Access monitoring  | N/A                                                 | 0         | 8   | 8     |
| **Agent**      | 60% Agnostic    | • Tool selection<br>• Goal achievement                                             | • Memory management<br>• State handling        | • Permission boundaries<br>• Action authorization                                 | • Framework auth<br>• Context isolation             | 16        | 8   | 24    |
| **Workflow**   | 20% Agnostic    | • Business compliance<br>• End-to-end success                                      | • Orchestration<br>• Inter-agent communication | • Data isolation<br>• Audit completeness                                          | • Framework security<br>• State management security | 48        | 8   | 56    |

### Kahuna Integration Points

| Kahuna Mode        | Role                  | Input/Output                                                           | Testing Interaction   |
| ------------------ | --------------------- | ---------------------------------------------------------------------- | --------------------- |
| **Manager Mode**   | Requirements Provider | • Business workflows<br>• Project documents<br>• Quality thresholds    | Defines what to test  |
| **Developer Mode** | Testing Executor      | • Test implementation<br>• Development testing<br>• Runtime monitoring | Executes all testing  |
| **Executive Mode** | Metrics Consumer      | • Quality dashboards<br>• Security reports<br>• Business KPIs          | Receives test results |

### Alert Severity and Response Matrix (Rough Draft - still a WIP)

| Severity     | Quality Threshold | Security Threshold | Response Time | Action                      |
| ------------ | ----------------- | ------------------ | ------------- | --------------------------- |
| **Critical** | < 0.5             | Any breach         | Immediate     | Block + Alert + Investigate |
| **High**     | < 0.7             | Score < 0.8        | < 5 min       | Block + Alert team          |
| **Medium**   | < 0.85            | Score < 0.9        | < 1 hour      | Log + Monitor               |
| **Low**      | < 0.95            | Score < 0.95       | < 24 hours    | Log for analysis            |

### Cache Strategy Parameters

| Parameter                   | Value     | Purpose                        | Impact                       | Framework Scope    |
| --------------------------- | --------- | ------------------------------ | ---------------------------- | ------------------ |
| **TTL (LLM/MCP)**           | 24 hours  | Foundation rarely changes      | High reuse across frameworks | Universal cache    |
| **TTL (Agent - Agnostic)**  | 12 hours  | Core behaviors stable          | Cross-framework reuse        | Universal cache    |
| **TTL (Agent - Specific)**  | 4 hours   | Framework features change      | Framework-isolated           | Framework cache    |
| **TTL (Workflow)**          | 1 hour    | Frequent updates               | Fresh results                | Framework cache    |
| **Cross-Framework Sharing** | Enabled   | Maximize test reuse            | 40-60% reduction in testing  | LLM/MCP/Agent core |
| **Invalidation**            | On update | Maintain consistency           | Cascade to dependents        | Both cache types   |
| **Cache Hit Rate**          | ~85%      | Increased with universal cache | 85% time saved               | Overall            |

## Framework Compatibility Matrix

| Framework     | LLM Support | MCP Support | Agent Support | Workflow Support | Adapter Status | Testing Coverage |
| ------------- | ----------- | ----------- | ------------- | ---------------- | -------------- | ---------------- |
| **Aurite**    | 100%        | 100%        | 100%          | 100%             | Native         | 100%             |
| **LangChain** | 100%        | 100%        | 80%           | 70%              | Available      | 85%              |
| **AutoGen**   | 100%        | 100%        | 75%           | 65%              | Available      | 80%              |
| **CrewAI**    | 100%        | 100%        | 70%           | 60%              | In Development | 75%              |
| **Custom**    | 100%        | 100%        | Varies        | Varies           | Generic        | 60-80%           |

## Summary

This hierarchical testing structure provides:

1. **Three-Dimensional Organization**: Quality/Security × Development/Runtime × Agnostic/Specific
2. **Framework Independence**: LLM and MCP tests work across all frameworks
3. **Cross-Framework Inheritance**: Agnostic test results shared between frameworks
4. **Efficient Execution**: Through enhanced caching and result reuse
5. **Comprehensive Coverage**: All components tested at appropriate levels
6. **Business Integration**: From requirements (Manager) to metrics (Executive)
7. **Significant Time Savings**: 70-85% reduction through compositional and cross-framework approach

The framework ensures that each component is tested appropriately while maximizing test reuse across different agent frameworks through:

- **Universal caching** for framework-agnostic components
- **Intelligent inheritance** of results across framework boundaries
- **Adapter pattern** for framework translation
- **Standardized formats** for cross-framework comparison

The tables and diagrams above provide a structured view that complements the visual representations, making it easy to:

- Compare testing approaches across components and frameworks
- Understand inheritance relationships both within and across frameworks
- Calculate time savings from cross-framework test reuse
- Plan test implementation for multi-framework environments
- Set appropriate thresholds and alerts for each framework

For detailed architecture on framework-agnostic testing, see [Framework-Agnostic Testing Architecture](framework_agnostic_testing.md).
