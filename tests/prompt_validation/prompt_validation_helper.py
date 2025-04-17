import json

def prepare_prompts(testing_config: dict):
    type_prompts = {
        "numeric": """{
            "<first criteria name>": <score from 1-10 here>,
            "<second criteria name>": <score from 1-10 here>,
            ...
        }""",
        "default": """<overall assessment (Very Bad, Poor, Average, Good, Excellent)>"""
    }
    
    evaluation_type = testing_config.get("evaluation_type", "default")
    
    if evaluation_type not in type_prompts:
        raise ValueError(f"Evaluation type not recognized '{evaluation_type}', Expected types: {list(type_prompts.keys())}")
    
    qa_system_prompt = f"""You are a Quality Assurance Agent, your job is to review the output from the {testing_config["id"]}.
    You have been provided with a prompt explaining how you should evaluate it.
    Here is the system prompt provided: "{testing_config["testing_prompt"]}"
    This prompt explains how to evaluate the output using this rubric: {json.dumps(testing_config["rubric"])}

    Format your output as JSON. Do not include any other text, and do not format it as a code block (```). Start with {{ and end with }}. Here is a template: {{
        "analysis": "<your analysis here>",
        "output": {type_prompts[evaluation_type]}
    }}
    """
    aggregation_system_prompt = """You are a Quality Assurance Agent. Your task is to aggregate multiple reports from a coworker into a single report. 
    Give your report output as a three sentence summary of the analysis, with an overall assessment at the bottom (Very Bad, Poor, Average, Good, Excellent)."""
    
    return {
        "type_prompts": type_prompts,
        "qa_system_prompt": qa_system_prompt,
        "aggregation_system_prompt": aggregation_system_prompt,
    }

def clean_thinking_output(output: str) -> str:
    """Removes all text up to and including </thinking>"""
    substring = "</thinking>"
    index = output.rfind(substring)
    
    if index > 0:
        output = output[index + len(substring):]
        
    return output