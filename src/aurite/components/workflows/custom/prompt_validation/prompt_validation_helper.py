import json
import yaml
import asyncio
import logging
import os
from google import genai
from pydantic import BaseModel, Field
from typing import TYPE_CHECKING
from aurite.components.components.agents.agent_models import AgentExecutionResult

# Type hint for ExecutionFacade to avoid circular import
if TYPE_CHECKING:
    from aurite.execution.facade import ExecutionFacade

logger = logging.getLogger(__name__)


class ValidationCriteria(BaseModel):
    name: str
    description: str
    weight: float | None = None


class ValidationRubric(BaseModel):
    criteria: list[ValidationCriteria]


class ExpectedToolCall(BaseModel):
    name: str
    eq: int | None = None
    lt: int | None = None
    le: int | None = None
    gt: int | None = None
    ge: int | None = None


class ValidationConfig(BaseModel):
    test_type: str = Field(
        ...,
        description="The type of object being tested",
        pattern="^(agent|workflow|custom_workflow)$",
    )
    name: str = Field(
        ...,
        description="The name of the object being tested. Should match the name in config file",
    )
    user_input: str | list[str] | dict | list[dict] = Field(
        ...,
        description="The input to be used as the initial user input. If a list of strings, it will run it with each separately",
    )
    iterations: int = Field(
        default=1,
        description="The total number of iterations to do when running the agent/workflow",
        ge=1,
    )
    testing_prompt: str = Field(
        ...,
        description="The prompt to be passed to the evaluation agent",
    )
    rubric: ValidationRubric | None = Field(
        None,
        description="The rubric to use when evaluating the agent",
    )
    evaluation_type: str = Field(
        default="default",
        description="If the output should be a score from 0-10 (numeric), or semantic (default)",
        pattern="^(numeric|default)$",
    )
    threshold: float | None = Field(
        default=None,
        description="The expected score threshold for the numeric evaluation_type",
        ge=0,
        le=10,
    )
    retry: bool = Field(
        default=False,
        description="If the process should retry if it fails to pass the threshold score",
    )
    max_retries: int = Field(
        default=0,
        description="The maximum retries, after the initial run",
        ge=0,
    )
    edit_prompt: bool = Field(
        default=False,
        description="If the prompt validator should try to improve the prompt if it fails to meet threshold",
    )
    editor_model: str = Field(
        default="gemini",
        description="The model to use for prompt editing",
        pattern="^(gemini|claude)$",
    )
    new_prompt: str | None = Field(
        default=None,
        description="For A/B Testing. The new prompt to try and compare to the original prompt",
    )
    expected_tools: list[ExpectedToolCall] = Field(
        default=[],
        description="A list of tool calls expected to occur, ignored if test_type is not agent",
    )
    analysis: bool = Field(
        default=True,
        description="If analysis should be performed on the agent output. Set to false for cases where you only want to check tool calls",
    )


async def run_iterations(
    executor: "ExecutionFacade",
    testing_config: ValidationConfig,
    override_system_prompt: str | None = None,
) -> (list, list):
    """Run iterations of the agent/workflow and the analysis agent for prompt validation

    Args:
        executor: The ExecutionFacade
        testing_config: The ValidationConfig
        override_system_prompt: Optional, test_type "agent" only. A system prompt to use instead of the tested agent's system prompt

    Returns:
        List of analysis results, list of full agent responses"""
    prompts = _prepare_prompts(testing_config)

    num_iterations = testing_config.iterations
    if type(num_iterations) is not int or num_iterations < 1:
        raise ValueError("iterations must be a positive integer")

    # convert to list if given input is a single string/dict
    test_input = (
        [testing_config.user_input]
        if type(testing_config.user_input) is not list
        else testing_config.user_input
    )

    tasks = [
        _run_single_iteration(
            executor, testing_config, t_in, prompts, i, override_system_prompt
        )
        for i in range(num_iterations)
        for t_in in test_input
    ]

    results_tuple = await asyncio.gather(*tasks)
    results, agent_responses = zip(*results_tuple)

    return list(results), list(agent_responses)


async def evaluate_results(
    executor: "ExecutionFacade",
    testing_config: ValidationConfig,
    results: list,
    agent_responses: list,
) -> dict:
    """Evaluate the prompt validation results

    Args:
        executor: The ExecutionFacade
        testing_config: The ValidationConfig
        results: The results list from run_iterations()
        agent_responses: The list of full agent responses from run_iterations()

    Returns:
        An evaluation dictionary with a bool "pass", if the results passed evaluation, as well as other details
    """
    evaluation = {}
    match testing_config.evaluation_type:
        case "numeric":
            final_results = {}
            final_score = 0
            for key in results[0]["grade"].keys():
                total = 0
                for i in range(len(results)):
                    total += results[i]["grade"][key]
                final_results[key] = round(total / len(results), 2)

            for criteria in testing_config.rubric.criteria:
                final_score += final_results[criteria.name] * criteria.weight

            logging.info(f"Final Prompt Validation Results: {final_results}")
            logging.info(f"Final Prompt Validation Weighted Score: {final_score}/10")

            evaluation = {
                "criteria_results": final_results,
                "weighted_score": round(final_score, 2),
                "pass": (final_score >= testing_config.threshold)
                if testing_config.threshold
                else True,
            }
        case "default":
            # simplify default eval to simply return pass if each result passes
            evaluation = {
                "pass": all([res["grade"] == "PASS" for res in results]),
                "full_results": results,
            }

    # check if tools are satisfied:
    if testing_config.test_type == "agent" and testing_config.expected_tools:
        tool_checks = {}
        for res in agent_responses:
            tool_check = check_tool_calls(res["output"], testing_config.expected_tools)
            tool_checks[res["input"]] = tool_check

            if not tool_check["success"]:
                # fails if a tool check does not pass
                evaluation["pass"] = False

        evaluation["tool_checks"] = tool_checks

    return evaluation


async def evaluate_results_ab(
    executor: "ExecutionFacade", testing_config: ValidationConfig, results: dict
):
    ab_output = await executor.run_agent(
        agent_name="A/B Agent",
        user_message=json.dumps(results),
    )

    logging.info(f"A/B Output: {ab_output.get('final_response').content[0].text}")

    return ab_output.get("final_response").content[0].text


async def improve_prompt(
    executor: "ExecutionFacade", model: str, results: list, current_prompt: str
) -> str:
    """Improve the system prompt of an agent based on the evaluation results

    Args:
        executor: The ExecutionFacade
        model: "claude" or "gemini", the model to use when improving the prompt
        results: The results list from run_iterations()
        current_prompt: The existing system prompt to improve

    Returns:
        The improved prompt
    """

    match model:
        case "claude":
            for res in results:  # remove output to reduce tokens
                res.pop("output")

            user_message = (
                f"""System Prompt: {current_prompt}\n\nAssessment:{results}"""
            )

            new_prompt_output = await executor.run_agent(
                agent_name="Prompt Editor Agent",
                user_message=user_message,
            )

            return new_prompt_output.get("final_response").content[0].text

        case "gemini":
            # now use gemini to improve the prompt

            # TODO: call as an agent once gemini is added to models
            client = genai.Client()

            response = client.models.generate_content(
                model="gemini-2.5-pro-preview-03-25",
                config=genai.types.GenerateContentConfig(
                    system_instruction="You are an expert prompt engineer. Your task is to make edits to agent system prompts to improve their output quality. You will be given the original system prompt and a list of samples of its performance. You will analyze the existing system prompt and output an improved version which will address any failings in the samples. Key points to remember: 1. Make use of short examples to communicate the expected output. 2. Clearly label different parts of the prompt. 3. Return only the new system prompt, with no other text before or after."
                ),
                contents=json.dumps(
                    {"current_prompt": current_prompt, "samples": results}
                ),
            )

            return response.text
        case _:
            raise ValueError(f"Unrecognized prompt editor model {model}")


def load_config(testing_config_path: str) -> ValidationConfig:
    """Load the config from path and validate the file path and data within

    Args:
        testing_config_path: The full filepath to a json or yaml config file

    Returns:
        A ValidationConfig object
    """

    if not os.path.exists(testing_config_path):
        raise FileNotFoundError(
            f"Testing config file not found at {testing_config_path}"
        )

    with open(testing_config_path, "r") as f:
        match testing_config_path.suffix:
            case ".json":
                testing_config_data = json.load(f)
            case ".yaml":
                testing_config_data = yaml.load(f, Loader=yaml.SafeLoader)
            case _:
                raise ValueError(
                    "Testing config file has wrong extension (.json or .yaml expected)"
                )

    testing_config = ValidationConfig.model_validate(testing_config_data, strict=True)

    return testing_config


def check_tool_calls(agent_response, expected_tools: list[ExpectedToolCall]) -> dict:
    """Check if the expected tools appear in the agent response

    Args:
        agent_response: The full Anthropic agent response
        expected_tools: A list of ExpectedToolCalls to check

    Returns:
        {
            "success": bool, true if all expected tools appear
            "error": str, error message if not successful }"""

    tool_calls = _extract_tool_calls(agent_response)
    call_counts = _count_tool_calls(tool_calls)

    calls = []
    errors = []

    for expected in expected_tools:
        count = call_counts.get(expected.name, 0)

        num_errors = len(errors)

        if expected.eq is not None and count != expected.eq:
            errors.append(
                f"Expected tool {expected.name} to be called == {expected.eq} time(s). Called {count} time(s) instead"
            )
        if expected.le is not None and count > expected.le:
            errors.append(
                f"Expected tool {expected.name} to be called <= {expected.le} time(s). Called {count} time(s) instead"
            )
        if expected.lt is not None and count >= expected.lt:
            errors.append(
                f"Expected tool {expected.name} to be called < {expected.lt} time(s). Called {count} time(s) instead"
            )
        if expected.ge is not None and count < expected.ge:
            errors.append(
                f"Expected tool {expected.name} to be called >= {expected.ge} time(s). Called {count} time(s) instead"
            )
        if expected.gt is not None and count <= expected.gt:
            errors.append(
                f"Expected tool {expected.name} to be called > {expected.gt} time(s). Called {count} time(s) instead"
            )

        calls.append(
            {
                "tool_name": expected.name,
                "call_count": count,
                "matches_expectation": num_errors
                == len(errors),  # success if no errors were added
            }
        )

    result = {
        "success": len(errors) == 0,
        "tools": calls,
    }
    if errors:
        result["errors"] = errors
    return result


def generate_config(
    agent_name: str, user_input: str, testing_prompt: str
) -> ValidationConfig:
    """Generate a simple ValidationConfig for an agent

    Args:
        agent_name: The name of the agent being tested
        user_input: The user message
        testing_prompt: A description of what the expected output should look like

    Returns:
        A ValidationConfig object
    """

    return ValidationConfig(
        test_type="agent",
        name=agent_name,
        user_input=user_input,
        testing_prompt=testing_prompt,
        retry=True,
        max_retries=2,
    )


def _prepare_prompts(testing_config: ValidationConfig):
    type_prompts = {
        "numeric": """{
            "<first criteria name>": <score from 1-10 here>,
            "<second criteria name>": <score from 1-10 here>,
            ...
        }""",
        "default": '"PASS" or "FAIL"',
    }

    evaluation_type = testing_config.evaluation_type

    if evaluation_type not in type_prompts:
        raise ValueError(
            f"Evaluation type not recognized '{evaluation_type}', Expected types: {list(type_prompts.keys())}"
        )

    qa_system_prompt = f"""You are a Quality Assurance Agent, your job is to review the output from the {testing_config.name} based on a given input.
    You have been provided with a prompt explaining how you should evaluate it. Your final output should be your analysis of its performance and a grade based on the system prompt.
    Here is the system prompt provided: "{testing_config.testing_prompt}"
    {f"You have also been provided a rubric containing criteria to use in your evaluation: {testing_config.rubric.model_dump_json()}" if testing_config.rubric else ""}

    Format your output as JSON. IMPORTANT: Do not include any other text before or after, and do not format it as a code block (```). Here is a template: {{
        "analysis": "<your analysis here>",
        "grade": {type_prompts[evaluation_type]}
    }}
    """

    match evaluation_type:
        case "default":
            grade_schema = {
                "type": "string",
                "description": "The final PASS or FAIL grade",
                "enum": ["PASS", "FAIL"],
            }
        case "numeric":
            if testing_config.rubric:
                grade_schema = {
                    "type": "object",
                    "properties": {},
                    "required": [
                        criteria.name for criteria in testing_config.rubric.criteria
                    ],
                }
                for criteria in testing_config.rubric.criteria:
                    grade_schema["properties"][criteria.name] = {
                        "type": "number",
                        "description": criteria.description,
                        "minimum": 0,
                        "maximum": 10,
                    }
            else:
                raise ValueError("Rubric not found when evaluation type is numeric")
        case _:
            raise ValueError(f"Evaluation type not recognized: {evaluation_type}")

    qa_schema = {
        "type": "object",
        "properties": {
            "analysis": {
                "type": "string",
                "description": "Your analysis of the performace",
            },
            "grade": grade_schema,
        },
        "required": ["analysis", "grade"],
    }

    return {
        "type_prompts": type_prompts,
        "qa_system_prompt": qa_system_prompt,
        "qa_schema": qa_schema,
    }


def _clean_thinking_output(output: str) -> str:
    """Removes all text up to and including </thinking>"""
    substring = "</thinking>"
    index = output.rfind(substring)

    if index > 0:
        output = output[index + len(substring) :]

    # also trim to first curly brace to remove any preambles like "Here is the json: {}"
    index = output.find("{")
    if index > 0:
        output = output[index:]

    output = output.replace("\n", " ")

    logging.info(f"clean_thinking_output returning {output}")

    return output


async def _get_agent_result(
    executor: "ExecutionFacade",
    testing_config: ValidationConfig,
    test_input,
    override_system_prompt: str | None = None,
) -> tuple:  # Corrected return type annotation
    if override_system_prompt:
        if testing_config.test_type != "agent":
            raise ValueError(
                f"Invalid type {testing_config.test_type}, overriding system prompt only works with agents"
            )
        else:
            full_output = await executor.run_agent(
                agent_name=testing_config.name,
                user_message=test_input,
                system_prompt=override_system_prompt,
            )
    else:
        # call the agent/workflow being tested
        match testing_config.test_type:
            case "agent":
                full_output = await executor.run_agent(
                    agent_name=testing_config.name,
                    user_message=test_input,
                )
                # ---- START DEBUG LOGGING ----
                if testing_config.name == "Planning Agent":
                    logger.info(
                        f"DEBUG: Planning Agent full_output type: {type(full_output)}"
                    )
                    logger.info(
                        f"DEBUG: Planning Agent full_output content: {full_output}"
                    )
                    try:
                        # Attempt to dump as JSON if it's a Pydantic model
                        logger.info(
                            f"DEBUG: Planning Agent full_output model_dump_json: {full_output.model_dump_json(indent=2)}"
                        )
                    except AttributeError:
                        logger.info(
                            "DEBUG: Planning Agent full_output is not a Pydantic model or model_dump_json failed."
                        )
                    except Exception as e:
                        logger.info(
                            f"DEBUG: Error during model_dump_json for Planning Agent full_output: {e}"
                        )
                # ---- END DEBUG LOGGING ----
            case "workflow":
                full_output = await executor.run_simple_workflow(
                    workflow_name=testing_config.name,
                    initial_input=test_input,
                )
            case "custom_workflow":
                full_output = await executor.run_custom_workflow(
                    workflow_name=testing_config.name,
                    initial_input=test_input,
                )
            case _:
                raise ValueError(f"Unrecognized type {testing_config.test_type}")

    if testing_config.test_type == "agent":
        # get text output for agents
        final_response_dict = full_output.get("final_response")
        output = ""  # Default to empty string

        if final_response_dict and isinstance(final_response_dict, dict):
            content_list = final_response_dict.get("content")
            if (
                content_list
                and isinstance(content_list, list)
                and len(content_list) > 0
            ):
                first_block = content_list[0]
                if isinstance(first_block, dict) and first_block.get("type") == "text":
                    output = first_block.get(
                        "text", ""
                    )  # Default to empty string if 'text' key is missing
                else:
                    logger.warning(
                        f"First content block in final_response is not a text block or not a dict: {first_block}"
                    )
                    # Attempt to stringify, or provide a more specific error/placeholder
                    output = str(first_block) if first_block is not None else ""
            else:
                logger.warning(
                    f"final_response content is empty, not a list, or not found: {content_list}"
                )
        else:
            logger.warning(
                f"final_response is None, not a dict, or not found in agent output: {final_response_dict}"
            )
    else:
        # for workflows, output is expected to be the full_output directly
        # (assuming workflows return simpler, directly serializable structures or are handled differently)
        output = full_output

    logging.info(f"Agent result: {output}")

    # Ensure the function still returns both output and full_output as a tuple
    return output, full_output


async def _run_single_iteration(
    executor: "ExecutionFacade",
    testing_config: ValidationConfig,
    test_input,
    prompts,
    i,
    override_system_prompt: str | None = None,
) -> dict:
    logging.info(f"Prompt Validation: Iteration {i + 1}")

    output, full_output = await _get_agent_result(
        executor, testing_config, test_input, override_system_prompt
    )

    if testing_config.analysis:
        # analyze the agent/workflow output, overriding system prompt
        analysis_output = await executor.run_agent(
            agent_name="Quality Assurance Agent",
            user_message=f"Input:{test_input}\n\nOutput:{output}",
            system_prompt=prompts["qa_system_prompt"],
        )

        # Extract text from the Quality Assurance Agent's response
        analysis_final_response_dict = analysis_output.get("final_response")
        analysis_text_output = ""  # Default to empty string

        if analysis_final_response_dict and isinstance(
            analysis_final_response_dict, dict
        ):
            content_list = analysis_final_response_dict.get("content")
            if (
                content_list
                and isinstance(content_list, list)
                and len(content_list) > 0
            ):
                first_block = content_list[0]
                if isinstance(first_block, dict) and first_block.get("type") == "text":
                    analysis_text_output = first_block.get("text", "")
                else:
                    logger.warning(
                        f"QA Agent: First content block in final_response is not a text block or not a dict: {first_block}"
                    )
                    analysis_text_output = (
                        str(first_block) if first_block is not None else ""
                    )
            else:
                logger.warning(
                    f"QA Agent: final_response content is empty, not a list, or not found: {content_list}"
                )
        else:
            logger.warning(
                f"QA Agent: final_response is None, not a dict, or not found in agent output: {analysis_final_response_dict}"
            )

        logging.info(f"Analysis result {i + 1}: {analysis_text_output}")

        try:
            analysis_json = json.loads(_clean_thinking_output(analysis_text_output))
        except Exception as e:
            raise ValueError(f"Error converting agent output to json: {e}")
    else:
        # if no analysis to be done, automatically pass
        analysis_json = {"grade": "PASS"}

    analysis_json["input"] = test_input
    analysis_json["output"] = output

    agent_response = {"input": test_input, "output": full_output}

    return analysis_json, agent_response


def _extract_tool_calls(agent_response: AgentExecutionResult) -> list[dict]:
    """Extract a list of tool calls from agent response"""
    tool_calls = []
    for item in agent_response.get("conversation", []):
        if item.get("role") == "assistant":
            for c in item.get("content", []):
                if c.get("type") == "tool_use":
                    tool_calls.append({"name": c.get("name"), "input": c.get("input")})

    return tool_calls


def _count_tool_calls(tool_calls: list[dict]) -> dict[str, int]:
    """Count how many times tools are called by name"""
    results = {}
    for call in tool_calls:
        if call["name"] not in results:
            results[call["name"]] = 0
        results[call["name"]] += 1

    return results
