# Module 1: Assignment - System Prompt Engineering Challenge

This assignment challenges you to apply what you've learned about system prompts and their impact on AI agent behavior. You'll modify an existing agent's system prompt to give it a new persona and achieve a different interaction style, all while maintaining its core functionality.

**Learning Objectives:**
*   Demonstrate your understanding of how system prompts influence agent behavior.
*   Practice iterative prompt refinement to achieve a desired outcome.
*   Test and verify your agent's modified behavior using the Aurite Developer UI.

---

## Prerequisites

*   Successful completion of the Module 1 Tutorial: "Your First Agent via the Developer UI."
*   Access to the Aurite Development UI (launched via `aurite studio`).
*   The "MyWeatherAssistant" agent (or a similar weather agent) should be configured in your UI as per the tutorial.

---

## Task Description

Your task is to take the "MyWeatherAssistant" agent (or the weather agent you created in the tutorial) and significantly alter its personality or how it presents information by only modifying its **system prompt**. The agent must still correctly use the weather tool to fetch and report weather information for a given location (e.g., London).

Choose **one** of the following challenges. Each requires you to modify only the system prompt of your weather agent to achieve the desired behavior. Remember, the agent must still use the `weather_lookup` tool for London.

### Challenge Options:

**A. Persona-Based Challenges (Focus on Style & Tone):**

1.  **The Dramatic Weather Reporter:**
    *   **Task:** Make the agent behave like an overly dramatic weather reporter. It should provide accurate core weather details (temperature, conditions for London) but deliver them with exaggerated, theatrical language.
    *   **Example Snippet:** "Hold onto your hats! A weather spectacle is unfolding in London! The mercury stands at a STAGGERING 15°C, under partly cloudy skies! Truly an event for the ages!"

2.  **The Pirate Captain Forecaster:**
    *   **Task:** Make the agent speak and act like a swashbuckling pirate captain, delivering the London weather forecast using pirate slang.
    *   **Example Snippet:** "Ahoy! Ye ask 'bout London's skies? Shiver me timbers! The spyglass shows 15°C, with clouds like lost treasure! Prepare ye, scallywag!"

**B. Data Manipulation Challenges (Focus on Processing & Presentation):**

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

1.  **Choose Your Challenge:** Select one of the challenges listed above.
2.  **Navigate to Your Agent's Configuration:**
    *   Launch the Aurite Development UI using `aurite studio`.
    *   In the top navigation bar, click on "Configure".
    *   In the sidebar that appears, click on "Agents".
    *   From the list of existing agents, select your "MyWeatherAssistant" (or the equivalent agent you created in the tutorial). This will open its configuration for editing.
3.  **Modify the System Prompt:**
    *   In the agent configuration form, locate the "System Prompt" field.
    *   Carefully edit the existing system prompt to meet the requirements of your chosen challenge. Think about:
        *   The agent's new role/character or data manipulation task.
        *   The tone of voice and language style (for persona challenges).
        *   Specific instructions for data processing (for data manipulation challenges).
        *   How it should integrate the factual weather data from the tool.
    *   Remember, the agent must still use the `weather_lookup` tool and provide accurate weather details for London, presented according to the challenge.
4.  **Save and Test Iteratively:**
    *   After modifying the system prompt, click the "Save" or "Update Agent" button to save your changes to the "MyWeatherAssistant" configuration.
    *   Navigate to the "Execute" section and select your agent.
    *   Test it by sending a message like: "What is the weather in London?"
    *   Observe the response. Does it reflect the new persona? Is the weather information still accurate?
    *   If not, go back to the "Build" section, refine your system prompt further, save, and test again. Prompt engineering often requires several iterations!
5.  **Final Verification:** Once you are satisfied with the agent's behavior and believe it meets the requirements of your chosen persona challenge, proceed to the submission.

---

## Submission Requirements

Please submit the following:

1.  **Your Final System Prompt:** Copy and paste the complete, final version of the system prompt you crafted for your chosen persona. Clearly indicate which persona challenge you selected.
2.  **Screenshot of Successful Interaction:**
    *   A single screenshot of the Aurite Developer UI's chat interface.
    *   This screenshot must clearly show:
        *   Your input message (e.g., "What is the weather in London?").
        *   The agent's complete response, demonstrating the new persona and providing the weather details for London.

---

## Evaluation Criteria

Your assignment will be evaluated based on:

1.  **Persona Adherence (60%):**
    *   Does the agent's response clearly and consistently exhibit the chosen persona (Dramatic, Sarcastic, or Pirate)?
    *   Is the language style appropriate for the persona?
2.  **Functional Correctness (30%):**
    *   Does the agent still correctly use the weather tool to fetch and report accurate weather information for London (e.g., temperature, conditions)?
3.  **System Prompt Quality (10%):**
    *   Is the submitted system prompt well-crafted and clearly designed to achieve the new behavior?

---

Good luck, and have fun experimenting with your agent's personality!
