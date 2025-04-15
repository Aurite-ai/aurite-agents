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

    async def test_workflow_prompt_validation(self, host_manager: HostManager):
          
        #TODO: Get initial input, the workflow to run, and the rubric to use
        # temp: hardcode
        #workflow_name = "Example workflow using weather and planning servers"
        agent_name = "Planning Agent"
        user_input = "create a 3 month plan to learn about the history of the world"
        output_type = "numeric"
        type_prompts = {
            "numeric": """{
    "<first criteria name>": <score from 1-10 here>,
    "<second criteria name>": <score from 1-10 here>,
    ...
}"""
        }
        rubric = {
            "criteria": [
                {
                    "name": "Completeness",
                    "description": "The plan covers all major historical events and periods.",
                    "weight": 0.4
                },
                {
                    "name": "Clarity",
                    "description": "The plan is easy to understand and follow.",
                    "weight": 0.3
                },
                {
                    "name": "Feasibility",
                    "description": "The plan is realistic and achievable within the given time frame.",
                    "weight": 0.3
                }
            ]
        }
        testing_prompt = "Your job is to evaluate the plan created by the Planning Agent. Use the rubric provided to evaluate the plan based on the criteria outlined."
        system_prompt = f"""You are a Quality Assurance Agent, your job is to review the output from the {agent_name}.
You have been provided with a prompt explaining how you should evaluate this agent.
Here is the system prompt provided: "{testing_prompt}"
This prompt explains how to evaluate the output using this rubric: {json.dumps(rubric)}

Format your output as JSON. Do not include any other text, and do not format it as a code block (```). Start with {{ and end with }}. Here is a template: {{
    "analysis": "<your analysis here>",
    "output": {type_prompts[output_type]}
}}
"""
        
        await host_manager.register_agent(AgentConfig(name="Quality Assurance Agent", client_ids=None, system_prompt=system_prompt))
        
        #output = host_manager.execute_workflow(workflow_name=workflow_name, initial_user_message=user_input)
        agent_output = await host_manager.execute_agent(agent_name=agent_name, user_message=user_input)
        
        logging.info(f'Agent result: {agent_output.get("final_response").content[0].text}')
        
        # Call agent to analyze this output based on a rubric
        analysis_output = await host_manager.execute_agent(agent_name="Quality Assurance Agent", user_message=agent_output.get("final_response").content[0].text)
                
        logging.info(f'Analysis result: {analysis_output.get("final_response").content[0].text}')
        
        try:
            analysis_json = json.loads(self._clean_thinking_output(analysis_output.get("final_response").content[0].text))
        except Exception as e:
            pytest.fail(f"Error converting agent output to json: {e}")
            
        assert "analysis" in analysis_json
        assert "output" in analysis_json
        
        assert "Completeness" in analysis_json["output"]
        assert len(analysis_json["output"]) == 3
        
        
        
        