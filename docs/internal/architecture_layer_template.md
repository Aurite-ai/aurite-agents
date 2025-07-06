# Layer X: [Layer Name]

**Version:** [e.g., 1.0]
**Date:** [YYYY-MM-DD]

## 1. Overview

*   Provide a high-level summary of this layer's purpose and primary responsibilities within the framework.
*   Describe the key features or capabilities this layer provides.
*   Mention its position relative to adjacent layers (what it consumes, what consumes it).

## 2. Relevant Files

*   List the core source code files and primary classes/modules belonging to this layer.
*   Briefly describe the main responsibility of each file/class in the context of the layer.

| File Path                      | Primary Class(es)/Modules | Core Responsibility                   |
| :----------------------------- | :------------------------ | :------------------------------------ |
| `src/[path]/[file_name].py`    | `[ClassName]`             | [Brief description of responsibility] |
| `src/[path]/[another_file].py` | `[AnotherClass]`          | [Brief description of responsibility] |
| ...                            | ...                       | ...                                   |

## 3. Functionality

Describe how the components within this layer work together and individually.

**3.1. Multi-File Interactions & Core Flows:**

*   Describe the key workflows or sequences of operations that involve multiple files/classes within this layer.
*   Explain how this layer interacts with adjacent layers (e.g., receiving requests, calling methods in other layers).
*   Use bullet points or numbered lists for clarity.
*   Example Flow: Initialization, Request Handling, Data Processing, etc.

**3.2. Individual File Functionality:**

*   Provide more detailed descriptions of the responsibilities and logic within each key file/class listed in Section 2.
*   Focus on public methods, important internal logic, and state management.
*   **`[file_name].py` (`[ClassName]`):**
    *   [Detailed responsibility 1]
    *   [Detailed responsibility 2]
    *   ...
*   **`[another_file].py` (`[AnotherClass]`):**
    *   [Detailed responsibility 1]
    *   ...

## 4. Testing

**4.A. Testing Overview:**

*   **Execution:** How are tests for this layer typically run? (e.g., `pytest -m [marker_name]`)
*   **Location:** Where do the tests for this layer reside? (e.g., `tests/[layer_dir]/`)
*   **Approach:** Describe the general testing strategy (e.g., mix of unit and integration tests, focus areas).

**4.B. Testing Infrastructure:**

*   List relevant testing infrastructure components used by this layer's tests.
*   **`tests/conftest.py`:** Mention any relevant global fixtures or configurations.
*   **`tests/[layer_dir]/conftest.py` (if exists):** Describe layer-specific fixtures.
*   **Key Fixtures:** List important fixtures (e.g., `mock_dependency`, `initialized_layer_component`) and their purpose.
*   **Mocks:** Describe common mocks used (e.g., `unittest.mock.Mock`, specific mocked classes).
*   **Markers:** Mention relevant pytest markers used (e.g., `anyio`, `unit`, `integration`).

**4.C. Testing Coverage:**

*   Map the core functionalities (from Section 3) to the relevant source files and the test files that verify them.
*   Indicate the current testing status or coverage level for each functionality.

| Functionality                              | Relevant File(s)               | Test File(s) / Status                                                                    |
| :----------------------------------------- | :----------------------------- | :--------------------------------------------------------------------------------------- |
| [Functionality Description 1 from Sec 3]   | `src/[path]/[file_name].py`    | `tests/[layer_dir]/test_[file_name].py` / Status: [e.g., Good, Partial, Missing]         |
| [Functionality Description 2 from Sec 3]   | `src/[path]/[another_file].py` | `tests/[layer_dir]/test_[another_file]_unit.py` / Status: [e.g., Good, Partial, Missing] |
| [Multi-file Flow Description from Sec 3.1] | `[file1].py`, `[file2].py`     | `tests/[layer_dir]/test_[integration_scenario].py` / Status: [e.g., Good, Partial]       |
| ...                                        | ...                            | ...                                                                                      |

**4.D. Remaining Testing Steps:**

*   List specific tests or test areas that still need to be implemented to achieve desired coverage.
*   Be specific about what needs to be tested (e.g., edge cases, error handling, specific methods).
*   This section shrinks as coverage in 4.C improves.
1.  Implement unit tests for `[ClassName].[method_name]` focusing on [specific aspect].
2.  Add integration tests for the interaction between `[ClassA]` and `[ClassB]` during [specific scenario].
3.  Verify error handling in `[function_name]` for [specific error condition].
4.  ...
