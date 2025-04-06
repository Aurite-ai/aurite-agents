Hello Gemini, we have a lot of work to do. We will be rewriting a lot of the host system that I have been developing as a framework for building and managing AI Agents. I am about to write a lot of my brainstorming here, so do your best to follow along. We will start by laying out my brainstorming with markdown documentation so we can get a better picture. Let's begin:

# Overview
I have a technical specs document in @/aurite-mcp/docs/host_implementation.md for you to use as reference in order to understand how I set up the host system. The main files in the host system are the simple FastAPI entrypoint @/aurite-mcp/src/main.py and the MCPHost class in @/aurite-mcp/src/host/host.py .

The implementation of the host system has always been 'off' to me, but I couldn't figure out why until I came to a realization in the shower last night. I think the main problem with the host system is the separation of concerns, specifically too many layers built on top of each other within a single class.

# The Current Host System
First and most importantly, the host system is designed to orchestrate MCP Servers. MCP (Model Context Protocol, a protocol for LLM integration with tools, prompts, and resources) is the foundation of the host system. The host uses several manager classes to handle the four components of an MCP server - roots, resources, prompts, and tools. Take a look at my simple example mcp server for reference: @/aurite-mcp/examples/basic/test_mcp_server.py for a low level server and @/aurite-mcp/examples/basic/test_fastmcp_server.py for the higher level server.

The host manages these MCP servers using the ClientConfig model defined in @/aurite-mcp/src/host/models.py . I think this implementation is optimal, and the manager class approach makes sense here.

Beyond these four MCP server components, the host system is also managing two other components that it shouldn't be handling (what I decided in the shower).

# Components to remove from the Host System: Specific Servers and Agents/Workflows.

1. The host is handling specific MCP servers like the storage server and the memory server in @/aurite-mcp/src/memory/ but I'm now thinking that the host should only handle MCP servers in a generic way, and that we should build independent components that use the host system to work with MCP servers. For example, we would build a class for storage that uses the host system to initialize and communicate with the various storage mcp servers (vector db, sql, etc) instead of implementing this functionality directly into the host system.

2. The host is also handling Agents and Workflows. Agents are essentially just MCP servers, as an agent is the combination of a system prompt and a set of tools that the LLM has access to (along with our user prompt). Workflows are similar, but instead of giving an LLM free reign over various MCP servers, a workflow defines which servers and tools to use in each step, along with how to handle the pre and post processing work (maybe we have a workflow where we need to perform additional formatting on the LLM response before the next workflow step). Just like the specific mcp servers, agents and workflows should probably not be defined in the host system, and instead we should build an independent component that uses the host system.

Picturing the host system without specific mcp servers or agents/workflows, I think this change will make the host much more readable and robust as it has a very clear purpose (managing MCP servers).

Since we are making a lot of changes to the host system, I'm thinking we can also take this time to rebuild both workflows and storage here. I have over-engineered both the storage integration ( @/aurite-mcp/src/host/resources/storage.py and the base workflow class @/aurite-mcp/src/agents/base_workflow.py and the host integration with @/aurite-mcp/src/host/agent/workflows.py . We won't rebuild storage and workflows until the very end of this work, as we first need to refactor the host system to remove the components we no longer want.

## New Additions to the Host system: partial MCP servers with static and dynamic implementations.

1. MCP Server component exclusion (static):
Currently, the host is provided one or more ClientConfig models that are used to initialize (if not already initialized) one or more mcp servers. This means the host will always use all of the prompts, resources, and tools on every mcp server that has been defined in the ClientConfig. ClientConfig also has capabilities, which defines whether or not the host should try to work with the tools, prompts, and resources on the server, but it still cannot selectively choose which tools, prompts, and resources to work with. To solve this, we will add in an optional variable to the ClientConfig model called 'exclude' which is a list of components to exclude. For example, if a ClientConfig has exclude: ["save_plan"] defined, whenever a router, agent, or workflow (or just direct host usage) attempts to work with an MCP server, that component will not be returned. Specifically, when list_prompts() list_tools() list_resources() or the execute version of these methods are requested by a router/agent/workflow, if the response contains "save_plan" (in this example save_plan is a tool in the planning mcp server), they will simply be assumed to not actually exist on the server.

2. Dynamic MCP Server usage:
Along with exclude for partial MCP servers, we will utilize the routing_weight variable (already in the  ClientConfig model, but we will rebuild the implementation here). routing_weight defaults to 1.0 (if not included), which means the router/agent/workflow will use all of the mcp servers available (or parts of the server if ClientConfig uses exclude). If routing_weight is below 1.0, it means the router/agent/workflow is allowed to decide which MCP server(s) to use in order to complete the task provided. This works in a similar way to 'exclude', but instead of excluding mcp server components directly, we are letting AI decide (maybe just simple vector cosine similarity, or an LLM call) which mcp server components are most relevant to the task at hand. This could mean excluding server components that are not relevant to the task, or including new servers that the agent/workflow/router has access to and are relevant to the task.

# New Architecture Design
Here is my new architectural brainstorm:
1. MCPHost Class: Orchestrates MCP Servers (manages mcp roots, resources, prompts, and tools based on a ClientConfig).
2. MCPRouter Class: a class used to group similar MCP servers under an interface that is easy to work with. For example, we will build a StorageRouter class. This StorageRouter will have the ClientConfig models for the various storage-related MCP servers already defined in the StorageRouter class (or somewhere nearby that it can easily access). With this router class, the agents and workflows that we develop will be able to simply initialize a StorageRouter with a parameter like "sql" and the StorageRouter will then initialize an MCPHost with the ClientConfig for the sql mcp server. We can make a base_router.py class for these mcp routers (base router class will be flexible, focused on utilizing the MCPHost to work with specific MCP servers in a standard / easy to access way.

3. Base Agent and Workflow Classes: While the MCPHost is focused on communication with MCP servers in a generic way, and the routers are focused on using the host to communicate with specific mcp servers in a standard way, the last component we need is the actual agent and workflow classes that handle the LLM API calls and actual use case implementation of the host system and routers. Agents will be more simple than workflows, as workflows may use an agent during one of the workflow steps. Agents are essentially just MCP servers (an agent is just a system prompt, set of tools, and the user query). The base agent class will contain the execute_prompt_with_tools method that runs LLM api calls in a loop (utilizing the tools, prompts, and resources provided by the MCP server through either the host directly, or through a router using the host).

# Implementation Plan
I copied the src/host folder to aurite-mcp/host-backup so we can make changes to src/host as we please and then look back at the backup host folder for reference (if needed).

Since I just provided you with a ton of context, let's break this down by creating plan documents. First, let's create an overarching plan document to outline all of the work we are looking to accomplish. The overarching plan will look something like this:

1. Remove specific MCP server code from the host system ( @/aurite-mcp/src/host/resources/storage.py and the mem0 code in host.py for example).
2. Remove the workflow manager ( @/aurite-mcp/src/host/agent/workflows.py ). Consider whether or not to keep execute_prompt_with_tools (does this belong in the host, or in the base agent or workflow class?)
3. Refactor @/aurite-mcp/src/main.py and test with @/aurite-mcp/docs/testing/main_server.postman_collection.json to ensure the removal of these two components did not break the host system.
4. Implement partial MCP servers with a new optional 'exclude' list in ClientConfig. The MCPHost will remove any MCP components that match an exclude string before returning a response. We will ignore dynamic mcp server usage with routing_weight until the end of our work as it is supplementary.
5. Create a new base router class. Test router with storage MCP servers.
6. Create a new base agent class. Test base agent with simple planning MCP server.
7. Create a new base workflow class. Test with a more comprehensive implementation of planning server.
8. Integrate Routers, Agents, and Workflow into the @/aurite-mcp/src/main.py FastAPI server (we will figure out how to do this after we implement these new components).

Okay! I have now provided all of context. Let's begin with the creation of our overarching plan.
