# Repository Installation Guide

This guide provides step-by-step instructions for setting up the Aurite Agents framework by cloning the main repository. This method is suitable for developers who want to contribute to the framework, delve into its source code, or require the full development environment including the frontend UI and backend services.

For installing Aurite as a Python package to use in your own projects, please see the [Package Installation Guide](../package_installation_guide.md).

## Prerequisites

*   Python >= 3.12 (if running locally without Docker for all services)
*   `pip` (Python package installer)
*   Node.js (LTS version recommended, for frontend development if run locally without Docker)
*   Yarn (Package manager for frontend, if run locally without Docker)
*   Docker & Docker Compose (for the quickstart script and containerized setup)
*   `redis-server` (Required if you plan to use the asynchronous task worker, whether locally or if you add it to Docker Compose)

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
    *   **For Linux/macOS:**
        In the project root directory (`aurite-agents`), execute:
        ```bash
        ./setup.sh
        ```
    *   **For Windows:**
        In the project root directory (`aurite-agents`), execute:
        ```bat
        setup.bat
        ```
    These scripts will:
    *   Check for Docker and Docker Compose.
    *   Guide you through creating and configuring your `.env` file (including API keys and project selection).
    *   Ask if you want to install optional ML dependencies for your local Python environment (useful if you plan to run or develop certain MCP Servers locally that require them).
    *   Build and start all services using Docker Compose.

    Once complete, the backend API will typically be available at `http://localhost:8000` and the frontend UI at `http://localhost:5173`. The script will display the generated API key needed for the UI.

    **Note on Initial Startup:** The backend container might take a few moments to start up completely, especially the first time, as it initializes MCP servers. During this time, the frontend UI might show a temporary connection error. Please allow a minute or two for all services to become fully operational.

#### Running Docker Compose Directly (Alternative to Setup Scripts)

If you prefer to manage your `.env` file manually or if the setup scripts encounter issues, you can still use Docker Compose:

1.  **Create/Configure `.env` File:** Ensure you have a valid `.env` file in the project root. You can copy `.env.example` to `.env` and fill in the necessary values (especially `ANTHROPIC_API_KEY`, `API_KEY`, and `PROJECT_CONFIG_PATH`).
2.  **Run Docker Compose:**
    ```bash
    docker compose up --build
    ```
    (Use `docker-compose` if you have an older standalone version).

### Manual Installation & Backend Setup

If you prefer to set up and run components manually or without Docker for all services:

1.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

2.  **Install Dependencies:**
    The project uses `pyproject.toml` for dependency management. Install the framework and its dependencies (the `[dev]` is for dev dependencies like pytest) in editable mode:
    ```bash
    pip install -e .[dev]
    ```
    This command allows you to make changes to the source code and have them immediately reflected without needing to reinstall.

3.  **Environment Variables Setup:**
    Before running the system, you need to set up your environment variables.

    a.  **Copy the Example File:** In the project root, copy the `.env.example` file to a new file named `.env`:
        ```bash
        cp .env.example .env
        ```

    b.  **Edit `.env`:** Open the newly created `.env` file and fill in your specific configurations and secrets. Pay close attention to comments like `#REPLACE` indicating values you must change.

    Key environment variables to configure in your `.env` file:

    *   **LLM API Key (Required):** You must provide an API key for the language model provider you intend to use. For example:
        *   `ANTHROPIC_API_KEY=your_anthropic_api_key`
        *   `OPENAI_API_KEY=your_openai_api_key`
        *   *(Add other provider keys as needed, e.g., `GEMINI_API_KEY`)*
        Only one key is strictly necessary to get started, depending on which LLM you configure your agents to use.
    *   `PROJECT_CONFIG_PATH` (Optional): Specifies the path to your main project configuration JSON file.
        *   If not set, the system defaults to looking for `aurite_config.json` in the root of the repository.
        *   You can set this to an absolute path or a path relative to the repository root (e.g., `config/projects/default.json`).
    *   `API_KEY` (Optional, for API server): A secret key to secure the FastAPI endpoints if you run the API server. Generate a strong random key if you use this. This is pre-configured if you use the `setup.sh` or `setup.bat` scripts.

    Other variables in the `.env` file (e.g., for Redis, database persistence like `AURITE_ENABLE_DB`, `AURITE_DB_URL`) are optional and only needed if you intend to use those specific features. Review all entries, especially those marked with `#REPLACE`, and configure them according to your needs.

    **Important Security Note: Encryption Key**

    *   **`AURITE_MCP_ENCRYPTION_KEY`**: This environment variable is used by the framework's `SecurityManager` to encrypt sensitive data.
        *   If not set, a key will be **auto-generated on startup**. This is convenient for quick local testing.
        *   **However, for any persistent deployment, or if you intend to use features that rely on encrypted storage (even for development), it is critical to set this to a strong, persistent, URL-safe base64-encoded 32-byte key.**
        *   Relying on an auto-generated key means that any encrypted data may become inaccessible if the application restarts and generates a new key.
        *   Please refer to `SECURITY.md` (to be created) for detailed information on generating, managing, and understanding the importance of this key. You can find `AURITE_MCP_ENCRYPTION_KEY` commented out in your `.env.example` file as a reminder.

4.  **Running the Backend API Server:**
    The primary way to interact with the framework is through its FastAPI server:
    ```bash
    python -m aurite.bin.api.api
    ```
    or use the `pyproject.toml` script:
    ```bash
    start-api
    ```
    (This script is available after running `pip install -e .[dev]` as described in the Manual Installation section. If using Docker, the API starts automatically within its container.)

    By default, it starts on `http://0.0.0.0:8000`. You can then send requests to its various endpoints to execute agents, register components, etc. (e.g., using Postman or `curl`).

### Frontend UI Setup

To set up and run the frontend developer UI for interacting with the Aurite Agents Framework:

**Note:** Ensure the backend API server (Step 4 in Manual Setup above) is running before starting the frontend if you are not using the Docker quickstart.

1.  **Navigate to the Frontend Directory:**
    Open a new terminal or use your existing one to change into the `frontend` directory:
    ```bash
    cd frontend
    ```

2.  **Install Frontend Dependencies:**
    If you don't have Yarn installed, you can install it by following the instructions on the [official Yarn website](https://classic.yarnpkg.com/en/docs/install).

    Inside the `frontend` directory, install the necessary Node.js packages using Yarn:
    ```bash
    yarn install
    ```

3.  **Start the Frontend Development Server:**
    Once dependencies are installed, start the Vite development server:
    ```bash
    yarn dev
    ```
    The frontend UI will typically be available in your web browser at `http://localhost:5173`.
