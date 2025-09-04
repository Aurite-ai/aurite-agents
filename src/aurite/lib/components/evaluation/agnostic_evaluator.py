# tests/fixtures/custom_workflows/example_workflow.py
import asyncio
import inspect
import json
import logging

# from aurite.lib.config import PROJECT_ROOT_DIR  # Import project root - REMOVED
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Union

import jsonschema

from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.models.config.components import LLMConfig

from ...models.config.components import EvaluationCase, EvaluationConfig
from .agent_runner import AgentRunner

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:

# Type hint for AuriteEngine to avoid circular import
if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine  # This is now correct

logger = logging.getLogger(__name__)


async def evaluate(
    input: EvaluationConfig,
    executor: Optional["AuriteEngine"] = None,
) -> Any:
    """
    Evaluates one or more evaluation test cases

    Args:
        input: The EvaluationConfig object
        executor: The AuriteEngine instance to run agents

    Returns:
        A dictionary containing the result or an error.
    """
    logger.info(f"Evaluation started with input: {input}")

    try:
        if input.review_llm and executor:
            config_manager = executor._config_manager

            llm_config = config_manager.get_config(component_id=input.review_llm, component_type="llm")

            if not llm_config:
                raise ValueError(f"No config found for llm id {input.review_llm}")

            llm_config = LLMConfig(**llm_config)
        else:
            # default to hardcoded anthropic llm config
            llm_config = LLMConfig(
                name="Default Eval",
                type="llm",
                model="claude-sonnet-4-20250514",
                # model="claude-3-5-haiku-latest",
                provider="anthropic",
                temperature=0.1,
            )

        llm_client = LiteLLMClient(llm_config)
        tasks = [
            _evaluate_case(
                case=case, llm_client=llm_client, run_agent=input.run_agent, expected_schema=input.expected_schema
            )
            for case in input.test_cases
        ]

        results = await asyncio.gather(*tasks)

        results_dict = {input.test_cases[i].id: results[i] for i in range(len(results))}

        return_value = {
            "status": "success",
            "input": input,
            "result": results_dict,
        }

        logger.info("Evaluation finished successfully.")

        return return_value
    except Exception as e:
        logger.error(f"Error within component evaluation: {e}")
        return {"status": "failed", "error": f"Error within component evaluation: {str(e)}"}


async def _evaluate_case(
    case: EvaluationCase,
    llm_client: LiteLLMClient,
    run_agent: Optional[Union[Callable[[EvaluationCase], Any], Callable[[EvaluationCase], Awaitable[Any]]]],
    expected_schema: Optional[dict[str, Any]],
) -> dict:
    output = case.output
    if not output:
        if run_agent:
            if type(run_agent) is str:
                runner = AgentRunner(run_agent)
                output = await runner.execute(case)
            elif inspect.iscoroutinefunction(run_agent):
                output = await run_agent(case)
            else:
                output = run_agent(case)
        else:
            raise ValueError(f"Case output and run_agent both undefined for case {case.id}")

    if expected_schema:
        try:
            if isinstance(output, str):
                data_to_validate = json.loads(output)
            elif isinstance(output, dict):
                data_to_validate = output
            else:
                raise TypeError("Component output not str/dict")

            jsonschema.validate(instance=data_to_validate, schema=expected_schema)

        except json.JSONDecodeError as e:
            return {
                "analysis": "Schema Validation Failed: Component did not output valid JSON",
                "grade": "FAIL",
            }
        except jsonschema.ValidationError as e:
            return {"analysis": f"Schema Validation Failed: {e.message}", "grade": "FAIL"}
        except jsonschema.SchemaError as e:
            return {"analysis": f"Schema Validation Failed: Invalid schema: {e.message}", "grade": "FAIL"}
        except TypeError as e:
            return {"analysis": f"Schema Validation Failed: {e}", "grade": "FAIL"}

    expectations_str = "\n".join(case.expectations)
    analysis_output = await llm_client.create_message(
        messages=[
            {
                "role": "user",
                "content": f"Expectations:\n{expectations_str}\n\nInput:{case.input}\n\nOutput:{output}",
            }
        ],
        tools=None,
        system_prompt_override="""You are an expert Quality Assurance Engineer. Your job is to review the output from an agent and make sure it meets a list of expectations.
Your output should be your analysis of its performance, and a list of which expectations were broken (if any). These strings should be identical to the original expectation strings.

Format your output as JSON. IMPORTANT: Do not include any other text before or after, and do NOT format it as a code block (```). Here is a template: {{
"analysis": "<your analysis here>",
"expectations_broken": ["<broken expectation 1>", "<broken expectation 2>", "etc"]
}}""",
    )

    analysis_text_output = analysis_output.content

    try:
        analysis_json = json.loads(_clean_thinking_output(analysis_text_output))
    except Exception as e:
        raise ValueError(f"Error converting evaluation agent output to json: {e}") from e

    analysis_json["grade"] = "PASS"
    if "expectations_broken" not in analysis_json or len(analysis_json["expectations_broken"]) > 1:
        analysis_json["grade"] = "FAIL"

    return analysis_json


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

    logging.debug(f"clean_thinking_output returning {output}")

    return output
