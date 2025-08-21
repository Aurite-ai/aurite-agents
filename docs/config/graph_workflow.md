# Graph Workflow Configuration

Graph workflows provide a flexible way to execute components in a non-linear, dependency-based order. They are perfect for complex tasks that require conditional execution, parallel processing, or dynamic routing based on component outputs, such as "run the data-validation agent, and if it passes, run both the analysis agent and the reporting agent in parallel."

A graph workflow configuration is a JSON or YAML object with a `type` field set to `"graph_workflow"`.

<!-- prettier-ignore -->
!!! info "How It Works"
    When you execute a graph workflow, the framework builds a dependency graph from the `nodes` and `edges` definitions. Components are executed when their dependencies are satisfied, allowing for parallel execution and conditional branching. The workflow continues until all reachable nodes have been processed or a terminal condition is met.

---

## Schema

The `GraphWorkflowConfig` defines the structure for a graph workflow.

=== ":material-format-list-bulleted-type: Core Fields"

    These fields define the fundamental properties of the workflow.

    | Field             | Type                     | Required | Description                                                                                                                         |
    | ----------------- | ------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
    | `name`            | `string`                 | Yes      | A unique identifier for the workflow. This name is used to run the workflow from the CLI or API.                                    |
    | `description`     | `string`                 | No       | A brief, human-readable description of what the workflow accomplishes.                                                              |
    | `nodes`           | `list[GraphWorkflowNode]` | Yes      | A list of nodes (components) in the graph. See "Nodes Configuration" below for details.                                            |
    | `edges`           | `list[GraphWorkflowEdge]` | Yes      | A list of edges defining dependencies between nodes. See "Edges Configuration" below for details.                                   |
    | `include_history` | `boolean`                | `None`   | If set, overrides the `include_history` setting for all agents in the workflow, forcing them all to either save or discard history. |
    | `include_logging` | `boolean`                | `None`   | If set, overrides the `include_logging` setting for all agents in the workflow, forcing them all to either enable or disable logging. |

=== ":material-sitemap: Nodes Configuration"

    Each node in the graph represents a component to execute. Nodes are defined as objects with the following structure:

    | Field     | Type     | Required | Description                                                                                    |
    | --------- | -------- | -------- | ---------------------------------------------------------------------------------------------- |
    | `node_id` | `string` | Yes      | A unique identifier for this node within the graph. Used to reference the node in edges.      |
    | `name`    | `string` | Yes      | The name of the component to execute (must match an existing agent or workflow configuration). |
    | `type`    | `string` | Yes      | The type of component. Currently only `"agent"` is supported.                                 |

    ```json
    "nodes": [
      {
        "node_id": "validation",
        "name": "data-validator-agent",
        "type": "agent"
      },
      {
        "node_id": "analysis",
        "name": "analysis-agent",
        "type": "agent"
      }
    ]
    ```

=== ":material-arrow-right: Edges Configuration"

    Edges define the dependencies and execution order between nodes. Each edge specifies that one node must complete before another can start.

    | Field  | Type     | Required | Description                                                                    |
    | ------ | -------- | -------- | ------------------------------------------------------------------------------ |
    | `from` | `string` | Yes      | The `node_id` of the source node (must complete before the target can start). |
    | `to`   | `string` | Yes      | The `node_id` of the target node (will receive input from the source node).   |

    ```json
    "edges": [
      {
        "from": "validation",
        "to": "analysis"
      },
      {
        "from": "validation",
        "to": "reporting"
      }
    ]
    ```

    **Data Flow:** When a node completes, its output is passed as input to all nodes that depend on it. If a node has multiple predecessors, their outputs are concatenated together as the input.

---

## :material-code-json: Configuration Examples

=== "Simple Parallel Processing"

    This example shows a workflow where data validation runs first, then both analysis and reporting run in parallel.

    ```json
    {
      "type": "graph_workflow",
      "name": "parallel-data-pipeline",
      "description": "Validates data, then runs analysis and reporting in parallel.",
      "nodes": [
        {
          "node_id": "validate",
          "name": "data-validator-agent",
          "type": "agent"
        },
        {
          "node_id": "analyze",
          "name": "analysis-agent",
          "type": "agent"
        },
        {
          "node_id": "report",
          "name": "reporting-agent",
          "type": "agent"
        }
      ],
      "edges": [
        {
          "from": "validate",
          "to": "analyze"
        },
        {
          "from": "validate",
          "to": "report"
        }
      ]
    }
    ```

=== "Diamond Pattern with Convergence"

    This example demonstrates a diamond-shaped workflow where processing splits into parallel paths and then converges.

    ```json
    {
      "type": "graph_workflow",
      "name": "diamond-processing-flow",
      "description": "Splits processing into parallel paths and converges the results.",
      "nodes": [
        {
          "node_id": "input",
          "name": "input-processor-agent",
          "type": "agent"
        },
        {
          "node_id": "path_a",
          "name": "path-a-agent",
          "type": "agent"
        },
        {
          "node_id": "path_b",
          "name": "path-b-agent",
          "type": "agent"
        },
        {
          "node_id": "merge",
          "name": "merge-results-agent",
          "type": "agent"
        }
      ],
      "edges": [
        {
          "from": "input",
          "to": "path_a"
        },
        {
          "from": "input",
          "to": "path_b"
        },
        {
          "from": "path_a",
          "to": "merge"
        },
        {
          "from": "path_b",
          "to": "merge"
        }
      ]
    }
    ```
