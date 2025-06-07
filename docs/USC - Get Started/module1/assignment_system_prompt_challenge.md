# Module 1: Optional Assignment - System Prompt Engineering Challenge

This **optional assignment** offers a chance to further explore system prompts and their impact on AI agent behavior. You can choose to complete one or more of the challenges below by modifying an existing agent's system prompt to give it a new persona or achieve a different interaction style, all while maintaining its core functionality.

**Learning Objectives:**
*   Demonstrate your understanding of how system prompts influence agent behavior.
*   Practice iterative prompt refinement to achieve a desired outcome.
*   Test and verify your agent's modified behavior by editing configuration files and running a Python script.

---

## Prerequisites

Before attempting this optional assignment, ensure you have:

1.  **Successfully completed all steps in the Module 1 Tutorial: "Your First Agent via Configuration Files."** This includes:
    *   Setting up your Python environment and installing the Aurite framework.
    *   Initializing an Aurite project within your workspace.
    *   Configuring your OpenAI API key in the `.env` file (located in your main workspace directory).
    *   Successfully configuring the "MyCLIWeatherAssistant" agent in your project's `aurite_config.json` file.
    *   Successfully modifying `run_example_project.py` to run "MyCLIWeatherAssistant" and verifying its operation.
2.  **Your `aurite_config.json` file should contain the "MyCLIWeatherAssistant" agent configuration**, as created in the tutorial. This agent should be set up to use the `my_openai_gpt4_turbo` LLM configuration and the `weather_server` MCP server.
3.  **Your `run_example_project.py` script should be configured to execute the "MyCLIWeatherAssistant" agent.**

---

## Task Description

Your task is to take the "MyCLIWeatherAssistant" agent (configured in the tutorial) and significantly alter its personality or how it presents information by only modifying its **system prompt** in the `aurite_config.json` file. The agent must still correctly use the weather tool to fetch and report weather information for a given location (e.g., London).

You can choose to complete **one or more** of the following challenges. Each requires you to modify only the system prompt of your "MyCLIWeatherAssistant" agent to achieve the desired behavior. Remember, the agent must still use the `weather_lookup` tool for London.

### Challenge Options:

**A. Persona-Based Challenges (Focus on Style & Tone):**

1.  **The Dramatic Weather Reporter:**
    *   **Task:** Make the agent behave like an overly dramatic weather reporter. It should provide accurate core weather details (temperature, conditions for London) but deliver them with exaggerated, theatrical language.
    *   **Example Snippet:** "Hold onto your hats! A weather spectacle is unfolding in London! The mercury stands at a STAGGERING 15°C, under partly cloudy skies! Truly an event for the ages!"

2.  **The Pirate Captain Forecaster:**
    *   **Task:** Make the agent speak and act like a swashbuckling pirate captain, delivering the London weather forecast using pirate slang.
    *   **Example Snippet:** "Ahoy! Ye ask 'bout London's skies? Shiver me timbers! The spyglass shows 15°C, with clouds like lost treasure! Prepare ye, scallywag!"

**B. Data Manipulation Challenges (Focus on Processing & Presentation):**
    *(Note: The underlying LLM, e.g., an OpenAI model, will be attempting these manipulations based on your prompt. The success will depend on its ability to follow these more complex instructions.)*

3.  **The Imperial Converter Weatherman:**
    *   **Task:** The `weather_lookup` tool can provide temperature in Celsius (metric default) or Fahrenheit (imperial). Modify the system prompt so that your agent *always* requests the weather in **imperial units (Fahrenheit)** from the tool, and then presents this Fahrenheit temperature to the user.
    *   **System Prompt Hint:** You'll need to instruct the agent to specifically request "imperial" units when it decides to call the `weather_lookup` tool.
    *   **Example Snippet:** "Alright, for London, the temperature is currently 59°F and it's partly cloudy." (Assuming 15°C was converted).

4.  **The Prankster Weatherman (Celsius Focus):**
    *   **Task:** Make the agent a "Prankster Weatherman." It should:
        1.  Request the weather in **metric units (Celsius)** from the tool (or rely on its default).
        2.  Take the actual Celsius temperature, **add 10 degrees** to it.
        3.  Report this "prank" Celsius temperature with a humorous or mischievous comment.
    *   **System Prompt Hint:** Instruct the agent on the arithmetic operation and the desired prankish tone.
    *   **Example Snippet:** "Incredible news from London! It's an UNEXPECTEDLY tropical {actual_temp_celsius + 10}°C today! Perfect for... well, something surprisingly warm! *wink*"

5.  **The "Feels Like" Fabricator (Advanced Celsius Focus):**
    *   **Task:** The agent should report the actual Celsius temperature from the tool but also invent a "feels like" temperature that is always 5 degrees Celsius lower than the actual temperature. It should present both.
    *   **System Prompt Hint:** Instruct the agent to report the tool's temperature directly and then to calculate and state a "feels like" temperature based on your rule.
    *   **Example Snippet:** "Okay, the actual temperature in London is 15°C and it's partly cloudy. However, with the wind and all, it probably *feels more like* 10°C out there. Brrr!"

---

## Steps to Complete the Assignment:

1.  **Choose Your Challenge(s):** Select one or more of the challenges listed above to attempt.
2.  **Locate Your Agent's Configuration:**
    *   Open your project's `aurite_config.json` file in your text editor.
    *   Find the configuration block for your "MyCLIWeatherAssistant" agent within the `agents` array. It should look similar to this:
        ```json
        {
          "name": "MyCLIWeatherAssistant",
          "system_prompt": "You are a helpful assistant. Your task is to use the available tools to find and report the weather for the location specified by the user. Only provide the temperature and a brief description of the conditions.",
          "llm_config_id": "my_openai_gpt4_turbo",
          "mcp_servers": ["weather_server"]
        }
        ```
3.  **Modify the System Prompt:**
    *   In the JSON configuration for "MyCLIWeatherAssistant", locate the `"system_prompt"` field.
    *   Carefully edit the value of this system prompt to meet the requirements of your chosen challenge. Think about:
        *   The agent's new role/character or data manipulation task.
        *   The tone of voice and language style (for persona challenges).
        *   Specific instructions for data processing (for data manipulation challenges).
        *   How it should integrate the factual weather data from the tool.
    *   Remember, the agent must still use the `weather_lookup` tool (via the `weather_server` MCP server) and provide accurate weather details for London, presented according to the challenge.
4.  **Save and Test Iteratively:**
    *   After modifying the system prompt in `aurite_config.json`, save the file.
    *   Open your terminal, ensure your virtual environment is active, and navigate to your project directory (e.g., `my_first_aurite_project`).
    *   Run your agent using the `run_example_project.py` script:
        ```bash
        python run_example_project.py
        ```
        *(This script should already be configured to run "MyCLIWeatherAssistant" with a query like "What is the weather in London?")*
    *   Observe the terminal output. Does it reflect the new persona/behavior? Is the weather information still accurate?
    *   If not, go back to `aurite_config.json`, refine the system prompt further, save, and test again by running the script. Prompt engineering often requires several iterations!
5.  **Final Verification:** Once you are satisfied with the agent's behavior and believe it meets the requirements of your chosen challenge, proceed to the submission.

---

## Submission Requirements

Please submit the following:

1.  **Your Final System Prompt(s):** For each challenge you complete, copy and paste the complete, final version of the system prompt you crafted. Clearly indicate which challenge each system prompt corresponds to.
2.  **Screenshot of Successful Interaction:**
    *   A single screenshot of your **terminal output** after running `python run_example_project.py`.
    *   This screenshot must clearly show:
        *   Your input message (e.g., "What is the weather in London?").
        *   The agent's complete response, demonstrating the new persona and providing the weather details for London.

---

## Self-Assessment Criteria

Consider the following points to self-assess your attempts:

1.  **Challenge Adherence (60%):**
    *   Does the agent's response clearly and consistently exhibit the chosen persona or correctly perform the data manipulation as per the challenge?
    *   Is the language style appropriate for the persona challenges?
    *   Is the data manipulation accurate for those challenges?
2.  **Functional Correctness (30%):**
    *   Does the agent still correctly use the weather tool to fetch and report accurate weather information for London (e.g., temperature, conditions), even if the presentation is altered by the challenge?
3.  **System Prompt Quality (10%):**
    *   Is the submitted system prompt well-crafted and clearly designed to achieve the new behavior with the underlying LLM (e.g., an OpenAI model)?

---

Good luck, and have fun experimenting with your agent's personality!
