# Project Rules: Framework Development Workflow

## 1. Objective

This document outlines the structured, multi-phase workflow for development within the **Aurite Agents** framework. Adherence to this process ensures that all development is context-aware, well-planned, and thoroughly verified.

**Note on Packaged Framework Development:** For tasks that involve modifying the distributable `aurite` package, such as changing the `aurite init` command or its templates, this document should be used in conjunction with the specific rules outlined in `.clinerules/package_development_rules.md`.

## 2. Phase 1: Discovery & Context Retrieval

The goal of this initial phase is to build a complete and accurate understanding of the task at hand by thoroughly reviewing all relevant documentation and source code.

1.  **Start with the Documentation Guide:** Always begin by reviewing `.clinerules/documentation_guide.md` to identify the high-level documents relevant to the task.

2.  **Recursive Document Review:** Follow the paths identified in the documentation guide. This may be a recursive process. For example, a task related to Agent behavior would involve:
    *   Reading `docs/components/PROJECT.md` (as indicated by the guide).
    *   Following the link within that document to `docs/components/agent.md`.

3.  **Consult Layer Documents:** After reviewing the component/feature documents, consult the relevant architectural layer documents in `docs/layers/`. These are critical for understanding the implementation details.
    *   The layer documents map functionality to specific source files and test files. For an Agent-related task, `docs/layers/2_orchestration.md` is essential as it describes the files responsible for agent definition and execution (e.g., `src/aurite/components/agents/agent.py`, `src/aurite/execution/facade.py`).

4.  **Review Source Code and Tests:** With the context from the layer documents, read the identified source code files to understand the current implementation. Simultaneously, review the corresponding test files (e.g., `tests/orchestration/agent/test_agent.py`) to understand existing behavior and identify which tests will need to be created or updated.

At the end of this phase, you must have a comprehensive understanding of the task's impact on the existing codebase and a clear list of source and test files that will be affected.

## 3. Phase 2: Planning & Design

With full context from Phase 1, the next step is to create a clear and actionable implementation plan.

1.  **Plan Complexity:**
    *   **Simple Tasks:** For straightforward changes, the implementation plan can be stated directly in conversation.
    *   **Complex Tasks:** For more involved tasks, the plan must be written to a file in `docs/plans/`.
    *   **Architectural Changes:** For tasks involving new features or significant architectural modifications, a formal design document must be created in `docs/design/` before an implementation plan is written.

2.  **Implementation Plan Requirements:**
    *   **Testing Integration:** The plan must include testing as part of the implementation steps. Each development step should be followed by a verification step.
    *   **Simple Verification:** Tests written during the implementation phase should be simple, focused on verifying the core functionality of the current step. Robust error handling, edge case testing, and performance-related mocks (e.g., for LLM API calls) should be deferred to a dedicated, comprehensive testing phase.
    *   **Iterative Testing:** All tests created or modified for a given step **must be run and must pass** before moving to the next step in the plan. If multiple unrelated tests fail, address them one at a time, running only the specific failed test case (e.g., using `pytest path/to/file.py::test_name`) until it passes.
    *   **Final Documentation Review:** The final step of every implementation plan must be to review and update the documentation. The plan should explicitly state: "When the implementation is complete and all tests are passing, review `.clinerules/documentation_guide.md` to identify all documents that require updates, read them, and then propose the necessary changes."

## 4. Phase 3: Implementation

This phase is focused on executing the approved implementation plan from Phase 2.

1.  **Execute the Plan:** Follow the implementation plan step-by-step.
2.  **Tool Utilization:** Use the available tools correctly and efficiently to make the necessary code changes, run tests, and interact with the file system.
3.  **Adherence to Plan:** Do not deviate from the agreed-upon plan. If an unforeseen issue arises, pause implementation, and return to the Planning & Design phase to discuss and revise the plan.
