"""
BaseAgent class for implementing dynamic agents with full agency.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Set, Tuple
import logging
import time
import json
import uuid

from ..host.host import MCPHost

logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Types of tools an agent can use"""

    INFORMATION = auto()  # Getting information (e.g., search, retrieve)
    ACTION = auto()  # Taking actions (e.g., send email, create task)
    REASONING = auto()  # Reasoning about information (e.g., analyze)
    UTILITY = auto()  # Utility functions (e.g., date/time calculations)


@dataclass
class AgentTool:
    """
    Represents a tool available to an agent.
    Wraps the MCP tool with metadata for agent decision-making.
    """

    name: str
    description: str
    tool_type: ToolType
    parameters: Dict[str, Any] = field(default_factory=dict)
    example_uses: List[Dict[str, Any]] = field(default_factory=list)
    usage_cost: float = 1.0  # Relative cost for planning purposes
    allowed_in_contexts: Set[str] = field(default_factory=set)


@dataclass
class MemoryItem:
    """An item in the agent's memory"""

    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    tags: Set[str] = field(default_factory=set)
    ttl: Optional[float] = None  # Time to live in seconds, None for permanent

    def is_expired(self) -> bool:
        """Check if the memory item has expired"""
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl


@dataclass
class PlanStep:
    """A step in a plan"""

    tool_name: str
    parameters: Dict[str, Any]
    expected_result: Optional[str] = None
    description: str = ""
    is_optional: bool = False
    fallback_steps: List["PlanStep"] = field(default_factory=list)


@dataclass
class Plan:
    """A plan for executing a task"""

    steps: List[PlanStep]
    goal: str
    sub_goals: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    current_step_index: int = 0

    def get_current_step(self) -> Optional[PlanStep]:
        """Get the current step in the plan"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance(self):
        """Advance to the next step in the plan"""
        self.current_step_index += 1

    def is_complete(self) -> bool:
        """Check if the plan is complete"""
        return self.current_step_index >= len(self.steps)


@dataclass
class AgentResult:
    """Result of an agent execution"""

    success: bool
    output: Any
    execution_time: float
    tool_calls: int = 0
    plan: Optional[Plan] = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentMemory:
    """
    Memory system for agents.
    Stores and retrieves information used by the agent.
    """

    def __init__(self, max_items: int = 1000):
        self.items: Dict[str, MemoryItem] = {}
        self.max_items = max_items
        self.tags_index: Dict[str, Set[str]] = {}  # tag -> set of keys

    def store(
        self,
        key: str,
        value: Any,
        tags: Optional[Set[str]] = None,
        ttl: Optional[float] = None,
    ) -> str:
        """
        Store a value in memory.

        Args:
            key: The key to store the value under, or '' to generate a random key
            value: The value to store
            tags: Optional set of tags for categorization and search
            ttl: Optional time-to-live in seconds

        Returns:
            The key the value was stored under
        """
        # Generate key if not provided
        if not key:
            key = str(uuid.uuid4())

        # Create memory item
        item = MemoryItem(
            key=key,
            value=value,
            timestamp=time.time(),
            tags=set(tags) if tags else set(),
            ttl=ttl,
        )

        # Store item
        self.items[key] = item

        # Update tag indices
        for tag in item.tags:
            if tag not in self.tags_index:
                self.tags_index[tag] = set()
            self.tags_index[tag].add(key)

        # Enforce max items limit by removing oldest items
        if len(self.items) > self.max_items:
            self._remove_oldest_items(len(self.items) - self.max_items)

        return key

    def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from memory by key.

        Args:
            key: The key to retrieve

        Returns:
            The stored value, or None if not found or expired
        """
        # Check if item exists
        if key not in self.items:
            return None

        item = self.items[key]

        # Check if expired
        if item.is_expired():
            self._remove_item(key)
            return None

        return item.value

    def search_by_tags(
        self, tags: Set[str], match_all: bool = True
    ) -> List[Tuple[str, Any]]:
        """
        Search for items by tags.

        Args:
            tags: Set of tags to search for
            match_all: If True, all tags must match; if False, any tag can match

        Returns:
            List of (key, value) tuples for matching items
        """
        # Find matching keys
        matching_keys = set()

        if match_all:
            # All tags must match
            if not tags:
                return []

            # Start with keys from first tag
            first_tag = next(iter(tags))
            if first_tag not in self.tags_index:
                return []

            matching_keys = self.tags_index[first_tag].copy()

            # Intersect with keys from other tags
            for tag in tags:
                if tag not in self.tags_index:
                    return []
                matching_keys &= self.tags_index[tag]
        else:
            # Any tag can match
            for tag in tags:
                if tag in self.tags_index:
                    matching_keys |= self.tags_index[tag]

        # Retrieve items and filter out expired ones
        results = []
        for key in matching_keys:
            if key in self.items and not self.items[key].is_expired():
                results.append((key, self.items[key].value))

        return results

    def search_by_value(self, query: str, exact: bool = False) -> List[Tuple[str, Any]]:
        """
        Search for items by value.

        Args:
            query: The query string to search for
            exact: If True, the query must match exactly; if False, it can be a substring

        Returns:
            List of (key, value) tuples for matching items
        """
        results = []

        for key, item in list(self.items.items()):
            # Skip expired items
            if item.is_expired():
                self._remove_item(key)
                continue

            # Convert value to string for searching
            value_str = str(item.value)

            # Check for match
            if exact and value_str == query:
                results.append((key, item.value))
            elif not exact and query.lower() in value_str.lower():
                results.append((key, item.value))

        return results

    def clear(self):
        """Clear all items from memory"""
        self.items.clear()
        self.tags_index.clear()

    def _remove_item(self, key: str):
        """Remove an item from memory and update indices"""
        if key not in self.items:
            return

        # Remove from tag indices
        item = self.items[key]
        for tag in item.tags:
            if tag in self.tags_index and key in self.tags_index[tag]:
                self.tags_index[tag].remove(key)
                # Clean up empty tag sets
                if not self.tags_index[tag]:
                    del self.tags_index[tag]

        # Remove item
        del self.items[key]

    def _remove_oldest_items(self, count: int):
        """Remove the oldest items from memory"""
        # Sort items by timestamp
        sorted_items = sorted(self.items.items(), key=lambda x: x[1].timestamp)

        # Remove oldest items
        for key, _ in sorted_items[:count]:
            self._remove_item(key)


class AgentPlanner:
    """
    Planner for agents.
    Creates and manages plans for completing tasks.
    """

    def __init__(self, host: MCPHost):
        self.host = host

    async def create_plan(
        self, task: str, available_tools: List[AgentTool], context: Dict[str, Any]
    ) -> Plan:
        """
        Create a plan for completing a task.

        Args:
            task: The task to plan for
            available_tools: The tools available to the agent
            context: The current context

        Returns:
            A plan for completing the task
        """
        # This is where we would use an LLM to generate a plan
        # For now, we'll create a simple example plan

        # Serialize tools information for the LLM
        tools_info = []
        for tool in available_tools:
            tools_info.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "type": tool.tool_type.name,
                    "parameters": tool.parameters,
                    "examples": tool.example_uses,
                }
            )

        # Generate JSON input for the planning LLM call
        planning_input = {
            "task": task,
            "available_tools": tools_info,
            "context": context,
        }

        # Call the planning tool/prompt through the host
        try:
            # This assumes we have a 'create_plan' prompt registered in the host
            plan_result = await self.host.execute_prompt(
                name="create_plan",
                arguments={"input": json.dumps(planning_input)},
                client_id="planning_server",  # This should be an actual client_id
            )

            # Parse the plan result
            plan_data = json.loads(plan_result.text)

            # Create Plan and PlanStep objects
            steps = []
            for step_data in plan_data.get("steps", []):
                fallback_steps = []
                for fallback_data in step_data.get("fallback_steps", []):
                    fallback_steps.append(
                        PlanStep(
                            tool_name=fallback_data["tool_name"],
                            parameters=fallback_data["parameters"],
                            expected_result=fallback_data.get("expected_result"),
                            description=fallback_data.get("description", ""),
                            is_optional=fallback_data.get("is_optional", False),
                        )
                    )

                steps.append(
                    PlanStep(
                        tool_name=step_data["tool_name"],
                        parameters=step_data["parameters"],
                        expected_result=step_data.get("expected_result"),
                        description=step_data.get("description", ""),
                        is_optional=step_data.get("is_optional", False),
                        fallback_steps=fallback_steps,
                    )
                )

            return Plan(
                steps=steps,
                goal=plan_data.get("goal", task),
                sub_goals=plan_data.get("sub_goals", []),
                context=context,
            )

        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            # Return a minimal plan
            return Plan(steps=[], goal=task, context=context)

    async def update_plan(
        self, plan: Plan, observation: Any, available_tools: List[AgentTool]
    ) -> Plan:
        """
        Update a plan based on new observations.

        Args:
            plan: The current plan
            observation: The new observation
            available_tools: The tools available to the agent

        Returns:
            The updated plan
        """
        # This is where we would use an LLM to update the plan
        # For now, we'll return the original plan
        return plan


class ToolRegistry:
    """
    Registry of tools available to an agent.
    Provides methods for discovering, registering, and filtering tools.
    """

    def __init__(self, host: MCPHost):
        self.host = host
        self.tools: Dict[str, AgentTool] = {}

    async def initialize(self):
        """Initialize the tool registry from the host"""
        logger.info("Initializing tool registry")

        # Discover tools from host
        await self.discover_tools()

    async def discover_tools(self) -> List[AgentTool]:
        """
        Discover tools available through the host.

        Returns:
            List of discovered tools
        """
        # Get tools from host
        host_tools = list(self.host._tools.values())

        discovered = []
        for tool in host_tools:
            # Convert MCP tool to AgentTool
            agent_tool = AgentTool(
                name=tool.name,
                description=tool.description,
                tool_type=self._infer_tool_type(tool),
                parameters={p.name: p.schema for p in tool.parameters}
                if hasattr(tool, "parameters")
                else {},
                example_uses=[],  # We don't have examples in the MCP tool schema
            )

            # Register the tool
            self.tools[tool.name] = agent_tool
            discovered.append(agent_tool)

        logger.info(f"Discovered {len(discovered)} tools")
        return discovered

    def _infer_tool_type(self, tool) -> ToolType:
        """
        Infer the type of a tool based on its name and description.

        Args:
            tool: The MCP tool

        Returns:
            The inferred tool type
        """
        name = tool.name.lower()
        description = tool.description.lower() if hasattr(tool, "description") else ""

        # Look for action-related keywords
        action_keywords = {"create", "send", "update", "delete", "post", "write"}
        for keyword in action_keywords:
            if keyword in name or keyword in description:
                return ToolType.ACTION

        # Look for information-related keywords
        info_keywords = {"get", "read", "list", "search", "find", "query"}
        for keyword in info_keywords:
            if keyword in name or keyword in description:
                return ToolType.INFORMATION

        # Look for reasoning-related keywords
        reasoning_keywords = {"analyze", "calculate", "evaluate", "predict"}
        for keyword in reasoning_keywords:
            if keyword in name or keyword in description:
                return ToolType.REASONING

        # Default to utility
        return ToolType.UTILITY

    def register_tool(self, tool: AgentTool):
        """Register a tool with the registry"""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[AgentTool]:
        """Get a tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> List[AgentTool]:
        """List all registered tools"""
        return list(self.tools.values())

    def filter_tools(self, criteria: Dict[str, Any]) -> List[AgentTool]:
        """
        Filter tools based on criteria.

        Args:
            criteria: Dictionary of criteria to filter by

        Returns:
            List of tools matching the criteria
        """
        results = list(self.tools.values())

        # Filter by tool type
        if "tool_type" in criteria:
            tool_type = criteria["tool_type"]
            results = [t for t in results if t.tool_type == tool_type]

        # Filter by context
        if "context" in criteria:
            context = criteria["context"]
            results = [
                t
                for t in results
                if not t.allowed_in_contexts or context in t.allowed_in_contexts
            ]

        # Filter by search terms
        if "search" in criteria:
            search = criteria["search"].lower()
            results = [
                t
                for t in results
                if search in t.name.lower() or search in t.description.lower()
            ]

        return results


class BaseAgent(ABC):
    """
    Base class for implementing dynamic agents with full agency.
    These agents have the ability to decide both how to use tools and which tools to use.
    """

    def __init__(self, host: MCPHost, name: str = "unnamed_agent"):
        self.host = host
        self.name = name
        self.memory = AgentMemory()
        self.tool_registry = ToolRegistry(host)
        self.planner = AgentPlanner(host)
        self.active_plan: Optional[Plan] = None
        self.execution_history: List[Dict[str, Any]] = []
        self.max_tool_calls: int = 50  # Prevent infinite loops

    async def initialize(self):
        """Initialize the agent"""
        logger.info(f"Initializing agent: {self.name}")

        # Initialize components
        await self.tool_registry.initialize()

    async def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Execute a task with the agent.

        Args:
            task: The task to execute
            context: Optional initial context

        Returns:
            The result of the execution
        """
        # Initialize execution
        if context is None:
            context = {}

        start_time = time.time()
        tool_calls = 0

        logger.info(f"Agent '{self.name}' executing task: {task}")

        try:
            # Create initial plan
            available_tools = self.tool_registry.list_tools()
            self.active_plan = await self.planner.create_plan(
                task, available_tools, context
            )

            # Execute plan
            result = await self._execute_plan(context)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Create and return result
            return AgentResult(
                success=True,
                output=result,
                execution_time=execution_time,
                tool_calls=tool_calls,
                plan=self.active_plan,
            )

        except Exception as e:
            # Calculate execution time
            execution_time = time.time() - start_time

            logger.error(f"Error executing task: {e}")

            # Create and return error result
            return AgentResult(
                success=False,
                output=str(e),
                execution_time=execution_time,
                tool_calls=tool_calls,
                plan=self.active_plan,
                error=e,
            )

    async def _execute_plan(self, context: Dict[str, Any]) -> Any:
        """
        Execute the current plan.

        Args:
            context: The current context

        Returns:
            The result of the plan execution
        """
        # Validate we have a plan
        if not self.active_plan or not self.active_plan.steps:
            return {"error": "No plan available"}

        # Keep track of tool calls to prevent infinite loops
        tool_calls = 0

        # Execute steps until plan is complete
        results = []
        while not self.active_plan.is_complete() and tool_calls < self.max_tool_calls:
            # Get current step
            current_step = self.active_plan.get_current_step()

            # Execute step
            try:
                logger.info(f"Executing step: {current_step.tool_name}")
                step_result = await self.host.call_tool(
                    current_step.tool_name, current_step.parameters
                )

                # Record execution
                self.execution_history.append(
                    {
                        "step": current_step,
                        "result": step_result,
                        "success": True,
                        "timestamp": time.time(),
                    }
                )

                # Store result in context and memory
                if isinstance(step_result, list) and step_result:
                    context[f"result_{current_step.tool_name}"] = (
                        step_result[0].text
                        if hasattr(step_result[0], "text")
                        else str(step_result[0])
                    )
                    self.memory.store(
                        key=f"result_{current_step.tool_name}_{int(time.time())}",
                        value=step_result,
                        tags={current_step.tool_name, "results"},
                    )
                    results.append(step_result)

                # Advance plan
                self.active_plan.advance()

            except Exception as e:
                logger.warning(f"Error executing step: {e}")

                # Record execution
                self.execution_history.append(
                    {
                        "step": current_step,
                        "error": str(e),
                        "success": False,
                        "timestamp": time.time(),
                    }
                )

                # Try fallback steps if any
                fallback_executed = False
                for fallback in current_step.fallback_steps:
                    try:
                        logger.info(f"Executing fallback step: {fallback.tool_name}")
                        fallback_result = await self.host.call_tool(
                            fallback.tool_name, fallback.parameters
                        )

                        # Record execution
                        self.execution_history.append(
                            {
                                "step": fallback,
                                "result": fallback_result,
                                "success": True,
                                "timestamp": time.time(),
                            }
                        )

                        # Store result in context and memory
                        if isinstance(fallback_result, list) and fallback_result:
                            context[f"result_{fallback.tool_name}"] = (
                                fallback_result[0].text
                                if hasattr(fallback_result[0], "text")
                                else str(fallback_result[0])
                            )
                            self.memory.store(
                                key=f"result_{fallback.tool_name}_{int(time.time())}",
                                value=fallback_result,
                                tags={fallback.tool_name, "results"},
                            )
                            results.append(fallback_result)

                        # Mark as executed
                        fallback_executed = True
                        break

                    except Exception as fallback_error:
                        logger.warning(
                            f"Error executing fallback step: {fallback_error}"
                        )

                        # Record execution
                        self.execution_history.append(
                            {
                                "step": fallback,
                                "error": str(fallback_error),
                                "success": False,
                                "timestamp": time.time(),
                            }
                        )

                # Skip step if it's optional or a fallback was executed
                if current_step.is_optional or fallback_executed:
                    self.active_plan.advance()
                else:
                    # Step failed and was required, update plan
                    available_tools = self.tool_registry.list_tools()
                    self.active_plan = await self.planner.update_plan(
                        self.active_plan,
                        {"error": str(e), "step": current_step.tool_name},
                        available_tools,
                    )

            # Increment tool calls counter
            tool_calls += 1

        # Check if we reached the maximum number of tool calls
        if tool_calls >= self.max_tool_calls:
            logger.warning(
                f"Reached maximum number of tool calls ({self.max_tool_calls})"
            )

        # Return final results
        return results

    @abstractmethod
    async def select_tools(self, task: str, context: Dict[str, Any]) -> List[AgentTool]:
        """
        Select tools for a task.
        This method should be implemented by subclasses to provide custom tool selection logic.

        Args:
            task: The task to select tools for
            context: The current context

        Returns:
            List of selected tools
        """
        pass

    @abstractmethod
    async def evaluate_result(self, result: Any) -> Dict[str, Any]:
        """
        Evaluate the result of a task.
        This method should be implemented by subclasses to provide custom result evaluation logic.

        Args:
            result: The result to evaluate

        Returns:
            Evaluation metrics
        """
        pass

    async def shutdown(self):
        """Clean up resources used by the agent"""
        logger.info(f"Shutting down agent: {self.name}")

        # Clear memory
        self.memory.clear()
