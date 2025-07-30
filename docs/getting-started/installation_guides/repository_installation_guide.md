# Repository Installation Guide

This guide provides step-by-step instructions for setting up the Aurite Agents framework by cloning the main repository. This method is suitable for developers who want to contribute to the framework, delve into its source code, or require the full development environment including the frontend UI and backend services.

For installing Aurite as a Python package to use in your own projects, please see the [Package Installation Guide](package_installation_guide.md).

## Prerequisites

- Python >= 3.12
- [Poetry](https://python-poetry.org/docs/#installation) (Python package and dependency manager)
- Node.js (LTS version recommended, for frontend development)
- Docker & Docker Compose (for the quickstart script and containerized setup)
- `redis-server` (Required if you plan to use the asynchronous task worker)

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Aurite-ai/aurite-agents.git
    cd aurite-agents
    ```

### Quickstart with Docker (Recommended)

The fastest way to get the entire Aurite Agents environment (Backend API, Frontend UI, and PostgreSQL database) up and running is by using the provided setup script with Docker.

1.  **Ensure Docker is running.**
2.  **Run the appropriate setup script for your operating system:**

    - **For Linux/macOS:**
      In the project root directory (`aurite-agents`), execute:
      ```bash
      ./scripts/setup.sh
      ```
    - **For Windows:**
      In the project root directory (`aurite-agents`), execute:
      `bat
    ./scripts/setup.bat
    `
      These scripts will:
    - Check for Docker and Docker Compose.
    - Guide you through creating and configuring your `.env` file (including API keys and project selection).
    - Ask if you want to install optional ML dependencies for your local Python environment (useful if you plan to run or develop certain MCP Servers locally that require them).
    - Build and start all services using Docker Compose.

    Once complete, the backend API will typically be available at `http://localhost:8000` and the frontend UI at `http://localhost:5173`. The script will display the generated API key needed for the UI.

    **Note on Initial Startup:** The backend container might take a few moments to start up completely, especially the first time, as it initializes MCP servers. During this time, the frontend UI might show a temporary connection error. Please allow a minute or two for all services to become fully operational.

#### Running Docker Compose Directly (Alternative to Setup Scripts)

If you prefer to manage your `.env` file manually or if the setup scripts encounter issues, you can still use Docker Compose:

1.  **Create/Configure `.env` File:** Ensure you have a valid `.env` file in the project root. You can copy `.env.example` to `.env` and fill in the necessary values (especially `ANTHROPIC_API_KEY` and `API_KEY`).
2.  **Run Docker Compose:**
    ```bash
    docker compose up --build
    ```
    (Use `docker-compose` if you have an older standalone version).

### Manual Installation & Backend Setup

If you prefer to set up and run components manually or without Docker for all services:

1.  **Install Python Dependencies:**
    This project uses [Poetry](https://python-poetry.org/) for dependency management. First, ensure you have Poetry installed.

    From the project root, run the following command to install all required dependencies, including those for development:

    ```bash
    poetry install --with dev
    ```

    This command reads the `pyproject.toml` file, resolves the dependencies, and installs them into a dedicated virtual environment managed by Poetry.

2.  **Activate the Virtual Environment:**
    To activate the virtual environment and use the installed packages, run:

    ```bash
    poetry shell
    ```

    All subsequent commands in this guide should be run inside this Poetry shell.

3.  **Environment Variables Setup:**
    Before running the system, you need to set up your environment variables.

    a. **Copy the Example File:** In the project root, copy the `.env.example` file to a new file named `.env`:
    `bash
    cp .env.example .env
    `

    b. **Edit `.env`:** Open the newly created `.env` file and fill in your specific configurations and secrets. Pay close attention to comments like `#REPLACE` indicating values you must change.

    Key environment variables to configure in your `.env` file:

    - **LLM API Key (Required):** You must provide an API key for the language model provider you intend to use. For example:
      - `ANTHROPIC_API_KEY=your_anthropic_api_key`
      - `OPENAI_API_KEY=your_openai_api_key`
      - _(Add other provider keys as needed, e.g., `GEMINI_API_KEY`)_
        Only one key is strictly necessary to get started, depending on which LLM you configure your agents to use.
    - `API_KEY` (Optional, for API server): A secret key to secure the FastAPI endpoints if you run the API server. Generate a strong random key if you use this. This is pre-configured if you use the `setup.sh` or `setup.bat` scripts.
    - **Configuration Context:** The framework automatically detects your project and workspace context by looking for `.aurite` files. You do not need to set a path manually. Use the `aurite init` command to create and manage these contexts.

    Other variables in the `.env` file (e.g., for Redis, database persistence like `AURITE_ENABLE_DB`, `AURITE_DB_URL`) are optional and only needed if you intend to use those specific features. Review all entries, especially those marked with `#REPLACE`, and configure them according to your needs.

    **Important Security Note: Encryption Key**

    - **`AURITE_MCP_ENCRYPTION_KEY`**: This environment variable is used by the framework's `SecurityManager` to encrypt sensitive data.
      - If not set, a key will be **auto-generated on startup**. This is convenient for quick local testing.
      - **However, for any persistent deployment, or if you intend to use features that rely on encrypted storage (even for development), it is critical to set this to a strong, persistent, URL-safe base64-encoded 32-byte key.**
      - Relying on an auto-generated key means that any encrypted data may become inaccessible if the application restarts and generates a new key.
      - Please refer to `SECURITY.md` (to be created) for detailed information on generating, managing, and understanding the importance of this key. You can find `AURITE_MCP_ENCRYPTION_KEY` commented out in your `.env.example` file as a reminder.

4.  **Running the Backend API Server:**
    The primary way to interact with the framework is through its FastAPI server, which can be started with a simple command:

    ```bash
    aurite api
    ```

    This command is available after installing the dependencies (Step 2). By default, the server starts on `http://0.0.0.0:8000`.

5.  **Using the CLI:**
    With the framework installed, you can now use the `aurite` command-line interface to interact with your project.

    - **List components:**
      ```bash
      aurite list agents
      ```
    - **Run an agent interactively:**
      ```bash
      aurite run your_agent_name
      ```
    - **Edit configurations in a TUI:**
      ```bash
      aurite edit
      ```

    For a complete guide to all commands, see the [CLI Reference](../../usage/cli_reference.md).

### 6. Frontend UI Setup

To set up and run the frontend developer UI for interacting with the Aurite Agents Framework:

**Note:** Ensure the backend API server (Step 5 above) is running before starting the frontend if you are not using the Docker quickstart.

1.  **Navigate to the Frontend Directory:**
    Open a new terminal or use your existing one to change into the `frontend` directory:

    ```bash
    cd frontend
    ```

2.  **Install Frontend Dependencies:**
    Inside the `frontend` directory, install the necessary Node.js packages using `npm`:

    ```bash
    npm install
    ```

3.  **Start the Frontend Development Server:**
    Once dependencies are installed, start the Vite development server:
    ```bash
    npm run dev
    ```
    The frontend UI will typically be available in your web browser at `http://localhost:5173`.
