"""
Agent QA Tester for the Aurite Testing Framework.

This module provides quality assurance testing specifically for agent components,
evaluating goal achievement, response quality, tool usage, and system prompt adherence.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.models.config.components import LLMConfig

from ...base_qa_tester import BaseQATester
from ...qa_models import (
    CaseEvaluationResult,
    ComponentQAConfig,
    ExpectationAnalysisResult,
    QAEvaluationResult,
    QATestCategory,
    QATestRequest,
    SchemaValidationResult,
)

if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)

__all__ = ["AgentQATester"]


class AgentQATester(BaseQATester):
    """
    Component-specific QA tester for agents (Level 3).

    This tester evaluates agent performance across multiple dimensions:
    - Goal Achievement: How well the agent accomplishes its intended objectives
    - Response Quality: Coherence, relevance, and completeness of responses
    - Tool Usage: Appropriate selection and usage of available tools
    - System Prompt Adherence: Following instructions and behavioral guidelines
    """

    def __init__(self, config: Optional[ComponentQAConfig] = None):
        """
        Initialize the Agent QA tester.

        Args:
            config: Optional configuration for agent-specific testing
        """
        if config is None:
            config = ComponentQAConfig(
                component_type="agent",
                test_categories=self._get_default_test_categories(),
                default_timeout=60.0,  # Agents may need more time for complex tasks
                parallel_execution=True,
                max_retries=1,
            )

        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_default_test_categories(self) -> List[QATestCategory]:
        """Get default test categories for agent testing."""
        return [
            QATestCategory(
                name="goal_achievement",
                description="How well the agent accomplishes its intended objectives",
                weight=0.4,  # Most important for agents
                required=True,
            ),
            QATestCategory(
                name="response_quality",
                description="Coherence, relevance, and completeness of responses",
                weight=0.3,
                required=True,
            ),
            QATestCategory(
                name="tool_usage",
                description="Appropriate selection and usage of available tools",
                weight=0.2,
                required=False,
            ),
            QATestCategory(
                name="system_prompt_adherence",
                description="Following instructions and behavioral guidelines",
                weight=0.1,
                required=False,
            ),
        ]

    async def test_component(
        self, request: QATestRequest, executor: Optional["AuriteEngine"] = None
    ) -> QAEvaluationResult:
        """
        Execute QA tests for an agent component.

        Args:
            request: The QA test request containing test cases and configuration
            executor: Optional AuriteEngine instance for executing the agent

        Returns:
            QAEvaluationResult containing the test results
        """
        evaluation_id = f"agent_qa_{uuid.uuid4().hex[:8]}"
        started_at = datetime.utcnow()

        self.logger.info(
            f"Starting agent QA testing {evaluation_id} for component: {request.component_config.get('name', 'unknown')}"
        )

        # Validate the request
        validation_errors = self.validate_request(request)
        if validation_errors:
            raise ValueError(f"Invalid request: {'; '.join(validation_errors)}")

        # Set up testing
        await self.setup()

        try:
            # Get LLM client for evaluation
            llm_client = await self._get_llm_client(request, executor)

            # Execute all test cases in parallel
            tasks = [
                self._evaluate_single_case(case=case, llm_client=llm_client, request=request, executor=executor)
                for case in request.test_cases
            ]

            case_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle any exceptions
            processed_results: Dict[str, CaseEvaluationResult] = {}
            failed_count = 0

            for case, result in zip(request.test_cases, case_results, strict=False):
                case_id_str = str(case.id)
                if isinstance(result, Exception):
                    # Create a failed result for exceptions
                    processed_results[case_id_str] = CaseEvaluationResult(
                        case_id=case_id_str,
                        input=case.input,
                        output=None,
                        grade="FAIL",
                        analysis=f"Agent test execution failed: {str(result)}",
                        expectations_broken=case.expectations,
                        error=str(result),
                    )
                    failed_count += 1
                elif isinstance(result, CaseEvaluationResult):
                    processed_results[case_id_str] = result
                    if result.grade == "FAIL":
                        failed_count += 1

            # Calculate overall score using agent-specific scoring
            overall_score = self.aggregate_scores(list(processed_results.values()))

            # Generate agent-specific recommendations
            recommendations = self._generate_agent_recommendations(list(processed_results.values()), request)

            # Determine overall status
            passed_count = len(processed_results) - failed_count
            if failed_count == 0:
                status = "success"
            elif failed_count == len(processed_results):
                status = "failed"
            else:
                status = "partial"

            completed_at = datetime.utcnow()

            return QAEvaluationResult(
                evaluation_id=evaluation_id,
                status=status,
                component_type="agent",
                component_name=request.component_config.get("name", "unknown"),
                overall_score=overall_score,
                total_cases=len(processed_results),
                passed_cases=passed_count,
                failed_cases=failed_count,
                case_results=processed_results,
                recommendations=recommendations,
                metadata={
                    "agent_config": request.component_config,
                    "test_categories": [cat.name for cat in self.get_test_categories()],
                    "framework": request.framework,
                },
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
            )

        finally:
            await self.teardown()

    async def _evaluate_single_case(
        self,
        case,
        llm_client: LiteLLMClient,
        request: QATestRequest,
        executor: Optional["AuriteEngine"] = None,
    ) -> CaseEvaluationResult:
        """
        Evaluate a single test case for an agent.

        Args:
            case: The test case to evaluate
            llm_client: LLM client for expectation analysis
            request: The overall test request
            executor: Optional AuriteEngine for agent execution

        Returns:
            CaseEvaluationResult for this test case
        """
        start_time = datetime.utcnow()

        try:
            # Get the output (either provided or by running the agent)
            output = await self._get_agent_output(case, request, executor)

            # Validate schema if provided
            schema_result = None
            if request.expected_schema:
                schema_result = self._validate_schema(output, request.expected_schema)
                if not schema_result.is_valid:
                    # Schema validation failed
                    return CaseEvaluationResult(
                        case_id=str(case.id),
                        input=case.input,
                        output=output,
                        grade="FAIL",
                        analysis=f"Schema Validation Failed: {schema_result.error_message}",
                        expectations_broken=[],
                        schema_valid=False,
                        schema_errors=schema_result.validation_errors,
                        execution_time=(datetime.utcnow() - start_time).total_seconds(),
                    )

            # Analyze expectations using LLM
            if case.expectations:
                expectation_result = await self._analyze_agent_expectations(case, output, llm_client, request)

                grade = "PASS" if not expectation_result.expectations_broken else "FAIL"

                return CaseEvaluationResult(
                    case_id=str(case.id),
                    input=case.input,
                    output=output,
                    grade=grade,
                    analysis=expectation_result.analysis,
                    expectations_broken=expectation_result.expectations_broken,
                    schema_valid=schema_result.is_valid if schema_result else True,
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                )
            else:
                # No expectations to check, just schema validation
                return CaseEvaluationResult(
                    case_id=str(case.id),
                    input=case.input,
                    output=output,
                    grade="PASS" if (not schema_result or schema_result.is_valid) else "FAIL",
                    analysis="No expectations defined, agent output generated successfully",
                    expectations_broken=[],
                    schema_valid=schema_result.is_valid if schema_result else True,
                    execution_time=(datetime.utcnow() - start_time).total_seconds(),
                )

        except Exception as e:
            self.logger.error(f"Error evaluating agent case {case.id}: {e}")
            return CaseEvaluationResult(
                case_id=str(case.id),
                input=case.input,
                output=None,
                grade="FAIL",
                analysis=f"Agent evaluation failed: {str(e)}",
                expectations_broken=case.expectations,
                error=str(e),
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )

    async def _get_agent_output(self, case, request: QATestRequest, executor: Optional["AuriteEngine"] = None):
        """
        Get the output for a test case by running the agent.

        Args:
            case: The test case
            request: The test request
            executor: Optional AuriteEngine for agent execution

        Returns:
            The output from the agent (full conversation history as formatted string)
        """
        # If output is already provided, use it
        if case.output is not None:
            return case.output

        # Otherwise, we need to run the agent
        if not executor:
            raise ValueError(f"Case {case.id}: No output provided and no executor available to run agent")

        agent_name = request.eval_name or request.component_config.get("name")
        if not agent_name:
            raise ValueError(f"Case {case.id}: No agent name specified for execution")

        # Run the agent using the executor
        result = await executor.run_agent(
            agent_name=agent_name,
            user_message=case.input,
        )

        # Format the full conversation history for evaluation
        conversation_text = self._format_conversation_history(result)
        return conversation_text

    def _validate_schema(self, output, expected_schema: Dict) -> SchemaValidationResult:
        """
        Validate agent output against an expected JSON schema.

        Args:
            output: The agent output to validate
            expected_schema: The JSON schema to validate against

        Returns:
            SchemaValidationResult with validation details
        """
        try:
            import jsonschema

            # Convert output to JSON if it's a string
            if isinstance(output, str):
                try:
                    data_to_validate = json.loads(output)
                except json.JSONDecodeError:
                    return SchemaValidationResult(
                        is_valid=False,
                        error_message="Agent output is not valid JSON",
                        validation_errors=["Failed to parse agent output as JSON"],
                    )
            elif isinstance(output, dict):
                data_to_validate = output
            else:
                return SchemaValidationResult(
                    is_valid=False,
                    error_message="Agent output is not a string or dictionary",
                    validation_errors=[f"Unexpected output type: {type(output).__name__}"],
                )

            # Validate against schema
            jsonschema.validate(instance=data_to_validate, schema=expected_schema)

            return SchemaValidationResult(is_valid=True, error_message=None, validation_errors=[])

        except jsonschema.ValidationError as e:
            return SchemaValidationResult(is_valid=False, error_message=e.message, validation_errors=[e.message])
        except jsonschema.SchemaError as e:
            return SchemaValidationResult(
                is_valid=False,
                error_message=f"Invalid schema: {e.message}",
                validation_errors=[f"Schema error: {e.message}"],
            )
        except Exception as e:
            return SchemaValidationResult(is_valid=False, error_message=str(e), validation_errors=[str(e)])

    async def _analyze_agent_expectations(
        self, case, output, llm_client: LiteLLMClient, request: QATestRequest
    ) -> ExpectationAnalysisResult:
        """
        Use an LLM to analyze whether the agent output meets the expectations.

        Args:
            case: The test case with expectations
            output: The agent output to analyze
            llm_client: The LLM client to use for analysis
            request: The test request for context

        Returns:
            ExpectationAnalysisResult with the analysis
        """
        expectations_str = "\n".join(case.expectations)
        agent_config = request.component_config

        # Create agent-specific analysis prompt
        system_prompt_text = agent_config.get("system_prompt", "Not specified")
        truncated_prompt = system_prompt_text[:200] + "..." if len(system_prompt_text) > 200 else system_prompt_text

        system_prompt = f"""You are an expert Quality Assurance Engineer specializing in AI agent evaluation.

You are evaluating an agent with the following configuration:
- Agent Name: {agent_config.get("name", "Unknown")}
- System Prompt: {truncated_prompt}
- Tools Available: {", ".join(agent_config.get("tools", [])) or "None"}
- Temperature: {agent_config.get("temperature", "Not specified")}

Your job is to review the agent's output and determine if it meets the specified expectations.

Focus on:
1. Goal Achievement: Did the agent accomplish what was asked?
2. Response Quality: Is the response coherent, relevant, and complete?
3. Tool Usage: If tools were available, were they used appropriately?
4. System Prompt Adherence: Does the response follow the agent's behavioral guidelines?

Format your output as JSON. IMPORTANT: Do not include any other text before or after, and do NOT format it as a code block (```). Here is the template:
{{
"analysis": "<your detailed analysis here>",
"expectations_broken": ["<broken expectation 1>", "<broken expectation 2>", "etc"]
}}"""

        analysis_output = await llm_client.create_message(
            messages=[
                {
                    "role": "user",
                    "content": f"Expectations:\n{expectations_str}\n\nUser Input: {case.input}\n\nAgent Output: {output}",
                }
            ],
            tools=None,
            system_prompt_override=system_prompt,
        )

        analysis_text = analysis_output.content

        if analysis_text is None:
            raise ValueError("Evaluation LLM returned no content")

        try:
            # Clean the output and parse JSON
            cleaned_output = self._clean_llm_output(analysis_text)
            analysis_json = json.loads(cleaned_output)

            return ExpectationAnalysisResult(
                analysis=analysis_json.get("analysis", "No analysis provided"),
                expectations_broken=analysis_json.get("expectations_broken", []),
            )

        except Exception as e:
            self.logger.error(f"Error parsing LLM analysis output: {e}")
            # Return a failed analysis
            return ExpectationAnalysisResult(
                analysis=f"Failed to parse LLM output: {str(e)}",
                expectations_broken=case.expectations,  # Assume all failed if we can't parse
            )

    def _clean_llm_output(self, output: str) -> str:
        """
        Clean LLM output to extract JSON.

        Args:
            output: Raw LLM output

        Returns:
            Cleaned JSON string
        """
        # Remove thinking tags if present
        if "</thinking>" in output:
            index = output.rfind("</thinking>")
            output = output[index + len("</thinking>") :]

        # Find the first curly brace
        index = output.find("{")
        if index > 0:
            output = output[index:]

        # Remove newlines for cleaner parsing
        output = output.replace("\n", " ")

        return output.strip()

    def _format_conversation_history(self, result) -> str:
        """
        Format the full conversation history from an AgentRunResult for evaluation.

        Args:
            result: AgentRunResult containing conversation history

        Returns:
            Formatted string representation of the full conversation including tool calls
        """
        formatted_output = []

        # Add conversation history if available
        if hasattr(result, "conversation_history") and result.conversation_history:
            formatted_output.append("=== FULL CONVERSATION HISTORY ===\n")

            for _i, message in enumerate(result.conversation_history):
                role = message.get("role", "unknown")
                content = message.get("content", "")

                # Format based on role
                if role == "user":
                    formatted_output.append(f"USER: {content}\n")
                elif role == "assistant":
                    formatted_output.append(f"ASSISTANT: {content}\n")
                elif role == "tool":
                    # Tool responses
                    tool_name = message.get("name", "unknown_tool")
                    formatted_output.append(f"TOOL RESPONSE ({tool_name}): {content}\n")

                # Check for tool calls in assistant messages
                if role == "assistant" and "tool_calls" in message:
                    for tool_call in message["tool_calls"]:
                        if isinstance(tool_call, dict):
                            function = tool_call.get("function", {})
                            tool_name = function.get("name", "unknown")
                            tool_args = function.get("arguments", "{}")
                            formatted_output.append(f"TOOL CALL: {tool_name}\n")
                            formatted_output.append(f"ARGUMENTS: {tool_args}\n")

            formatted_output.append("\n=== FINAL RESPONSE ===\n")

        # Add the final response
        if hasattr(result, "primary_text") and result.primary_text:
            formatted_output.append(result.primary_text)
        elif hasattr(result, "final_response") and result.final_response:
            formatted_output.append(
                str(
                    result.final_response.content
                    if hasattr(result.final_response, "content")
                    else result.final_response
                )
            )

        return "".join(formatted_output)

    async def _get_llm_client(self, request: QATestRequest, executor: Optional["AuriteEngine"] = None) -> LiteLLMClient:
        """
        Get or create an LLM client for evaluation.

        Args:
            request: The test request
            executor: Optional AuriteEngine with config manager

        Returns:
            LiteLLMClient for evaluation
        """
        if request.review_llm and executor and executor._config_manager:
            # Use the specified LLM configuration
            llm_config = executor._config_manager.get_config(component_type="llm", component_id=request.review_llm)

            if not llm_config:
                raise ValueError(f"No config found for LLM: {request.review_llm}")

            return LiteLLMClient(LLMConfig(**llm_config))
        else:
            # Use default Anthropic configuration
            default_config = LLMConfig(
                name="Default Agent QA Evaluator",
                type="llm",
                model="claude-3-5-sonnet-20241022",
                provider="anthropic",
                temperature=0.1,
            )
            return LiteLLMClient(default_config)

    def _generate_agent_recommendations(self, results: List[CaseEvaluationResult], request: QATestRequest) -> List[str]:
        """
        Generate agent-specific recommendations based on test results.

        Args:
            results: List of case evaluation results
            request: Original test request

        Returns:
            List of agent-specific recommendation strings
        """
        recommendations = []
        agent_config = request.component_config

        if not results:
            return recommendations

        failed_cases = [r for r in results if r.grade == "FAIL"]

        # Analyze system prompt issues
        system_prompt = agent_config.get("system_prompt", "")
        if system_prompt and len(system_prompt) < 50:
            recommendations.append(
                "System prompt is very short. Consider providing more detailed instructions and behavioral guidelines."
            )

        # Analyze tool usage patterns
        tools = agent_config.get("tools", [])
        if not tools and any("tool" in r.analysis.lower() for r in failed_cases):
            recommendations.append(
                "Agent lacks tools but test cases suggest tool usage is needed. Consider adding relevant tools."
            )

        # Analyze temperature settings
        temperature = agent_config.get("temperature", 0.7)
        if temperature > 0.9 and len(failed_cases) > len(results) / 2:
            recommendations.append(
                f"High temperature setting ({temperature}) may be causing inconsistent responses. Consider lowering to 0.3-0.7."
            )

        # Analyze response length issues
        max_tokens = agent_config.get("max_tokens")
        if max_tokens and max_tokens < 500:
            short_responses = [
                r for r in failed_cases if "too short" in r.analysis.lower() or "incomplete" in r.analysis.lower()
            ]
            if short_responses:
                recommendations.append(
                    f"Max tokens setting ({max_tokens}) may be too low, causing truncated responses. Consider increasing."
                )

        # Analyze conversation memory
        conversation_memory = agent_config.get("conversation_memory", True)
        if not conversation_memory and any("context" in r.analysis.lower() for r in failed_cases):
            recommendations.append(
                "Conversation memory is disabled but test cases suggest context awareness is needed."
            )

        return recommendations

    def get_test_categories(self) -> List[QATestCategory]:
        """
        Return the categories of tests this tester can perform.

        Returns:
            List of test categories supported by this tester
        """
        return self.config.test_categories if self.config else self._get_default_test_categories()

    async def setup(self) -> None:
        """
        Setup method called before running tests.

        Performs any necessary initialization for agent testing.
        """
        self.logger.debug("Setting up agent QA tester")
        # Add any agent-specific setup here
        pass

    async def teardown(self) -> None:
        """
        Teardown method called after running tests.

        Performs cleanup after agent testing.
        """
        self.logger.debug("Tearing down agent QA tester")
        # Add any agent-specific cleanup here
        pass

    def validate_request(self, request: QATestRequest) -> List[str]:
        """
        Validate the test request for agent-specific requirements.

        Args:
            request: The test request to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = super().validate_request(request)

        # Agent-specific validations
        if request.component_type != "agent":
            errors.append(f"Component type must be 'agent', got '{request.component_type}'")

        # Validate agent configuration has required fields
        agent_config = request.component_config
        if not agent_config.get("name"):
            errors.append("Agent configuration missing required 'name' field")

        if not agent_config.get("llm") and not agent_config.get("llm_config_id"):
            errors.append("Agent configuration missing LLM specification ('llm' or 'llm_config_id')")

        # Validate test cases have expectations (but don't be overly strict about content)
        # We'll just warn if there are no expectations at all
        cases_without_expectations = [case for case in request.test_cases if not case.expectations and not case.output]
        if cases_without_expectations and not request.eval_name:
            # Only error if we have no way to generate output and no expectations
            errors.append(
                f"Test cases {', '.join(str(c.id) for c in cases_without_expectations[:3])} have no expectations "
                "and no output provided. Either provide expectations or ensure the agent can be executed."
            )

        return errors
