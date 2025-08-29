# Testing Hierarchy and Flow

## Overview

This document visualizes the complete testing hierarchy and flow for the Kahuna Testing & Security Framework, showing how components build upon each other and how test results flow through the system.

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

    %% Component Testing Hierarchy
    QDev --> CompQ[Component Quality Tests]
    QRun --> CompQM[Component Quality Monitors]
    SDev --> CompS[Component Security Tests]
    SRun --> CompSM[Component Security Monitors]

    %% Foundation Layer
    CompQ --> LLM_Q[LLM Quality Tests]
    CompQ --> MCP_Q[MCP Server Quality Tests]
    CompS --> LLM_S[LLM Security Tests]
    CompS --> MCP_S[MCP Server Security Tests]

    %% Integration Layer
    LLM_Q --> Agent_Q[Agent Quality Tests]
    MCP_Q --> Agent_Q
    LLM_S --> Agent_S[Agent Security Tests]
    MCP_S --> Agent_S

    %% Business Layer
    Agent_Q --> WF_Q[Workflow Quality Tests]
    Agent_S --> WF_S[Workflow Security Tests]

    %% Results Flow
    WF_Q --> Results[Test Results]
    WF_S --> Results
    CompQM --> Metrics[Runtime Metrics]
    CompSM --> Metrics

    Results --> Kahuna_Exec[Kahuna Executive Mode]
    Metrics --> Kahuna_Exec

    %% Input from Manager Mode
    Kahuna_Mgr[Kahuna Manager Mode] --> Requirements[Business Requirements]
    Requirements --> Start

    style Start fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style QA fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style SEC fill:#F44336,stroke:#C62828,stroke-width:2px,color:#fff
    style Results fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style Metrics fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style Kahuna_Exec fill:#9C27B0,stroke:#7B1FA2,stroke-width:2px,color:#fff
    style Kahuna_Mgr fill:#00BCD4,stroke:#0097A7,stroke-width:2px,color:#fff
```

## Test Execution Flow

```mermaid
flowchart TD
    Start[Start Testing] --> Check{Check Dependencies}

    Check -->|No Dependencies| Foundation[Test Foundation Components]
    Check -->|Has Dependencies| Wait[Wait for Dependencies]

    Foundation --> Cache1[Cache LLM Results]
    Foundation --> Cache2[Cache MCP Results]

    Cache1 --> Ready1[LLM Tests Complete]
    Cache2 --> Ready2[MCP Tests Complete]

    Ready1 --> AgentTest{Agent Testing}
    Ready2 --> AgentTest

    Wait --> DepCheck{Dependencies Ready?}
    DepCheck -->|No| Wait
    DepCheck -->|Yes| AgentTest

    AgentTest --> Inherit[Inherit Foundation Results]
    Inherit --> AgentSpecific[Run Agent-Specific Tests]
    AgentSpecific --> CacheAgent[Cache Agent Results]

    CacheAgent --> ReadyAgent[Agent Tests Complete]

    ReadyAgent --> WorkflowTest{Workflow Testing}

    WorkflowTest --> InheritAll[Inherit All Agent Results]
    InheritAll --> WFSpecific[Run Workflow-Specific Tests]
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
    Result --> Cache{Cache Result}

    Cache --> Meta[Store Metadata<br/>• Component ID<br/>• Version<br/>• Timestamp<br/>• TTL]

    Meta --> TTL{Check TTL}

    Request[New Test Request] --> CheckCache{Check Cache}

    CheckCache -->|Found| TTL
    CheckCache -->|Not Found| Test

    TTL -->|Valid| UseCache[Use Cached Result]
    TTL -->|Expired| Test

    UseCache --> Inherit[Inherit to Dependent]

    Update[Component Update] --> Invalidate[Invalidate Cache]
    Invalidate --> Cascade[Cascade Invalidation]
    Cascade --> Deps[Invalidate All Dependents]

    style Test fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style UseCache fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style Invalidate fill:#F44336,stroke:#C62828,stroke-width:2px,color:#fff
    style Cache fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
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

| Component      | Depends On      | Inherits From                                      | New Tests                                                        | Inheritance Benefit       |
| -------------- | --------------- | -------------------------------------------------- | ---------------------------------------------------------------- | ------------------------- |
| **LLM**        | None            | None                                               | • Prompt injection<br>• Content safety<br>• Response quality     | Foundation (0% inherited) |
| **MCP Server** | None            | None                                               | • API security<br>• Performance<br>• Availability                | Foundation (0% inherited) |
| **Agent**      | LLM + MCP       | • LLM security scores<br>• MCP performance metrics | • Tool selection<br>• Goal achievement<br>• Multi-turn coherence | ~60% inherited            |
| **Workflow**   | Multiple Agents | • All agent scores<br>• All foundation scores      | • Business logic<br>• End-to-end flow<br>• Data consistency      | ~70% inherited            |

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

| Component      | Quality Tests                                                                                                  | Security Tests                                                                                                              | Inherited | New | Total |
| -------------- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | --------- | --- | ----- |
| **LLM**        | • Coherence (Dev)<br>• Instruction following (Dev)<br>• Format compliance (Dev)<br>• Quality scoring (Runtime) | • Prompt injection (Dev)<br>• Content safety (Dev)<br>• Data leakage (Dev)<br>• Real-time filtering (Runtime)               | 0         | 8   | 8     |
| **MCP Server** | • API compliance (Dev)<br>• Performance (Dev)<br>• Error handling (Dev)<br>• Availability monitoring (Runtime) | • Authentication (Dev)<br>• Input validation (Dev)<br>• Rate limiting (Dev)<br>• Access monitoring (Runtime)                | 0         | 8   | 8     |
| **Agent**      | • Tool selection (Dev)<br>• Goal achievement (Dev)<br>• Efficiency (Dev)<br>• Performance tracking (Runtime)   | • Permission boundaries (Dev)<br>• Action authorization (Dev)<br>• Resource limits (Dev)<br>• Behavior monitoring (Runtime) | 16        | 8   | 24    |
| **Workflow**   | • Business compliance (Dev)<br>• End-to-end success (Dev)<br>• Performance (Dev)<br>• KPI tracking (Runtime)   | • Cross-agent security (Dev)<br>• Data isolation (Dev)<br>• Audit completeness (Dev)<br>• Incident detection (Runtime)      | 48        | 8   | 56    |

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

### Cache Strategy Parameters (Also a WIP)

| Parameter            | Value     | Purpose                   | Impact                |
| -------------------- | --------- | ------------------------- | --------------------- |
| **TTL (Foundation)** | 24 hours  | LLM/MCP rarely change     | High reuse            |
| **TTL (Agent)**      | 4 hours   | Moderate change frequency | Balanced              |
| **TTL (Workflow)**   | 1 hour    | Frequent updates          | Fresh results         |
| **Invalidation**     | On update | Maintain consistency      | Cascade to dependents |
| **Cache Hit Rate**   | ~70%      | Reduce redundant testing  | 70% time saved        |

## Summary

This hierarchical testing structure provides:

1. **Clear Organization**: Separation between Quality and Security, Development and Runtime
2. **Efficient Execution**: Through test result inheritance and caching
3. **Comprehensive Coverage**: All components tested at appropriate levels
4. **Business Integration**: From requirements (Manager) to metrics (Executive)
5. **Significant Time Savings**: 50-70% reduction through compositional approach

The framework ensures that each component is tested appropriately while avoiding redundant testing through intelligent inheritance of results from foundation components to higher-level integrations.

The tables above provide a structured view that complements the visual diagrams, making it easy to:

- Compare testing approaches across components
- Understand inheritance relationships
- Calculate time savings
- Plan test implementation
- Set appropriate thresholds and alerts
