# Optional Assignment: Agent Tooling Challenge

This **optional assignment** provides a hands-on opportunity to build agents that use a variety of powerful, pre-packaged tools. You will choose from the challenges below, each requiring you to configure and run a new agent to solve a specific problem using tools from the Aurite toolbox.

**Learning Objectives:**
*   Build confidence in using different tool servers from the built-in toolbox.
*   Practice writing effective system prompts that guide an agent to select and use the correct tools.
*   Gain experience with the end-to-end workflow of defining, registering, and running a tool-equipped agent.

---

## Prerequisites

Before attempting this assignment, ensure you have:

1.  **Successfully completed all steps in Tutorial 2: "Giving Agents Tools with MCP Servers."** This includes:
    *   Setting up your Python environment and installing the `aurite` package.
    *   Configuring your `OPENAI_API_KEY`, `SMITHERY_API_KEY`, and `SMITHERY_PROFILE_ID` in your notebook environment.
    *   Having a running `aurite` instance that has been initialized via `await aurite.initialize()`.
2.  A basic understanding of how to create an `AgentConfig` and register it with Aurite.

---

## Task Description

Your task is to complete **one or more** of the following challenges. For each challenge, you will create a new agent by defining an `AgentConfig`, registering it, and then running it with a specific query. The key is to select the correct `mcp_servers` from the toolbox and write a system prompt that clearly instructs the agent on its goal and how to use its tools.

### Challenge Options:

**A. The File Organizer Agent**

*   **Goal:** Create an agent that can manage files on a local computer.
*   **Tool Server:** `desktop_commander`
*   **Task:**
    1.  Create an agent named "File Organizer".
    2.  Write a system prompt that instructs the agent its job is to manage files and directories.
    3.  Give the agent a query that asks it to first **create a new directory** named `my-agent-creations` and then **write a file** inside that new directory named `hello_world.txt` with the content "Hello from my Aurite agent!".
*   **Hint:** The agent will need to use two tools in sequence: `create_directory` and then `write_file`. Your prompt should guide it to understand this two-step process.

**B. The AI Research Assistant**

*   **Goal:** Create an agent that can find academic papers.
*   **Tool Server:** `exa_search`
*   **Task:**
    1.  Create an agent named "Research Assistant".
    2.  Write a system prompt that defines its role as an academic researcher.
    3.  Give the agent a query asking it to **find recent research papers on the topic of "Large Language Model Agents"**.
*   **Hint:** The `exa_search` server has a specific tool called `research_paper_search`. Your prompt should encourage the agent to use the most appropriate tool for finding academic literature.

**C. The App Store Analyst**

*   **Goal:** Create an agent that can provide insights about mobile applications.
*   **Tool Server:** `appinsightmcp`
*   **Task:**
    1.  Create an agent named "App Store Analyst".
    2.  Write a system prompt that explains its job is to find and report on mobile apps.
    3.  Give the agent a query asking it to **"find the top 5 free social media apps on the Google Play store"**.
*   **Hint:** The `appinsightmcp` server has many tools. Review its documentation to see which tool is best for finding top apps in a specific category. Your prompt should guide the agent toward this tool.

---

## Steps to Complete the Assignment:

1.  **Choose a Challenge:** Select one of the challenges above.
2.  **Create a New Code Cell:** In your Jupyter notebook (after you have completed the setup from Tutorial 2), create a new code cell.
3.  **Define and Register Your Agent:**
    *   Import `AgentConfig` from `aurite.config.config_models`.
    *   Create a new `AgentConfig` instance for your chosen challenge. Make sure to set the `name`, `system_prompt`, and the correct `mcp_servers` (e.g., `["desktop_commander"]`).
    *   Register your agent using `await aurite.register_agent(your_agent_config)`.
4.  **Run the Agent:**
    *   Define the user query for your challenge.
    *   Call `await aurite.run_agent(...)` with your agent's name and the query.
    *   Use the `display_agent_response` helper function from the tutorial to display the result.
5.  **Verify and Iterate:** Check the output. Did the agent use the correct tool? Did it accomplish the task? If not, refine your system prompt and try again!

---

## Submission Requirements

For each challenge you complete, please provide:

1.  **The Python code for your `AgentConfig`**.
2.  **The final output** from the `display_agent_response` function, showing that the agent successfully completed the task.

---

Good luck, and have fun building your agents!
