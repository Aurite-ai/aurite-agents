## Config Parameters
Updated as of 4/22/2025


- test_type
  - "agent" or "workflow" or "custom_workflow"
  - The type of object being tested
- name
  - str
  - The name of the object being tested. Should match the name in config file
- user_input
  - str or list[str]
  - The input to be used as the initial user input. If a list of strings, it will run it with each separately
- iterations
  - int, default 1
  - The total number of iterations to do when running the agent/workflow
- testing_prompt
  - str
  - The prompt to be passed to the evaluation agent
- rubric
  - dict, example below
  - The rubric to use when evaluating the agent. Expects weight if evaluation_type is numeric, otherwise optional
```json 
    "rubric": {
        "criteria": [
            {
                "name": "Completeness",
                "description": "The plan covers all details asked for in the initial prompt.",
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
```
- evaluation_type
  - "numeric" or "default"
  - If the output should be a score from 0-10 (numeric), or semantic (default)
- threshold
  - number (0-10), optional
  - The expected score threshold for the numeric evaluation_type
- retry
  - bool, default false
  - If the process should retry if it fails to pass the threshold score
- max_retries
  - int, default 0
  - The maximum retries, after the initial run (max_retries=2 would result in 3 total runs)
- edit_prompt
  - bool, default false
  - If the prompt validator should try to improve the prompt if it fails to meet threshold. The new prompt will be used in the next retry, and the final prompt will be included with the output

- new_prompt
  - str, optional
  - For A/B Testing. The new prompt to try and compare to the original prompt