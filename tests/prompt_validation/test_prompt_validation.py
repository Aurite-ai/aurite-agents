"""
Tests for the HostManager class.
"""

import pytest

# Mark all tests in this module to be run by the anyio plugin
pytestmark = pytest.mark.anyio

import os  
import json
import logging
from src.host_manager import HostManager
from src.host.host import MCPHost
from src.host.models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
)
from src.config import PROJECT_ROOT_DIR  # Import project root

class TestPromptValidation:
        
    def _clean_thinking_output(self, output: str) -> str:
        substring = "</thinking>"
        index = output.rfind(substring)
        
        if index > 0:
            output = output[index + len(substring):]
            
        return output

    @pytest.mark.timeout(300)
    async def test_workflow_prompt_validation(self, request, host_manager: HostManager):
        
        # edit the path based on command line args
        config_file = request.config.getoption("--config")
        
        if config_file:
            testing_config_path = PROJECT_ROOT_DIR / f"config/testing/{config_file}"
        else:
            pytest.fail("No json config specified. Use --config=[filename]")
        
        if not testing_config_path.exists():
            pytest.skip(f"Testing config file not found at {testing_config_path}")
            
        with open(testing_config_path, "r") as f:
            testing_config = json.load(f)
          
        type_prompts = {
            "numeric": """{
    "<first criteria name>": <score from 1-10 here>,
    "<second criteria name>": <score from 1-10 here>,
    ...
}"""
        }
        
        system_prompt = f"""You are a Quality Assurance Agent, your job is to review the output from the {testing_config["id"]}.
You have been provided with a prompt explaining how you should evaluate it.
Here is the system prompt provided: "{testing_config["testing_prompt"]}"
This prompt explains how to evaluate the output using this rubric: {json.dumps(testing_config["rubric"])}

Format your output as JSON. Do not include any other text, and do not format it as a code block (```). Start with {{ and end with }}. Here is a template: {{
    "analysis": "<your analysis here>",
    "output": {type_prompts[testing_config["evaluation_type"]]}
}}
"""
        
        await host_manager.register_agent(AgentConfig(name="Quality Assurance Agent", client_ids=None, system_prompt=system_prompt))
                
        num_iterations = testing_config.get("iterations", 1)
        results = []
        
        for i in range(num_iterations):
            logging.info(f"Prompt Validation: iteration {i+1} of {num_iterations}")
            match testing_config["type"]:
                case "agent":
                    output = await host_manager.execute_agent(agent_name=testing_config["id"], user_message=testing_config["input"])
                case "workflow":
                    output = await host_manager.execute_workflow(workflow_name=testing_config["id"], initial_user_message=testing_config["input"])
                case "custom_workflow":
                    output = await host_manager.execute_custom_workflow(workflow_name=testing_config["id"], initial_input=testing_config["input"])
                case _:
                    pytest.fail(f"Unrecognized type {testing_config['type']}")
            
            logging.info(f'Agent result: {output.get("final_response").content[0].text}')
            
            # Call agent to analyze this output based on a rubric
            analysis_output = await host_manager.execute_agent(agent_name="Quality Assurance Agent", user_message=output.get("final_response").content[0].text)
                    
            logging.info(f'Analysis result: {analysis_output.get("final_response").content[0].text}')
            
            try:
                analysis_json = json.loads(self._clean_thinking_output(analysis_output.get("final_response").content[0].text))
            except Exception as e:
                pytest.fail(f"Error converting agent output to json: {e}")
            
            assert "analysis" in analysis_json
            assert "output" in analysis_json
            
            results.append(analysis_json)
            
            
        if testing_config["evaluation_type"] == "numeric":
            final_results = {}
            final_score = 0
            for key in results[0]["output"].keys():
                total = 0
                for i in range(num_iterations):
                    total += results[i]["output"][key]
                final_results[key] = total/num_iterations
                
            for criteria in testing_config["rubric"]["criteria"]:
                final_score += final_results[criteria["name"]] * criteria["weight"]
                
            logging.info(f"Final Prompt Validation Results: {final_results}")
            logging.info(f"Final Prompt Validation Weighted Score: {final_score}/10")
        #TODO: add aggregation for non-numeric output