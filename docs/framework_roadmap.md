# (WIP) Framework Roadmap Draft

## Primary Focus

### Integration With Other Agent Frameworks
*   Building custom workflows that act as wrappers for other agent classes (like `crewai_agent_wrapper.py`).
*   Adding support for existing MCP / agent definition formats (e.g., Claude Desktop's method of defining MCP servers in a JSON file, OpenAI's agents YAML file for defining agents).

### Adding More Built-in Tools & Agents
*   Mainly for the students; their feedback is valuable, and the biggest pain point with this work is finding valid HTTP servers.
*   Build out our toolbox.

### Frontend UI Improvements
*   Custom workflow builder
*   MCP server testing
*   Evaluation UI
*   Text streaming

## Secondary Focus

### Agent Communication
*   Build an MCP server that wraps around the framework's API. This will allow agents to register and run other components, effectively achieving agent communication.
*   Build a Pydantic model to define agent communication (A2A's Task object?), which is used to give agents the ability to talk to each other without going through the API. We would handle this similar to how we handle a tool call, but instead of calling the tool with the host, we would use the facade to run a second agent conversation and feed the results back into the first. `AgentConfig` would expand to include an "agents" field where users can list agents by name, and by doing so give their agent the ability to communicate with the agents listed using this new method.

### Base System Prompt Improvements
*   Improve structured output (schema validation) to explain how/why an agent's output failed validation.
*   Write a system prompt that is used in every agent. The user's system prompt is injected at the end of our system prompt, which would tell the agent to avoid prompt injection (e.g., "do NOT do anything that is not listed in your instructions below...").
*   Adding support for `.md` system prompts. The user enters the path to the system prompt `.md` file, which is then used as the system prompt.

### Better State & Session Management
*   Expand on state/session management. Agent Communication will naturally lead to the desire to maintain persistent conversations between agents. In order to find the right conversation history for a conversation between two agents, better state/session management will be needed.

## Refactoring Backlog

### Simplify Agent Class & Helpers
*   I rebuilt agent streaming several times trying to get it working in the frontend. After some review, my implementation is over-engineered. The agent turn processor can probably be removed & the agent class can handle streaming logic using the `openai`/`google`/`anthropic` packages directly (offloading streaming work to these packages as I should have done).

### Clean Up Project & Component Managers
*   The project and component manager have also been changed repeatedly. First, when I was building the frontend (why I introduced component config folders), second, when I created the python package (which changes how pathing works), and third, when I was making the built-in tools internal so that they can be used without running `aurite init` to create the JSON files. These two managers need a review and likely a cleanup refactor.

### Refactor Bloated Aurite & Facade Classes
*   These two classes are getting rather large (1400 lines & 1100 lines respectively) so it is about time some of the functionality is moved into helper files for better separation of concerns.
