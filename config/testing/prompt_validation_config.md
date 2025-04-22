## Config Parameters
Updated as of 4/21/2025


- type
  - "agent" or "workflow" or "custom_workflow"
  - The object being tested
- id
  - str
  - The id of the object being tested. Should match the name in config file
- input
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
- repeat
  - bool, default false
  - If the process should repeat if it fails to pass the threshold score
- max_repetitions
  - int, default 1
  - The maximum total repetitions (with repeat)