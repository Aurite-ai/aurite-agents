# Aurite Agents Framework: USC Course Module Details

This document provides a detailed breakdown of the three core modules designed to teach USC MS students how to utilize the Aurite Agents framework. Each module section outlines the specific content for its conceptual document, the steps for its tutorial, and the requirements for its assignment.

## Module 1: Introduction to AI Agents

**Module Goal:** To provide students with a foundational understanding of what AI agents are, their core components (system prompts and tools), and how to configure and run a basic agent using the Aurite Agents framework's frontend developer UI.

---

### 1.1. Conceptual Document: "What is an AI Agent?"

**Learning Objectives:**
*   Students will be able to define an AI agent in the context of LLMs.
*   Students will understand the role and importance of a system prompt in guiding an agent's behavior.
*   Students will grasp the concept of tools as a means for agents to interact with external code/systems.
*   Students will recognize the basic components of a well-structured system prompt.

**Key Topics to Cover:**
1.  **Introduction to AI Agents:**
    *   Definition: An LLM configured for a specific purpose (via a system prompt) and given the ability to execute code (via tools).
    *   Analogy: Agent as a specialized worker.
2.  **Core Component 1: The System Prompt**
    *   Purpose: Defining the agent's persona, task, context, and rules.
    *   Metaphor: System prompt as the "inner logic" of a function (User Message = Input, Agent Response = Output).
    *   Impact on LLM behavior.
3.  **Introduction to Prompt Engineering (Briefly):**
    *   Concept: Crafting effective prompts.
    *   Basic Template/Structure for System Prompts:
        1.  **Role:** (e.g., "You are a weather analyst...")
        2.  **Task:** (e.g., "Your job is to use tools to find weather information...")
        3.  **Context:** (e.g., "Use the `weather_lookup` tool for location X...")
        4.  **Rules/Constraints:** (e.g., "DO NOT provide forecasts for unrequested locations.")
    *   Provide a simple, clear example.
4.  **Core Component 2: Tools**
    *   Purpose: Enabling agents to execute code and interact with external systems/data.
    *   Analogy: Tool as a function with a semantic description (docstring) that the LLM can understand.
    *   Brief overview of tool calling: Agent requests a tool call, code executes, results return to the agent. (Mention that MCP handles much of this, to be detailed in Module 2).
5.  **Summary:** How system prompts and tools combine to create a functional agent.
---

### 1.2. Tutorial: First Agent via the Developer UI

**Learning Objectives:**
*   Students will be able to start the Aurite Agents development UI.
*   Students will learn how to navigate the UI to create and configure an agent.
*   Students will successfully define an agent's name, system prompt, select an LLM, and assign an MCP client (toolset).
*   Students will be able to execute their configured agent and observe its interaction with a tool.

**Prerequisites:**
*   `aurite` package installed (`pip install aurite`).
*   Project initialized (`aurite init`).
*   Environment variables set up as per the main `aurite` package README (especially `ANTHROPIC_API_KEY` or other relevant LLM API keys, and the `API_KEY` for the Aurite backend).
*   Aurite backend API server and frontend developer UI running (via `aurite studio`).

**Framework Changes Required for this Tutorial:**
*   The frontend developer UI (`aurite studio`) must be functional, including any necessary styling fixes.
*   The `aurite studio` command must successfully launch both the backend API and the frontend UI.
*   The frontend build must be included in the `aurite` package in such a way that `aurite studio` can serve it.

**Tutorial Steps:**

1.  **Launch the Aurite Development Environment:**
    *   Open your terminal in the directory created by `aurite init`.
    *   Run the command: `aurite studio`.
    *   Observe the terminal output indicating the backend API and frontend UI have started.
    *   Open a web browser and navigate to `http://localhost:5173` (or the port indicated by `aurite studio`).
    *   If prompted, enter the API key for the Aurite backend (this key is manually set in the `.env` file as per the main package README).

2.  **Create a Simple Weather Agent via UI:**
    *   In the top navigation bar, click "Build".
    *   In the sidebar that appears, click "Agents".
    *   **Name:** Enter a name for your agent, e.g., "MyWeatherAssistant".
    *   **System Prompt:** Enter a simple system prompt, e.g., "You are a helpful assistant. Your task is to use the available tools to find and report the weather for the location specified by the user."
    *   **LLM Configuration:** From the "LLM Configuration" dropdown, select a pre-configured LLM (e.g., the default Anthropic Haiku model if available from `aurite init`).
    *   **Client (Tool) Selection:** From the "Clients" or "Tool Sets" dropdown/multi-select, choose the client that provides weather tools (e.g., `weather_mcp_server` if available from `aurite init`).

3.  **Execute Your Agent via UI:**
    *   In the top navigation bar, click "Execute".
    *   In the sidebar, click "Agents".
    *   From the list of available agents, select "MyWeatherAssistant" (or the name you gave it).
    *   In the chat input field, type a message like: "What is the weather in London?"
        *   *Note to student: The example `weather_mcp_server` is a test fixture and may only support a limited set of locations. 'London' is a reliable choice for testing.*
    *   Click the "Send" button or press Enter.
    *   Observe the agent's response.

**Success Criteria / Verification:**
*   The agent successfully calls the weather lookup tool (this might be visible in UI logs or inferred from the response).
*   The agent responds with a weather forecast for London.

**Notes for AI Assistant (Content Generation):**
*   Provide clear screenshots for each UI interaction step.
*   Emphasize the connection between the UI fields (System Prompt, LLM selection, Client selection) and the concepts learned in the "What is an AI Agent?" document.
*   Keep the example agent very simple for this first tutorial.

---

### 1.3. Assignment: System Prompt Engineering Challenge

**Learning Objectives:**
*   Students will demonstrate their understanding of how system prompts influence agent behavior.
*   Students will practice iterative prompt refinement to achieve a desired outcome.
*   Students will be able to test and verify their agent's modified behavior.

**Prerequisites:**
*   Completion of Module 1 Tutorial ("First Agent via the Developer UI").
*   Access to the Aurite Development UI.

**Task Description:**
Students will take the "MyWeatherAssistant" (or a similar pre-configured agent provided) and modify its system prompt to achieve a new, specified behavior. The core functionality (using the weather tool) should remain, but the agent's persona or how it presents information should change based on the new prompt.

**Example Task:**
"Modify the 'MyWeatherAssistant' to become a 'Dramatic Weather Reporter'. Instead of just stating the weather, it should describe the weather in London with overly dramatic and exaggerated language, as if reporting on a major cinematic event. It must still accurately report the core weather details (temperature, conditions) obtained from the tool but present them dramatically."

*(Alternative example: "Modify the 'MyWeatherAssistant' to be a 'Sarcastic Weather Bot'. It should provide the correct weather but add a sarcastic comment or observation with each forecast.")*

**Submission Requirements:**
*   The final system prompt used for the modified agent.
*   A screenshot of the agent's chat interface showing a successful interaction where it exhibits the new behavior for a query about London's weather.

**Evaluation Criteria:**
*   Does the agent still correctly use the weather tool to fetch information for London?
*   Does the agent's response clearly exhibit the new persona/behavior described in the task (e.g., dramatic, sarcastic)?
*   Is the system prompt well-crafted to achieve this new behavior?

**Notes for AI Assistant (Content Generation):**
*   Provide 2-3 distinct "persona change" tasks like the example above, from which students can choose or be assigned one.
*   Remind students to test iteratively.

---
## Module 2: Understanding MCP and Building Custom Tools

**Module Goal:** To introduce students to the Model Context Protocol (MCP), how it enables agents to use tools, and how to configure different types of MCP servers as `clients` within the Aurite Agents framework.

---

### 2.1. Conceptual Document: "How Does MCP Work?"

**Learning Objectives:**
*   Students will understand the basic principles of the Model Context Protocol (MCP).
*   Students will learn how MCP facilitates communication between LLMs/agents and external tools/services.
*   Students will recognize how `ClientConfig` in the Aurite Agents framework is used to define connections to MCP servers.

**Key Topics to Cover:**
1.  **What is MCP?**
    *   Purpose: Standardizing how LLMs access external tools, prompts, and resources.
    *   Key concepts: Discovery (listing tools), tool calls, structured data exchange.
2.  **MCP in the Aurite Agents Framework:**
    *   How agents use tools provided by MCP servers.
    *   The role of `ClientConfig`: Defining how the framework connects to and interacts with an MCP server.
    *   Brief overview of different transport types for MCP servers (stdio, HTTP, local command-managed) and how they are specified in `ClientConfig`.
    *   Mention that detailed MCP specifications are available online, and this document focuses on its integration within Aurite.
3.  **Benefits of using MCP:**
    *   Interoperability, reusability of tools, decoupling agents from tool implementations.

**Notes for AI Assistant (Content Generation):**
*   Keep this document relatively concise, as extensive MCP documentation exists elsewhere.
*   Focus on the "what" and "why" from a framework user's perspective.
*   Use clear diagrams if helpful to illustrate agent-MCP server interaction.

---

### 2.2. Tutorial: Configuring and Running an Agent with a Local MCP Server via CLI

**Learning Objectives:**
*   Students will learn to define a `ClientConfig` for a local MCP server in `aurite_config.json`.
*   Students will understand how to reference this `ClientConfig` in an `AgentConfig`.
*   Students will be able to use the `aurite` CLI (`start-api` and `run-cli`) to execute an agent that uses tools from the configured local MCP server.
*   Students will gain familiarity with inspecting agent-tool interactions through logs or CLI output.

**Prerequisites:**
*   Completion of Module 1.
*   Basic understanding of JSON syntax.
*   Familiarity with using a command-line interface.
*   `aurite` package installed and project initialized.
*   API server runnable (`start-api`) and CLI usable (`run-cli`).

**Framework Changes Required for this Tutorial:**
*   Ensure the example `weather_mcp_server.py` (or a similar simple, local MCP server) is robust and included with `aurite init`.
*   The `aurite` CLI (`start-api` and `run-cli execute agent ...`) must be functional.

**Tutorial Steps:**

1.  **Review an Example Local MCP Server:**
    *   Briefly examine the provided `mcp_servers/weather_mcp_server.py` (or a similar example) created by `aurite init`. Understand that it's a Python script offering tools. (No need to modify it in this tutorial).
2.  **Configure the Local MCP Server as a Client:**
    *   Open your project's `aurite_config.json` file.
    *   Add or modify a `ClientConfig` entry in the `"clients"` list for the local weather server. Example:
        ```json
        {
          "client_id": "local_weather_service",
          "server_path": "mcp_servers/weather_mcp_server.py", // Path relative to project root
          "capabilities": ["tools"],
          "timeout": 10.0
        }
        ```
    *   Explain each field (`client_id`, `server_path`, `capabilities`).
3.  **Configure an Agent to Use the Client:**
    *   In `aurite_config.json`, add or modify an `AgentConfig` in the `"agents"` list.
    *   Ensure its `client_ids` list includes `"local_weather_service"`.
    *   Define a simple `system_prompt` instructing the agent to use weather tools. Example:
        ```json
        {
          "name": "CLIWeatherAgent",
          "system_prompt": "You are an assistant that uses tools to find the weather. Respond with only the weather information.",
          "llm_config_id": "default_anthropic_haiku", // Or any available LLM
          "client_ids": ["local_weather_service"]
        }
        ```
4.  **Run the Agent using the CLI:**
    *   **Start the API Server:** In one terminal, navigate to your project directory and run `start-api`. Wait for it to initialize.
    *   **Execute the Agent:** In a *second* terminal, navigate to your project directory and run:
        `run-cli execute agent "CLIWeatherAgent" "What's the weather like in London?"`
    *   Observe the output in the CLI.

**Success Criteria / Verification:**
*   The `start-api` command runs without errors.
*   The `run-cli` command executes and returns a response from the agent.
*   The agent's response indicates it successfully used the `local_weather_service` to get the weather for London. (The exact format of the response will depend on the system prompt and LLM).

**Notes for AI Assistant (Content Generation):**
*   Explain the purpose of `start-api` (runs the backend) and `run-cli` (interacts with the backend).
*   Clearly show the JSON configurations for `ClientConfig` and `AgentConfig`.
*   Emphasize that `server_path` is relative to the project root (where `aurite_config.json` resides).

---

### 2.3. Assignment: Configure and Test Diverse MCP Client Types

**Learning Objectives:**
*   Students will demonstrate the ability to configure `ClientConfig` for different MCP server transport types (local stdio, remote HTTP, local command-managed).
*   Students will practice testing these configurations by integrating them into an agent and verifying tool usage.
*   Students will understand the flexibility of the Aurite framework in connecting to various MCP server implementations.

**Prerequisites:**
*   Completion of Module 2 Tutorial.
*   Understanding of the fields in `ClientConfig`.

**Task Description:**
Students will add three distinct `ClientConfig` entries to their `aurite_config.json` file, each representing a different way an MCP server can be connected. They will then test each one.

1.  **Local Stdio Client (Python script):**
    *   Configure the existing `mcp_servers/weather_mcp_server.py` (if not already done precisely as in the tutorial, or use a slightly different `client_id` for this assignment task).
2.  **Remote HTTP Client (Public MCP Server):**
    *   Configure a connection to a publicly available HTTP-based MCP server. An example will be provided (e.g., a search server). Students will need to insert their API key if required by the public server.
3.  **Local Command-Managed Client (e.g., npx/Smithery-based server):**
    *   Configure a client that is started via a command-line instruction (e.g., using `npx` to run a Smithery-compatible MCP server). An example command and server will be provided. Students may need to ensure `npx` (Node.js) is installed.

**Testing Requirement:**
For *each* of the three `ClientConfig` entries created:
*   Create or modify an `AgentConfig` to use *only* that specific client.
*   Execute the agent via the `run-cli` command with an appropriate user message to invoke a tool from that client.
*   Verify that the agent successfully calls a tool from the configured client and provides a relevant response.

**Example Client Configurations (to be provided to students as reference):**
```json
// Add these to the "clients": [] list in your aurite_config.json

// 1. Local Stdio Example (if different from tutorial, or for practice)
{
  "client_id": "assignment_weather_stdio",
  "server_path": "mcp_servers/weather_mcp_server.py",
  "capabilities": ["tools"],
  "timeout": 10.0
}

// 2. Remote HTTP Example (replace with actual public server details)
// {
//   "client_id": "public_search_http",
//   "transport_type": "http_stream",
//   "http_endpoint": "https://example.com/public_search_mcp_server/mcp?api_key=YOUR_KEY_IF_NEEDED",
//   "capabilities": ["tools"]
// }

// 3. Local Command-Managed Example (replace with actual command details)
// {
//   "client_id": "local_memory_command",
//   "transport_type": "local", // This implies stdio but managed by an external command
//   "command": "npx",
//   "args": ["-y", "@some_org/some-mcp-server", "--port", "auto"], // Example args
//   "capabilities": ["tools"],
//   "timeout": 20.0 // May need longer timeout for command startup
// }
```
*(The actual JSON for types 2 and 3 will need to be fully specified for the students, including valid example servers they can use).*

**Submission Requirements:**
*   The complete `aurite_config.json` file containing the three new `ClientConfig` entries and any `AgentConfig` entries used for testing.
*   For each of the three client types, a brief description of the test performed (e.g., agent name used, user message sent) and a copy of the successful CLI output from `run-cli`.

**Evaluation Criteria:**
*   Are all three `ClientConfig` types correctly defined in `aurite_config.json`?
*   Does the submitted evidence (CLI outputs) demonstrate successful tool interaction for an agent using each of the three client types?
*   Are the configurations and testing descriptions clear?

**Notes for AI Assistant (Content Generation):**
*   Ensure the example JSON for HTTP and command-managed clients are fully functional and tested examples that students can adapt. This might involve finding suitable public MCP servers or creating simple, shareable command-managed examples.
*   Clearly explain the differences between `stdio` (direct script path), `http_stream` (URL endpoint), and `local` with `command`/`args` (external process management) transport types in `ClientConfig`.

---
## Module 3: Orchestrating Agents with Workflows

**Module Goal:** To teach students how to create and manage multi-step processes by building, configuring, and executing both simple and custom workflows within the Aurite Agents framework.

---

### 3.1. Conceptual Document: "Orchestrating Tasks with Simple and Custom Workflows"

**Learning Objectives:**
*   Students will understand the purpose and use cases for `SimpleWorkflow` components.
*   Students will learn how `SimpleWorkflow` components execute a linear sequence of agents.
*   Students will understand the purpose and greater flexibility of `CustomWorkflow` components.
*   Students will grasp how `CustomWorkflow` components allow for custom Python logic and can utilize the `ExecutionFacade` to run other components.

**Key Topics to Cover:**
1.  **Introduction to Workflows:**
    *   Why use workflows? (Managing complex tasks, breaking down problems, reusability).
    *   Overview of the two workflow types in Aurite: `SimpleWorkflow` and `CustomWorkflow`.
2.  **Simple Workflows (`SimpleWorkflowConfig`):**
    *   Concept: A linear sequence of agents (or other workflows).
    *   Configuration: How to define steps (list of agent/workflow names) in `aurite_config.json`.
    *   Execution flow: Output of one step becomes the input of the next.
    *   Use cases: Chaining information processing, multi-stage analysis.
3.  **Custom Workflows (`CustomWorkflowConfig`):**
    *   Concept: User-defined Python classes for maximum control and flexibility.
    *   Structure:
        *   Defining a Python class with an `execute_workflow` method.
        *   Configuration: `module_path` and `class_name` in `aurite_config.json`.
    *   Capabilities:
        *   Implementing custom logic (conditional branching, loops, data transformation).
        *   Using the `ExecutionFacade` (passed to `execute_workflow`) to run other registered components (agents, simple workflows, even other custom workflows).
    *   Use cases: Complex decision-making, dynamic task routing, integrating external non-MCP logic.
4.  **Comparing Simple and Custom Workflows:**
    *   When to choose which type.
    *   Complexity vs. flexibility trade-offs.

**Notes for AI Assistant (Content Generation):**
*   Use clear examples for both simple and custom workflow configurations.
*   Provide a conceptual code snippet for a basic custom workflow class structure.
*   Emphasize the power of `ExecutionFacade` within custom workflows.

---

### 3.2. Tutorial: Building and Running Simple and Custom Workflows via CLI

**Learning Objectives:**
*   Students will be able to define configurations for multiple agents.
*   Students will learn to create a `SimpleWorkflowConfig` that sequences these agents.
*   Students will write a basic `CustomWorkflow` Python class that utilizes the `ExecutionFacade`.
*   Students will configure their `CustomWorkflow` in `aurite_config.json`.
*   Students will execute both their simple and custom workflows using the `run-cli` command.

**Prerequisites:**
*   Completion of Module 1 and Module 2.
*   Comfortable with JSON configuration and basic Python scripting.
*   `aurite` CLI (`start-api` and `run-cli`) functional.

**Framework Changes Required for this Tutorial:**
*   Ensure `run-cli execute workflow <name> ...` and `run-cli execute custom-workflow <name> ...` commands are fully functional.
*   The `ExecutionFacade` passed to custom workflows must correctly allow execution of other components.

**Tutorial Scenario:**
A simple data processing pipeline:
1.  Agent 1: Takes a topic, generates 3 related keywords.
2.  Agent 2: Takes a keyword, generates a short descriptive sentence for it.
3.  Simple Workflow: Runs Agent 1, then for each keyword generated, runs Agent 2.
4.  Custom Workflow: Orchestrates the Simple Workflow, perhaps adds a final summary step or logs results.

**Tutorial Steps:**

1.  **Define Two Helper Agents (in `aurite_config.json`):**
    *   **Agent A (`KeywordGenerator`):**
        *   System Prompt: "Given a topic, generate a list of 3 relevant keywords. Output as a JSON list of strings."
        *   LLM: A capable LLM (e.g., Haiku or Opus).
        *   No tools needed for this simple version.
    *   **Agent B (`SentenceGenerator`):**
        *   System Prompt: "Given a keyword, write one concise descriptive sentence about it."
        *   LLM: A capable LLM.
        *   No tools needed.
    *   *Students test each agent individually using `run-cli execute agent ...` to ensure they work.*
2.  **Create a Simple Workflow (in `aurite_config.json`):**
    *   Define a `SimpleWorkflowConfig` named `KeywordToSentenceWorkflow`.
    *   Steps: `["KeywordGenerator", "SentenceGenerator"]`
        *   **Clarification for Tutorial:** For this tutorial, Agent A outputs 3 keywords. The Simple Workflow will run Agent A, then Agent B. Agent B will receive the *list* of keywords. Agent B's prompt should be: "Given a list of keywords, write one concise descriptive sentence for EACH keyword. Combine all sentences into a single response."
    *   Test the simple workflow: `run-cli execute workflow "KeywordToSentenceWorkflow" "Artificial Intelligence"`
3.  **Create a Custom Workflow (Python script and `aurite_config.json`):**
    *   **Python Script (`custom_workflows/my_data_pipeline.py`):**
        ```python
        # custom_workflows/my_data_pipeline.py
        from aurite.execution.facade import ExecutionFacade # Assuming facade is passed
        import json

        class DataPipelineWorkflow:
            async def execute_workflow(self, initial_input: dict, executor: ExecutionFacade, session_id: str | None = None):
                topic = initial_input.get("topic", "general knowledge")

                # Run the Simple Workflow
                simple_workflow_result = await executor.run_simple_workflow(
                    workflow_name="KeywordToSentenceWorkflow",
                    initial_input=topic # Pass the topic to the simple workflow
                )

                # Custom logic: e.g., log, format, or add to the result
                final_output = {
                    "topic": topic,
                    "processed_sentences": simple_workflow_result.get("final_message", "No sentences generated."),
                    "custom_summary": f"Successfully processed topic: {topic}"
                }
                return final_output
        ```
    *   **Configuration (in `aurite_config.json`):**
        ```json
        {
          "name": "MyDataPipeline",
          "module_path": "custom_workflows.my_data_pipeline",
          "class_name": "DataPipelineWorkflow"
        }
        ```
        (This goes into the `"custom_workflows"` list).
    *   Test the custom workflow: `run-cli execute custom-workflow "MyDataPipeline" '{"topic": "Machine Learning"}'` (Note: input must be a JSON string for CLI).

**Success Criteria / Verification:**
*   Both helper agents execute successfully via CLI.
*   The simple workflow executes successfully via CLI, producing sentences for keywords related to the input topic.
*   The custom workflow Python script is correctly written and configured.
*   The custom workflow executes successfully via CLI, incorporating the simple workflow's output and adding its custom summary.

**Notes for AI Assistant (Content Generation):**
*   Provide complete JSON and Python code snippets.
*   Clearly explain the data flow between agents in the simple workflow.
*   Emphasize how the `ExecutionFacade` is used in the custom workflow.
*   Explain how to structure the `custom_workflows` directory and `__init__.py` if necessary for imports.

---

### 3.3. Assignment: Solve a Data Analytics Business Goal

**Learning Objectives:**
*   Students will apply their understanding of agents, MCP clients (if needed), and workflows (simple or custom) to solve a defined problem.
*   Students will practice designing a multi-step agentic solution.
*   Students will gain experience in translating a business requirement into a functional Aurite Agents implementation.

**Prerequisites:**
*   Completion of Module 1, 2, and Module 3 Tutorial.
*   Proficiency in configuring agents, clients (if custom tools are needed), simple workflows, and custom workflows.

**Task Description:**
Students will be provided with a specific business data analytics goal/use case. They must design and implement a solution using the Aurite Agents framework. This may involve:
*   Creating one or more agents with specific system prompts.
*   Optionally, if the use case requires it, defining and using a new (simple) MCP server with custom tools (though the primary focus should be on agent/workflow orchestration unless tool creation is explicitly part of the use case).
*   Orchestrating these agents using a simple workflow or, if more complex logic is needed, a custom workflow.
*   The solution should take a defined input and produce a defined output that addresses the business goal.

**(The specific business goal/use case will be provided by the university professor. For this planning document, we will assume a placeholder goal to structure the assignment, e.g., "Analyze customer feedback (provided as text) to categorize sentiment and identify key product issues mentioned.")**

**Example Placeholder Business Goal (to be replaced):**
"You are provided with a list of customer feedback strings. Your task is to build an Aurite solution that:
1.  For each feedback string, determines if the sentiment is positive, negative, or neutral.
2.  For negative feedback, identifies up to 3 key product issues or complaints mentioned.
3.  Outputs a summary report in JSON format, listing each feedback, its sentiment, and identified issues (if any)."

**Framework Components to Use (Student's Choice, guided by the problem):**
*   Agents (for sentiment analysis, issue extraction).
*   Simple Workflow (if the process is strictly linear).
*   Custom Workflow (if conditional logic or more complex orchestration is needed, e.g., only run issue extraction if sentiment is negative).
*   `aurite_config.json` for all configurations.
*   Python scripts for custom workflows or any custom MCP servers (if they choose to build one).

**Submission Requirements:**
*   A brief design document (1-2 pages) explaining their chosen approach, the agents/workflows designed, and why.
*   All necessary configuration files (`aurite_config.json` with their solution).
*   Any Python scripts for custom workflows or MCP servers.
*   Clear instructions on how to run their solution (e.g., example `run-cli` commands and sample inputs).
*   Example output for a given sample input.

**Evaluation Criteria:**
*   **Functionality:** Does the solution correctly address the specified business goal and produce the desired output?
*   **Design:** Is the chosen architecture (agents, workflow type) appropriate and well-justified?
*   **Implementation:** Are configurations correct? Is custom Python code (if any) clear and functional?
*   **Clarity:** Are the design document, run instructions, and example output clear and easy to understand?

**Notes for AI Assistant (Content Generation):**
*   The assignment document should clearly state the *actual* business goal once decided.
*   Provide a template or guiding questions for the "design document."
*   Offer hints on how to break down the problem into agentic steps.
