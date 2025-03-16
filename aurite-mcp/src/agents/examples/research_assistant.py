"""
Example implementation of a research assistant using BaseAgent.
"""

from typing import Dict, List, Any
import logging
import re

from ...host.host import MCPHost
from ..base_agent import BaseAgent, AgentTool, ToolType

logger = logging.getLogger(__name__)


class ResearchAssistantAgent(BaseAgent):
    """
    A research assistant agent that can search for information,
    analyze documents, and generate summaries and reports.
    """

    def __init__(self, host: MCPHost):
        super().__init__(host, name="research_assistant")

        # Define tool preferences
        self.preferred_tools = {
            "search": ["web_search", "document_search", "database_query"],
            "analysis": ["extract_entities", "analyze_sentiment", "classify_text"],
            "generation": ["generate_text", "create_summary", "format_report"],
        }

    async def select_tools(self, task: str, context: Dict[str, Any]) -> List[AgentTool]:
        """
        Select tools for a research task.

        Args:
            task: The research task to select tools for
            context: The current context

        Returns:
            List of selected tools
        """
        # Available tools from registry
        available_tools = self.tool_registry.list_tools()

        # Initialize selected tools
        selected_tools = []

        # Parse task to determine required tool categories
        task_lower = task.lower()
        categories = set()

        # Detect search-related tasks
        search_keywords = ["find", "search", "look for", "locate", "identify"]
        if any(keyword in task_lower for keyword in search_keywords):
            categories.add("search")

        # Detect analysis-related tasks
        analysis_keywords = ["analyze", "examine", "evaluate", "assess", "compare"]
        if any(keyword in task_lower for keyword in analysis_keywords):
            categories.add("analysis")

        # Detect generation-related tasks
        generation_keywords = ["write", "create", "generate", "summarize", "prepare"]
        if any(keyword in task_lower for keyword in generation_keywords):
            categories.add("generation")

        # If no categories detected, assume all are needed
        if not categories:
            categories = {"search", "analysis", "generation"}

        # Select tools from each needed category
        for category in categories:
            preferred = self.preferred_tools.get(category, [])

            # First try to get preferred tools
            for tool_name in preferred:
                for tool in available_tools:
                    if tool.name == tool_name:
                        selected_tools.append(tool)
                        break

            # If no preferred tools found, select by inferred type
            if not any(tool.name in preferred for tool in selected_tools):
                tool_type_map = {
                    "search": ToolType.INFORMATION,
                    "analysis": ToolType.REASONING,
                    "generation": ToolType.ACTION,
                }

                # Select tools by type
                for tool in available_tools:
                    if tool.tool_type == tool_type_map.get(category):
                        selected_tools.append(tool)
                        # Limit to 2 tools per category if selecting by type
                        if (
                            len(
                                [
                                    t
                                    for t in selected_tools
                                    if t.tool_type == tool_type_map.get(category)
                                ]
                            )
                            >= 2
                        ):
                            break

        logger.info(f"Selected {len(selected_tools)} tools for task: {task}")
        return selected_tools

    async def evaluate_result(self, result: Any) -> Dict[str, Any]:
        """
        Evaluate the result of a research task.

        Args:
            result: The result to evaluate

        Returns:
            Evaluation metrics
        """
        # Initialize evaluation metrics
        metrics = {
            "completeness": 0.0,
            "relevance": 0.0,
            "accuracy": 0.0,
            "overall_quality": 0.0,
        }

        # Basic evaluation logic
        if result:
            # Convert result to string for evaluation
            result_str = ""
            if isinstance(result, list):
                for item in result:
                    if hasattr(item, "text"):
                        result_str += item.text
                    else:
                        result_str += str(item)
            else:
                result_str = str(result)

            # Calculate basic metrics based on content
            word_count = len(re.findall(r"\w+", result_str))

            # Completeness based on word count
            metrics["completeness"] = min(1.0, word_count / 500)

            # Other metrics - in a real implementation, these would use more sophisticated methods
            metrics["relevance"] = 0.8  # Placeholder
            metrics["accuracy"] = 0.7  # Placeholder

            # Overall quality is average of other metrics
            metrics["overall_quality"] = (
                sum(
                    [metrics["completeness"], metrics["relevance"], metrics["accuracy"]]
                )
                / 3
            )

        logger.info(f"Result evaluation: {metrics}")
        return metrics

    async def research_topic(self, topic: str, depth: str = "medium") -> Dict[str, Any]:
        """
        Research a specific topic and produce a report.

        Args:
            topic: The topic to research
            depth: The depth of research (shallow, medium, deep)

        Returns:
            Research results including sources and summary
        """
        # Create a research task
        task = f"Research the topic '{topic}' with {depth} depth and create a comprehensive report"

        # Set up context
        context = {"topic": topic, "depth": depth, "research_type": "informational"}

        # Execute the task using the traditional plan-based approach
        result = await self.execute(task, context)

        # Create a research report
        report = {
            "topic": topic,
            "success": result.success,
            "execution_time": result.execution_time,
            "tool_calls": result.tool_calls,
        }

        if result.success:
            # Extract report content
            content = ""
            sources = []

            if isinstance(result.output, list):
                for item in result.output:
                    if hasattr(item, "text"):
                        content += item.text
                        # Extract sources (simplified implementation)
                        source_matches = re.findall(r"\[(.*?)\]", item.text)
                        sources.extend(source_matches)

            report["content"] = content
            report["sources"] = sources
            report["evaluation"] = await self.evaluate_result(result.output)
        else:
            report["error"] = str(result.error)

        return report

    async def research_topic_with_llm(
        self,
        topic: str,
        depth: str = "medium",
        client_id: str = "research_server",
        prompt_name: str = "research_assistant",
    ) -> Dict[str, Any]:
        """
        Research a topic using direct LLM integration with tools.

        This method uses the new execute_prompt_with_tools approach for more
        dynamic tool selection during execution.

        Args:
            topic: The topic to research
            depth: The depth of research (shallow, medium, deep)
            client_id: The client ID to use for the prompt
            prompt_name: The name of the prompt to use

        Returns:
            Research results including sources and summary
        """
        # Create a research task
        task = f"Research the topic '{topic}' with {depth} depth and create a comprehensive report"

        # Set up prompt arguments
        prompt_arguments = {
            "topic": topic,
            "depth": depth,
            "research_type": "informational",
            "output_format": "structured_report",
        }

        # Set up context
        context = {"topic": topic, "depth": depth, "research_type": "informational"}

        # Execute the task using LLM with tools
        result = await self.execute_with_llm(
            task=task,
            prompt_name=prompt_name,
            prompt_arguments=prompt_arguments,
            client_id=client_id,
            context=context,
        )

        # Create a research report
        report = {
            "topic": topic,
            "success": result.success,
            "execution_time": result.execution_time,
            "tool_calls": result.tool_calls,
        }

        if result.success:
            # Extract report content directly from LLM output
            report["content"] = result.output

            # Extract sources (simplified implementation)
            source_matches = re.findall(r"\[(.*?)\]", result.output)
            report["sources"] = source_matches

            # Get conversation history and tool uses from metadata
            if result.metadata:
                report["conversation"] = result.metadata.get("conversation", [])
                report["tool_uses"] = result.metadata.get("tool_uses", [])

            # Evaluate the result
            report["evaluation"] = await self.evaluate_result(result.output)
        else:
            report["error"] = str(result.error)

        return report
