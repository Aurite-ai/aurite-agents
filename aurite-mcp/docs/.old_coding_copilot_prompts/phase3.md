Hello Gemini,

We are ready to begin the next phase of the MCP Host Overhaul.
This overarching plan remains documented in @/aurite-mcp/docs/plans/overarching_host_refactor_plan.md (Please ignore similarly named plans in the `/completed` subdirectories).

We have just successfully completed Phase 2: MCP Server Management Enhancements. The implementation details for that are in: @/aurite-mcp/docs/plans/phase2_implementation_plan.md

**Action:** Please review this overarching plan document and technical implementation plan for phase 2 to refresh context on our progress and the overall goals.

---

**Current Task: Initiate New Phase Planning**

We are now entering the **Planning & Design Phase** for:
**Phase 3: Agent Implementation and Model Refinement**

The primary goal of this phase is to design and implement a class for Agents. The agent class should be easy for us to set up, considering the MCP servers that the host integrates with already provides all of the relevant components for an agent (prompts, resources, and tools). Currently, I have the agent execution method defined directly in @/aurite-mcp/src/host/host.py , but I decided that was poor separation of concerns, so we will move this method to our new agent class (host will no longer have `prepare_prompt_with_tools` or `execute_prompt_with_tools`).

The agent class will contain 2 components:

1. The agent class will take in an AgentConfig (a model that we will build in @/aurite-mcp/src/host/models.py ) in order to prepare the agent. The variables defined in this AgentConfig model will all be optional. If no variables are provided, the agent will simply act as an LLM chatbot responding to user messages with default settings. Here are the optional variables:
    - `hosts`: A list of `HostConfig` instances defining the hosts the agent can use.
    - `clients`: A list of `ClientConfig` instances defining direct client connections the agent can use (alternative or supplement to hosts).
    - LLM properties: `temperature`, `model`, and `system_prompt` used in the LLM API call.

We need to think carefully on how we should set up these models (there is a hierarchy with `RootConfig` --> `ClientConfig` --> `HostConfig` --> `AgentConfig`) as this will determine how we will implement the agent. When the agent class is initialized, this `AgentConfig` is used to prepare the agent with the prompts, resources, and tools from the specified hosts/clients, along with the LLM API call properties like temp, model, and system prompt.

2. After initializing the agent with `AgentConfig`, this Agent class has a single method (for now) that runs a loop (adapting the `execute_prompt_with_tools()` method logic from `host.py`) using the `AgentConfig` variables. We'll rename this method to simply `execute()` in the agent class.

**Initial Focus for Planning:**
For the implementation plan, let's define the steps for:
1.  Determine the optimal structure and definitions for the models in `@/aurite-mcp/src/host/models.py`, paying close attention to the `AgentConfig` and its relationship with `HostConfig` and `ClientConfig`.
2.  Define the `Agent` class structure (`__init__`, properties) in a new file `@/aurite-mcp/src/agents/agent.py`.
3.  Outline the implementation steps for the `Agent.execute()` method, detailing how it will adapt the logic previously in `host.py`'s `execute_prompt_with_tools` and interact with configured hosts/clients.
4.  Define the testing strategy: Plan initial test cases and required setup (e.g., mock hosts/clients, simple agent instances) in `@/aurite-mcp/tests/agents/test_agent.py`.
5.  Outline necessary documentation updates (e.g., README sections, code comments) related to the new Agent class, `AgentConfig`, and any model changes.

**Reminder:** As per our workflow, focus on creating a plan that is simple, readable, meaningful, and achieves the goal with the minimal necessary changes.

**Next Step:** Please confirm you've reviewed the context documents and share your initial thoughts on reviewing `host.py` and `models.py` to plan for phase 3. Let's outline the steps for the new implementation plan.