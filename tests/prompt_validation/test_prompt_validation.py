"""
Tests for the HostManager class.
"""

import pytest

# Mark all tests in this module to be run by the anyio plugin
pytestmark = pytest.mark.anyio

import os  
import json
from src.host_manager import HostManager
from src.host.host import MCPHost
from src.host.models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
)
from src.config import PROJECT_ROOT_DIR  # Import project root

class TestPromptValidation:
    
    def _get_rubric_prompt(self, name: str = "default") -> str:
        rubric_path = PROJECT_ROOT_DIR / "config/testings/rubrics.json"
        
        try:
            with open(rubric_path, "r") as f:
                raw_config = json.load(f)
                
            return raw_config.get(name, "")
        
        except Exception as e:
            print(f"Rubric not found {name}")
            return ""
        
    def _analyze_output(self, output: str, rubric_name: str):
        rubric = self._get_rubric_prompt(rubric_name)
        
        #TODO: Call agent / llm directly to analyze this output based on a rubric
        
        return {
            ""
        }

    async def test_workflow_prompt_validation(self, host_manager: HostManager):
          
        #TODO: Get initial input, the workflow to run, and the rubric to use
        # temp: hardcode
        #workflow_name = "Example workflow using weather and planning servers"
        agent_name = "Planning Agent"
        user_input = "create a 3 month plan to learn about the history of the world"
        output_type = "numeric"
        type_prompts = {
            "numeric": """{
    "criteria 1": (numeric score here),
    "criteria 2": (score 2 here)
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
Here is the system prompt provided: {testing_prompt}
This prompt explains how to evaluate the output using this rubric: {json.dumps(rubric)}"""
        
        host_manager.register_agent(AgentConfig(name="Quality Assurance Agent", client_ids=None, system_prompt=system_prompt))
        
        #output = host_manager.execute_workflow(workflow_name=workflow_name, initial_user_message=user_input)
        agent_output = host_manager.execute_agent(agent_name=agent_name, user_message=user_input)
        
        # Call agent to analyze this output based on a rubric
        analysis_output = host_manager.execute_agent(agent_name="Quality Assurance Agent", user_message=agent_output.get("final_response"))
        
        assert analysis_output.get("final_response") == ""
        
        
        