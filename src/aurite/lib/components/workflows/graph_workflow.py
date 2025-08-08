"""
Executor for Graph Workflows with parallel node execution.
"""

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Optional

import networkx as nx

from ...models.api.responses import GraphWorkflowExecutionResult, GraphWorkflowNodeResult

# Relative imports assuming this file is in src/workflows/
from ...models.config.components import GraphWorkflowConfig

# Import LLM client and Facade for type hinting only
if TYPE_CHECKING:
    from ...execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)


class GraphWorkflowExecutor:
    """
    Executes a graph workflow defined by a GraphWorkflowConfig.
    """

    def __init__(
        self,
        config: GraphWorkflowConfig,
        engine: "AuriteEngine",
    ):
        """
        Initializes the GraphWorkflowExecutor.

        Args:
            config: The configuration for the specific workflow to execute.
            engine: The AuriteEngine instance, used to run agents.
        """
        if not isinstance(config, GraphWorkflowConfig):
            raise TypeError("config must be an instance of GraphWorkflowConfig")
        if not engine:
            raise ValueError("AuriteEngine instance is required.")

        self.config = config
        self.engine = engine

        self._build_and_verify_graph()

        logger.debug(f"GraphWorkflowExecutor initialized for workflow: {self.config.name}")

    def _build_and_verify_graph(self):
        node_config_map = {node.node_id: node for node in self.config.nodes}
        for edge in self.config.edges:
            if edge.from_node not in node_config_map:
                raise ValueError(f"Edge {edge} references undefined node: {edge.from_node}")
            if edge.to_node not in node_config_map:
                raise ValueError(f"Edge {edge} references undefined node: {edge.to_node}")

        self.graph = nx.DiGraph()

        self.graph.add_nodes_from([n.node_id for n in self.config.nodes])
        self.graph.add_edges_from([(e.from_node, e.to_node) for e in self.config.edges])

        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("Graph workflow is not acyclic")

    async def execute(
        self,
        initial_input: str,
        session_id: Optional[str] = None,
        base_session_id: Optional[str] = None,
        force_logging: Optional[bool] = None,
    ) -> GraphWorkflowExecutionResult:
        """
        Executes the configured graph workflow.

        Args:
            initial_input: The initial input message for the initial node(s).
            session_id: Optional session ID to use for conversation history tracking.
            base_session_id: The original, user-provided session ID for the workflow.

        Returns:
            A GraphWorkflowExecutionResult object containing the final status,
            results for each node, the final output, and any error message.
        """
        workflow_name = self.config.name

        if not session_id and self.config.include_history:
            session_id = f"workflow-{uuid.uuid4().hex[:8]}"
            logger.info(f"Auto-generated session_id for graph workflow '{workflow_name}': {session_id}")

        logger.info(f"Executing graph workflow: '{workflow_name}' with session_id: {session_id}")

        node_results: dict[str, GraphWorkflowNodeResult] = {}

        try:
            # Create a mapping from node_id to node config for easy lookup
            node_config_map = {node.node_id: node for node in self.config.nodes}

            # Track which nodes are ready to execute (all predecessors completed)
            completed_nodes = set()
            running_tasks = {}  # node_id -> asyncio.Task

            # Find all nodes with in degree 0 and start them as asyncio tasks
            start_nodes = [node_id for node_id in self.graph.nodes if self.graph.in_degree[node_id] == 0]

            if not start_nodes:
                raise ValueError("Graph workflow has no start nodes (nodes with in-degree 0)")

            logger.debug(f"Starting execution of {len(start_nodes)} initial nodes: {start_nodes}")

            # Start initial nodes
            for node_id in start_nodes:
                node_config = node_config_map[node_id]
                task = asyncio.create_task(
                    self._execute_node(node_config, initial_input, session_id, base_session_id, force_logging)
                )
                running_tasks[node_id] = task

            # Process nodes as they complete
            while running_tasks or len(completed_nodes) < len(self.graph.nodes):
                if not running_tasks:
                    # No tasks running but not all nodes completed - this shouldn't happen in a valid DAG
                    remaining_nodes = set(self.graph.nodes) - completed_nodes
                    raise ValueError(f"Workflow execution stalled. Remaining nodes: {remaining_nodes}")

                # Wait for at least one task to complete
                done, pending = await asyncio.wait(running_tasks.values(), return_when=asyncio.FIRST_COMPLETED)

                # Process completed tasks
                for task in done:
                    # Find which node this task belongs to
                    completed_node_id = None
                    for node_id, node_task in running_tasks.items():
                        if node_task == task:
                            completed_node_id = node_id
                            break

                    if completed_node_id is None:
                        raise RuntimeError("Could not identify completed task")

                    # Get the result and handle any exceptions
                    try:
                        result = await task
                        node_config = node_config_map[completed_node_id]

                        # Store the result
                        node_results[completed_node_id] = GraphWorkflowNodeResult(
                            name=node_config.name, type=node_config.type, result=result
                        )

                        completed_nodes.add(completed_node_id)
                        del running_tasks[completed_node_id]

                        logger.debug(f"Node '{completed_node_id}' completed successfully")

                        # Check if this completion enables any new nodes to run
                        for successor_node_id in self.graph.successors(completed_node_id):
                            if successor_node_id not in completed_nodes and successor_node_id not in running_tasks:
                                # Check if all predecessors of this successor are completed
                                predecessors = list(self.graph.predecessors(successor_node_id))
                                if all(pred in completed_nodes for pred in predecessors):
                                    # All predecessors completed, we can start this node

                                    # Concatenate outputs from all predecessors as input
                                    predecessor_outputs = []
                                    for pred_id in predecessors:
                                        if pred_id in node_results:
                                            # Extract the text result from the node result
                                            pred_result = node_results[pred_id].result
                                            if isinstance(pred_result, str):
                                                predecessor_outputs.append(pred_result)
                                            else:
                                                # If it's not a string, convert to string representation
                                                predecessor_outputs.append(str(pred_result))

                                    # Concatenate all predecessor outputs
                                    combined_input = "\n\n".join(predecessor_outputs) if predecessor_outputs else ""

                                    # Start the successor node
                                    successor_config = node_config_map[successor_node_id]
                                    task = asyncio.create_task(
                                        self._execute_node(
                                            successor_config, combined_input, session_id, base_session_id, force_logging
                                        )
                                    )
                                    running_tasks[successor_node_id] = task
                                    logger.debug(
                                        f"Started node '{successor_node_id}' with input from predecessors: {predecessors}"
                                    )

                    except Exception as e:
                        logger.error(f"Node '{completed_node_id}' failed with error: {e}")
                        # Clean up remaining tasks
                        for remaining_task in running_tasks.values():
                            remaining_task.cancel()

                        return GraphWorkflowExecutionResult(
                            workflow_name=workflow_name,
                            status="failed",
                            node_results=node_results,
                            final_output=None,
                            error=f"Node '{completed_node_id}' failed: {str(e)}",
                            session_id=session_id,
                        )

            # All nodes completed successfully
            # Find final output nodes (nodes with out-degree 0) and combine their results
            final_outputs = {
                node_id: node_results[node_id].result
                for node_id in self.graph.nodes
                if self.graph.out_degree[node_id] == 0
            }

            logger.info(f"Graph workflow '{workflow_name}' completed successfully")

            return GraphWorkflowExecutionResult(
                workflow_name=workflow_name,
                status="completed",
                node_results=node_results,
                final_output=final_outputs,
                error=None,
                session_id=session_id,
            )

        except Exception as e:
            logger.error(f"Error within graph workflow execution: {e}")
            return GraphWorkflowExecutionResult(
                workflow_name=workflow_name,
                status="failed",
                node_results=node_results,
                final_output=None,
                error=f"Workflow setup error: {str(e)}",
                session_id=session_id,
            )

    async def _execute_node(
        self,
        node_config,
        input_text: str,
        session_id: Optional[str],
        base_session_id: Optional[str],
        force_logging: Optional[bool],
    ) -> str:
        """
        Execute a single node in the graph workflow.

        Args:
            node_config: The GraphWorkflowNode configuration
            input_text: The input text for this node
            session_id: Session ID for conversation history
            base_session_id: Base session ID for the workflow
            force_logging: Whether to force logging

        Returns:
            The text output from the node execution
        """
        logger.info(f"Executing node '{node_config.node_id}' ({node_config.name}) with input: {input_text[:200]}...")

        try:
            if node_config.type == "agent":
                # Execute the agent using the engine
                agent_result = await self.engine.run_agent(
                    agent_name=node_config.name,
                    user_message=input_text,
                    session_id=f"{session_id}-{node_config.node_id}" if session_id else None,
                    force_include_history=self.config.include_history,
                    base_session_id=base_session_id,
                    force_logging=force_logging,
                )

                # Check if the agent execution was successful
                if agent_result.status != "success":
                    error_detail = agent_result.error_message or f"Agent finished with status: {agent_result.status}"
                    raise Exception(f"Agent '{node_config.name}' failed: {error_detail}")

                if agent_result.final_response is None:
                    raise Exception(f"Agent '{node_config.name}' succeeded but produced no response.")

                # Return the text content from the agent's response
                return agent_result.final_response.content or ""

            else:
                # For future extension - other node types like workflows
                raise ValueError(f"Unsupported node type: {node_config.type}")

        except Exception as e:
            logger.error(f"Error executing node '{node_config.node_id}': {e}")
            raise
