# Module 2: Conceptual Document - How MCP Works (with Aurite)

Welcome to Module 2! In Module 1, you learned about AI agents and used the Aurite Developer UI to build one. Now, we'll explore a key technology that powers how agents use tools: the **Model Context Protocol (MCP)**, and specifically, how you interact with it through the Aurite Agents framework.

**Learning Objectives:**
*   Understand the basic principles of the Model Context Protocol (MCP) from a user's perspective.
*   Learn how MCP facilitates communication between LLMs/agents and external tools/services.
*   Recognize how `ClientConfig` in the Aurite framework's `aurite_config.json` file is used to define connections to various MCP servers.
*   Become familiar with the different types of MCP servers you might connect to.

---

## 1. What is MCP (Model Context Protocol)?

At a high level, the **Model Context Protocol (MCP)** is a specification or a set of rules that standardizes how Large Language Models (LLMs) and AI agents can discover and use external capabilities like tools, pre-defined prompts, or other informational resources.

*   **Purpose:** Imagine many different tools created by different developers. MCP aims to provide a common "language" or "interface" so that an agent doesn't need to learn a unique way to talk to each tool. It simplifies integration.

*   **Key Concepts (from a user's view):**
    *   **Discovery:** MCP allows an agent (or the framework it's running in) to ask an "MCP server" what tools it offers. This is like asking a toolbox what wrenches and screwdrivers it contains.
    *   **Tool Calls:** Once an agent knows about a tool, MCP defines how the agent can request to use that tool, pass it the necessary information (inputs/arguments), and get a result back.
    *   **Structured Data:** MCP encourages exchanging information in a structured way (often using JSON), making it easier for both the agent and the tool to understand each other.

*   **Where to Find More:** MCP itself has extensive online documentation detailing its specifications. For this course, we're focused on *how you use MCP-compatible servers within the Aurite framework*, not on becoming MCP protocol experts.

---

## 2. MCP in the Aurite Agents Framework: The Role of Client Configurations in JSON

The Aurite Agents framework uses MCP to manage how your agents connect to and utilize tools. You, as the user, will primarily interact with MCP by defining **client configuration objects** within the `"clients"` list in your project's `aurite_config.json` file.

*   **What is a Client Configuration Object?**
    *   In Aurite, an MCP server that provides tools (or prompts/resources) is referred to as a "Client" from the perspective of your agent.
    *   A client configuration is a JSON object you define in `aurite_config.json`. This object tells the Aurite framework everything it needs to know to connect to and communicate with a specific MCP server.
    *   Each such JSON object essentially registers an MCP server with your Aurite project, making its tools available to your agents.

*   **How Agents Use Tools via these JSON Configurations:**
    1.  You define one or more client configuration objects in the `"clients"` array (list) in your `aurite_config.json`.
    2.  When you define an agent configuration (also a JSON object, in the `"agents"` array), you specify which clients (by their `client_id` from the client configurations) that agent should have access to.
    3.  When your agent runs, the Aurite framework (specifically, the `MCPHost` component) uses the details in the relevant client configuration JSON to manage the connection to the MCP server.
    4.  The agent can then discover and call tools provided by that server.

---

## 3. Types of MCP Servers and Their JSON Configurations in Aurite

You might encounter or want to use different kinds of MCP servers. The Aurite framework allows you to connect to them by defining specific JSON objects within the `"clients"` array in your `aurite_config.json`. Here are common types:

*   **a) Local Python Script Server (Stdio-based):**
    *   **What it is:** A single Python script that runs as an MCP server, communicating over standard input/output (stdio).
    *   **Example:** The `weather_mcp_server.py` that typically comes with `aurite init` is this type.
    *   **Key JSON Fields:**
        *   `client_id`: A unique name you give this client entry (e.g., `"local_weather_service"`).
        *   `server_path`: The path to the Python script (e.g., `"mcp_servers/weather_mcp_server.py"`). This path is usually relative to your project root directory (where `aurite_config.json` is located).
        *   `capabilities`: Usually `["tools"]` if it provides tools. Can also include `"prompts"`.
        *   `timeout`: (Optional) How long in seconds to wait for the server.
    *   **JSON Example:**
        ```json
        {
          "client_id": "weather_server_stdio",
          "server_path": "mcp_servers/weather_mcp_server.py",
          "capabilities": ["tools", "prompts"],
          "timeout": 15.0
        }
        ```
    *   **Use Case:** Great for simple, custom tools you write yourself as part of your project, or for example servers provided with `aurite init`.

*   **b) Remote HTTP-based Server:**
    *   **What it is:** An MCP server running somewhere on a network (or the internet) that you access via an HTTP URL.
    *   **Key JSON Fields:**
        *   `client_id`: A unique name (e.g., `"public_search_engine"`).
        *   `transport_type`: Must be set to `"http_stream"` or `"http_long_poll"` (depending on the server's MCP implementation).
        *   `http_endpoint`: The full URL to the MCP server's endpoint.
        *   `capabilities`: Typically `["tools"]`.
        *   `headers`: (Optional) An object for any necessary HTTP headers, like API keys (e.g., `{"Authorization": "Bearer YOUR_API_KEY"}`).
    *   **JSON Example:**
        ```json
        {
          "client_id": "duckduckgo_search_http",
          "transport_type": "http_stream",
          "http_endpoint": "https://server.smithery.ai/@nickclyde/duckduckgo-mcp-server/mcp",
          "capabilities": ["tools"]
        }
        ```
        *(Note: If the server requires an API key in the URL or headers, you would include it here. The example URL might be a public one or require an API key you'd need to obtain.)*
    *   **Use Case:** Accessing third-party MCP tools or services hosted online.

*   **c) Local Command-Managed Server:**
    *   **What it is:** An MCP server that is started and managed by a command-line instruction. This is common for tools distributed as, for example, Node.js packages (e.g., using `npx`) or other executables. The Aurite framework will run this command to start the server.
    *   **Key JSON Fields:**
        *   `client_id`: A unique name (e.g., `"my_npm_tool_server"`).
        *   `transport_type`: Often `"local"` (which implies stdio communication with the process started by the command).
        *   `command`: The executable command to run (e.g., `"npx"`).
        *   `args`: A list of string arguments for the command.
        *   `capabilities`: `["tools"]`, and/or `["prompts"]`.
        *   `timeout`: (Optional) How long to wait for the server.
    *   **JSON Example:**
        ```json
        {
          "client_id": "smithery_memory_server_local",
          "transport_type": "local",
          "command": "npx",
          "args": [
             "-y",
             "@smithery/cli@latest",
             "run",
             "@jlia0/servers",
             "--key",
             "{SMITHERY_API_KEY}"
          ],
          "capabilities": ["tools", "prompts"],
          "timeout": 20.0
        }
        ```
        *(Note: `{SMITHERY_API_KEY}` is a placeholder. Students would need to replace this with their actual API key, potentially loaded from an environment variable if the server supports it, or directly if necessary. The tutorial/assignment should clarify how to handle such keys.)*
    *   **Use Case:** Using off-the-shelf MCP tools (like those from Smithery or other registries) that are run as local processes via a command.

---

## 4. Benefits of Using MCP (and Aurite's JSON Client Configurations)

*   **Interoperability:** Agents can potentially use tools from any MCP-compliant server, regardless of how that server is implemented or hosted.
*   **Reusability:** A well-built MCP tool server can be used by many different agents across various projects.
*   **Decoupling:** Your agent logic doesn't need to be tightly coupled with the specific implementation details of each tool. The client configuration in `aurite_config.json` handles the connection specifics.
*   **Standardization:** Aurite's approach provides a consistent way to manage connections to diverse MCP servers through simple JSON objects, simplifying your project configuration.

---

In the upcoming tutorial for Module 2, you will get hands-on experience editing your `aurite_config.json` file to:
1.  Define a `ClientConfig` for the local `weather_mcp_server.py`.
2.  Create an `AgentConfig` that uses this client.
3.  Run your agent using the Aurite command-line interface (CLI) tools (`start-api` and `run-cli`).

This will be your first step into configuring the Aurite framework directly through its files, moving beyond the UI!
