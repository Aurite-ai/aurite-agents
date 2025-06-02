Hello Gemini. Our primary objective is to develop a comprehensive set of course materials for 30 USC MS students, enabling them to learn and utilize the Aurite agent development framework. To achieve this, I will first provide you with extensive context on the framework's architecture and current state. Following that, we will delve into the specifics of the course structure and the materials we need to create. Your role will be to assist in designing, drafting, and refining these educational resources.

# USC Framework Teaching Project

## Task Overview
Today I need your assistance to prepare course material for the 30 USC MS students that I will be teaching over the next few weeks. These 30 students will use the `aurite` agent development framework package that I built for my company. The framework is designed to simplify and standardize the way that developers build agentic components.

My boss (Paul) has assigned me this student teaching task in order to gain free QA testing (students will use the framework and provide feedback) along with introducing potential future customers to our open source tool.

Before I dive into the course materials that we will create for the students, I will start with providing you context on the current state of the framework. There is plenty of documentation in the `docs/` folder that I will reference during this explanation. After explaining the framework, I will explain the general direction we will take in order to build the course materials.

## Project Workflow and Order of Operations

To effectively create the course materials, we will follow a structured, iterative approach, focusing on one module at a time. The overall process will be:

1.  **Sequential Module Development:** We will develop materials for Module 1, then Module 2, and finally Module 3.

2.  **Per-Module Planning:** Before diving into content creation for each module, we will first detail its specific learning objectives, content outline, tutorial steps, and assignment requirements in the `docs/.copilot/usc_project_modules.md` document (or a dedicated plan for that module if more granularity is needed).

3.  **Content Creation Order within Each Module:** For each module, the development sequence will be:
    *   **a. Conceptual Document:**
        *   Draft, review, and finalize the conceptual document for the module.
    *   **b. Tutorial Prerequisites & Development:**
        *   **Identify & Implement Project Changes:** If the module's tutorial requires any new features, bug fixes, or packaging changes to the `aurite` framework (e.g., for Module 1, this includes fixing frontend UI styling and packaging it for launch via `aurite studio`), we will implement and verify these changes first.
        *   **Draft Tutorial:** Create the tutorial document, ensuring it aligns with the conceptual document and any framework modifications.
    *   **c. Assignment Prerequisites & Development:**
        *   **Identify & Implement Project Changes:** If the module's assignment requires any specific framework capabilities or setup not yet present, implement these.
        *   **Draft Assignment:** Create the assignment document, ensuring it aligns with the module's learning objectives and is achievable with the framework's current state (including any modifications made).

4.  **Iterative Refinement:** Throughout this process, we will review and refine all materials to ensure clarity, accuracy, and effectiveness for the students. The `README_packaged.md` and other existing framework documentation (like `docs/components/agent.md`) will also be reviewed and updated as needed to support the course content.

This structured approach will ensure that all necessary framework features are in place before the corresponding educational materials are finalized.

## Framework Context

### Framework Overview
The repository we are currently working in contains the framework package source code. I have recently finished the first version of this framework, so I packaged it and published the package to PyPI.

Users can run `pip install aurite` to install the framework package, and then `aurite init` to scaffold the files and folders that are used by the framework.

You can see exactly which files and folders are created (and how) by reviewing the content of `src/aurite/cli/main.py` (content will be provided for `src/aurite/cli/main.py`), which contains the `aurite init` script. I would normally just point you to `README_packaged.md` (content will be provided for `README_packaged.md`), but we will actually need to review and update this as part of our preparation work.

### Framework Reference Documentation
It is important that you remain aware of the existing documentation for the framework, as we will reference these documents in the course material we create. Key framework documents include:

-   **Overview Documentation:** For more context on what framework components do, refer to the root `README.md` (content will be provided for `README.md`) and the `docs/framework_overview.md` document (content will be provided for `docs/framework_overview.md`).

-   **Component Configuration Documentation:** To understand how each configuration setting works, see the component documents in `docs/components/` (e.g., `docs/components/agent.md`, content will be provided). These component documents are a work in progress (WIP) and will be crucial for the course materials (e.g., we will reference the agent component document in the tutorial about building an agent). Currently, `agent.md`, `llm.md`, and `client.md` have been drafted but require further review.

### Framework Configuration System
The framework is built around a JSON configuration file, referred to as the **project configuration file**. The active project configuration file can be set with the `PROJECT_CONFIG_PATH` environment variable, which defaults to `./aurite_config.json`. This default file is the example project configuration created by the `aurite init` command (detailed in the `src/aurite/cli/main.py` script). Refer to the example project configuration file, `aurite_config.json` (content will be provided), for a quick look at how the framework can be configured for a specific project.

Project files contain a `name`, `description`, and five array variables used to define the framework's building blocks, which are called 'agentic components' or simply 'components'. These components are: `llms`, `clients` (MCP servers), `agents`, `simple_workflows`, and `custom_workflows`. To understand how these component configurations are defined, see `src/aurite/config/config_models.py` (content will be provided), which contains Pydantic models for each component configuration, along with a project configuration model to tie them all together.

### Framework Architecture (Layers)
The framework is organized into a hierarchy of layers, where each layer builds on top of the layer below it to fulfill a specific goal. For detailed information on each layer, refer to the corresponding documents in the `docs/layers/` directory.

A general overview of the layers, from external connections inwards, is as follows:

#### Layer 4: External Connections
Layer 4 consists of the external MCP tool servers. As MCP itself has extensive online documentation, there is no custom framework documentation for this layer.

#### Layer 3: Host System
It's recommended to start understanding the internal framework structure by reading the Layer 3 document: `docs/layers/3_host.md` (content will be provided). This layer explains how the framework orchestrates MCP servers as "clients," including capabilities for filtering and discovering tools, prompts, and resources provided by these servers.

Layer 3 is organized around the `MCPHost` class (defined in `src/aurite/host/host.py`, content will be provided), which manages the lifecycle of MCP servers based on the client JSON configurations in the project file.

#### Layer 2: Orchestration
After reviewing Layer 3, proceed to Layer 2 (Orchestration) by reading `docs/layers/2_orchestration.md` (content will be provided). This is the central layer of the framework. The `HostManager` class (defined in `src/aurite/host_manager.py`, content will be provided) was recently renamed to `Aurite`, allowing users to import the main framework class via `from aurite import Aurite`.

The `Aurite` class (formerly HostManager) is responsible for:
1.  Determining the active project configuration file.
2.  Using `src/aurite/config/project_manager.py` (content will be provided) to load all configurations from the active project file into memory.
3.  Initializing the `ExecutionFacade` class (defined in `src/aurite/execution/facade.py`, content will be provided), which handles the execution of components.
4.  Providing methods to dynamically register configurations (adding them to the active project configuration).
5.  Executing components through the `ExecutionFacade`.

#### Layer 1: Entrypoints
Layer 2 contains the core logic of the framework. Layer 1 (Entrypoints), documented in `docs/layers/1_entrypoints.md` (content will be provided), defines the various runtime entrypoints that initialize and utilize the `Aurite` class. These entrypoints are essentially wrappers around Layer 2 classes and are relatively simple.

There are two primary ways to run the framework:
1.  The FastAPI server, defined in `src/aurite/bin/api/api.py` (content will be provided) and its associated router files in `src/aurite/bin/api/routes/`.
2.  The Worker entrypoint, defined in `src/aurite/bin/worker.py` (content will be provided).

Additionally, a CLI is available in `src/aurite/bin/cli.py`. It acts as a simple wrapper for the API, facilitating requests to a running API server. The FastAPI server is included in the packaged version of the project and can be started with the `start-api` command.

#### Layer 0: Frontend Developer UI
A frontend developer UI (built with React, Tailwind CSS, Vite, Node.js, and TypeScript) is provided to make it easier for users to build, configure, and execute components in a guided, low-code/no-code friendly manner. Note that the UI primarily supports JSON configurations and does not replace an IDE for writing Python code for MCP servers or custom workflows.

This UI is considered Layer 0 as it's not an integral part of the backend framework, which is designed to be frontend-agnostic. However, it's documented as the primary developer interface.

The frontend is not yet part of the packaged `aurite` distribution and has some outstanding UI styling issues. **Our first task in this project will be to address these styling issues and then determine the best way to include the frontend build in the package, allowing it to be launched with a command like `aurite studio`** (similar to `prisma studio`).

## Course Context
Now that you have a better understanding of how the framework (and its packaged version) are set up, I will provide context on how we will build the course materials for the students.

### Course Material Context
My plan for teaching these students is as follows. The detailed content, learning objectives, and specific tasks for each module's conceptual document, tutorial, and assignment will be further elaborated in a separate document: `docs/.copilot/usc_project_modules.md` (content will be provided once created/revised). This main prompt outlines the high-level structure and goals for these materials.

The students will learn to use the framework to build MCP tool servers, agents, simple workflows, and eventually custom workflows geared towards data analytics.

Most of these students have limited software development experience, and almost all are new to AI. To use the framework effectively, they will first need to learn the basics of LLMs, MCP, and agents (where agents connect LLMs with MCP tool servers).

These components have a clear hierarchy:
-   **Agents** are defined by an LLM and one or more MCP tool servers (referred to as `clients` in the framework).
-   **Simple Workflows** are sequential lists of agents, where the output of one agent becomes the input for the next. Simple workflows can also include other simple workflows and even custom workflows as steps.
-   **Custom Workflows** are Python classes that users can write, offering maximum flexibility. They utilize the `ExecutionFacade` to run other components, including other custom workflows, enabling the creation of modular and complex systems.

To introduce students to these concepts, we will create three conceptual documents:
1.  What is an Agent?
2.  How Does MCP Work?
3.  How Does The `Aurite Agents framework` Package Work?

Each conceptual document will be accompanied by a tutorial, an assignment, and a screen-recorded video (which I will create) explaining all three parts. Students will begin with the conceptual document, then follow the tutorial, and finally complete the assignment.

The course will culminate in a final assignment where students build an agent to solve a real-world business data analytics use case.

### Course Material Context
My plan for teaching these students is as follows:

#### Overall Course Structure
The course will be divided into three modules. Each module is designed to build upon the previous one and will include:
*   A conceptual document to explain core ideas.
*   A hands-on tutorial to apply these concepts using the framework.
*   An assignment to assess understanding and practical skills.

For each module, I will also create a screen-recorded video. This video will cover the conceptual document, provide a walkthrough of the tutorial, and offer a brief explanation of the assignment.

In total, the core student-facing materials we will create are:
*   3 Conceptual Documents
*   3 Tutorials
*   3 Assignments

#### Module-Specific Content Overview

##### Module 1: Introduction to AI Agents
*   **Conceptual Document:** "What is an Agent?" (This document must be read by students before starting Tutorial 1.)
*   **Tutorial:** Introductory tutorial focused on using the frontend developer UI to configure and run a basic agent.

##### Module 2: Understanding MCP and Building Custom Tools
*   **Conceptual Document:** "How Does MCP Work?" (This document must be read by students before starting Tutorial 2.)
*   **Tutorial:** Basic coding tutorial where students will use the built-in CLI to run an agent that utilizes an MCP server they build.

##### Module 3: Orchestrating Agents with Workflows
*   **Conceptual Document:** "How Does The `Aurite Agents framework` Package Work?" (This document, likely an enhanced version of the package README, must be read by students before starting Tutorial 3.)
*   **Tutorial:** Intermediate coding tutorial where students use the built-in CLI to create, configure, and run both a simple workflow and a custom workflow.

##### Assignments

*   **Module 1 Assignment: System Prompt Modification**
    *   Objective: Students will modify the system prompt of a pre-existing agent to alter its behavior and achieve a specific, different goal.

*   **Module 2 Assignment: MCP Client Configuration and Testing**
    *   Objective: Students will create `ClientConfig` entries in their `aurite_config.json` for three different types of MCP server connections (e.g., a local stdio server, a remote HTTP-based server, and a command-line managed local server).
    *   Task: They will then test each client configuration by integrating it into an agent and verifying that the agent can successfully access and utilize tools from that MCP client.

*   **Module 3 Assignment: Solving a Business Goal with an Agent/Workflow**
    *   Objective: Students will design and build an agent (or a simple/custom workflow, if more appropriate for the complexity) to address a specified business data analytics goal.
    *   Note: The specific business use cases for this assignment will be determined separately.

*   **Potential Future/Additional Assignments (For internal consideration, not for initial AI prompt focus):**
    *   Develop a 'human-in-the-loop' tool, enabling users to provide feedback or direction to an agent during its execution.
    *   Create a custom workflow that incorporates conditional logic (multiple branching paths) and utilizes the 'human-in-the-loop' tool.
