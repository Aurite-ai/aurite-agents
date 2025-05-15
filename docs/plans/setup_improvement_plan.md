# Implementation Plan: Project Setup Improvements

**Version:** 1.0
**Date:** 2025-05-15
**Author(s):** Ryan, Gemini
**Related Design Document (Optional):** N/A

## 1. Goals
*   Improve the clarity and logical flow of project setup instructions in `README.md`.
*   Enable easy startup of backend, frontend, and PostgreSQL services using Docker Compose.
*   Provide a `setup.sh` script to automate initial environment configuration and service startup.

## 2. Scope
*   **In Scope:**
    *   Reorganizing `README.md` content, focusing on installation and setup sections.
    *   Creating `frontend/Dockerfile` for the frontend application.
    *   Creating `docker-compose.yml` in the project root to manage backend, frontend, and PostgreSQL services.
    *   Modifying `frontend/vite.config.ts` to proxy API requests to the backend service in Docker.
    *   Creating `setup.sh` in the project root for environment setup and Docker Compose execution.
*   **Out of Scope (for this plan):**
    *   Creating a Windows equivalent of the setup script (e.g., `setup.bat` or `setup.ps1`) - can be a future enhancement.
    *   Packaging the project for PyPI.
    *   Resolving dynamic path handling for PyPI distribution.
    *   Implementing `SECURITY.md`.

## 3. Prerequisites
*   Backend `Dockerfile.dev` is functional.
*   Node.js and Yarn are available for creating/testing the frontend Dockerfile.
*   Docker and Docker Compose (or `docker compose`) are installed on the development machine for testing the script and Docker setup.
*   `openssl` (or a similar tool) available for generating a random API key in `setup.sh`.

## 4. Implementation Steps

**Phase 1: README.md Reorganization**

1.  **Step 1.1: Analyze Current README.md and Define New Structure**
    *   **File(s):** `README.md`
    *   **Action:**
        *   Review the existing `README.md` (provided by user).
        *   Define a new, more logical structure as follows:
            1.  Title
            2.  Getting Started (Introductory sentence)
                *   Prerequisites
                *   Installation & Backend Setup
                    1.  Clone Repo
                    2.  Create Venv
                    3.  Install Dependencies (`pip install -e .[dev]`)
                    4.  Environment Variables Setup (Copy `.env.example` to `.env`, highlight key variables: `PROJECT_CONFIG_PATH`, `API_KEY`, `ANTHROPIC_API_KEY`, `AURITE_MCP_ENCRYPTION_KEY`. Refer to `.env.example` for details.)
                    5.  Running the Backend API Server (`python -m src.bin.api.api` or `start-api`)
                *   Frontend UI Setup
                    1.  Navigate to `frontend` directory.
                    2.  Install Frontend Dependencies (`yarn install`).
                    3.  Start Frontend Development Server (`yarn dev`). (Add a note that the backend server should be running).
            3.  Architecture Overview
            4.  Core Concepts for Users
            5.  Configuration System Overview (User Perspective) (Move existing "Configuration Overview (User Perspective)" section here).
            6.  Other Entrypoints (CLI, Worker) (Consolidate information about CLI and Worker from "Basic Usage").
            7.  Simplified Directory Structure
            8.  Further Documentation
            9.  Contributing
    *   **Verification:** The proposed structure logically orders setup steps, ensuring backend is configured before frontend is started. Key configuration information is accessible.

2.  **Step 1.2: Implement README.md Changes**
    *   **File(s):** `README.md`
    *   **Action:**
        *   Apply the structural changes outlined in Step 1.1 to `README.md`.
        *   Ensure all instructions are clear, accurate, and code blocks are correctly formatted.
        *   Update any internal links if section titles change significantly.
    *   **Verification:**
        *   The `README.md` file is updated with the new structure.
        *   A manual review confirms improved clarity and flow.

**Phase 2: Docker Compose Setup**

1.  **Step 2.1: Create Frontend Dockerfile**
    *   **File(s):** `frontend/Dockerfile` (new file)
    *   **Action:** Create the Dockerfile with the following content:
        ```dockerfile
        # Stage 1: Build
        FROM node:lts-alpine as builder
        WORKDIR /app
        COPY package.json yarn.lock ./
        RUN yarn install --frozen-lockfile
        COPY . .
        # If you have a build step for production, add it here
        # RUN yarn build

        # Stage 2: Development server
        FROM node:lts-alpine
        WORKDIR /app
        COPY --from=builder /app ./
        # Ensure vite is a dependency, or install globally if needed for dev
        # RUN npm install -g vite # Or ensure it's in devDependencies
        EXPOSE 5173
        CMD ["yarn", "dev", "--host", "0.0.0.0"]
        ```
    *   **Verification:** The `frontend/Dockerfile` is created. (Local build test optional at this stage, will be tested with docker-compose).

2.  **Step 2.2: Update Vite Configuration for Proxying**
    *   **File(s):** `frontend/vite.config.ts`
    *   **Action:** Modify the `server` configuration in `frontend/vite.config.ts` to proxy API requests:
        ```typescript
        import { defineConfig } from 'vite';
        import react from '@vitejs/plugin-react';

        export default defineConfig({
          plugins: [react()],
          server: {
            host: '0.0.0.0', // Exposes server to the network, crucial for Docker
            port: 5173,
            proxy: {
              '/api': {
                target: 'http://backend:8000', // 'backend' will be the service name in docker-compose.yml
                changeOrigin: true,
                // Assuming backend FastAPI routes are NOT prefixed with /api (e.g., /projects/create_file)
                // If backend routes ARE prefixed with /api (e.g. /api/projects/create_file), then remove the rewrite line.
                rewrite: (path) => path.replace(/^\/api/, ''),
              },
            },
          },
        });
        ```
        *Note: Confirm if backend FastAPI routes are prefixed with `/api`. If they are (e.g., `@router.post("/api/projects/...")`), the `rewrite` line should be removed. If backend routes are at root (e.g., `@router.post("/projects/...")`), the `rewrite` is necessary.*
    *   **Verification:** `frontend/vite.config.ts` is updated with the proxy configuration.

3.  **Step 2.3: Create `docker-compose.yml`**
    *   **File(s):** `docker-compose.yml` (new file in project root)
    *   **Action:** Create the `docker-compose.yml` file:
        ```yaml
        version: '3.8'

        services:
          postgres:
            image: postgres:15-alpine
            container_name: aurite_postgres
            environment:
              POSTGRES_USER: ${AURITE_DB_USER:-postgres_user} # Use .env or default
              POSTGRES_PASSWORD: ${AURITE_DB_PASSWORD:-postgres_password} # Use .env or default
              POSTGRES_DB: ${AURITE_DB_NAME:-aurite_storage}   # Use .env or default
            volumes:
              - postgres_data:/var/lib/postgresql/data
            ports:
              - "${AURITE_DB_PORT:-5432}:5432" # Expose DB port if needed externally
            networks:
              - aurite_network
            restart: unless-stopped

          backend:
            build:
              context: .
              dockerfile: Dockerfile.dev
            container_name: aurite_backend
            ports:
              - "${PORT:-8000}:8000"
            volumes:
              - ./src:/app/src
              - ./config:/app/config
              # Add other necessary volume mounts for development if any
            env_file:
              - .env # Load environment variables from .env file
            depends_on:
              - postgres
            networks:
              - aurite_network
            restart: unless-stopped
            # Ensure PROJECT_CONFIG_PATH in .env is relative to /app inside container if not absolute
            # Or ensure it's an absolute path that's valid inside the container.
            # Dockerfile.dev sets PROJECT_CONFIG_PATH=/app/config/projects/testing_config.json
            # This will be overridden by .env if .env has PROJECT_CONFIG_PATH.

          frontend:
            build:
              context: ./frontend
              dockerfile: Dockerfile # Uses frontend/Dockerfile created in Step 2.1
            container_name: aurite_frontend
            ports:
              - "5173:5173"
            volumes:
              - ./frontend/src:/app/src # For hot reloading of frontend source
              - ./frontend/public:/app/public
              # Add other necessary volume mounts for development if any
            depends_on:
              - backend
            networks:
              - aurite_network
            restart: unless-stopped

        networks:
          aurite_network:
            driver: bridge

        volumes:
          postgres_data:
            driver: local
        ```
    *   **Verification:** `docker-compose.yml` is created in the project root.

**Phase 3: Create `setup.sh` Script**

1.  **Step 3.1: Design and Implement `setup.sh`**
    *   **File(s):** `setup.sh` (new file in project root)
    *   **Action:** Create the script with the following logic:
        ```bash
        #!/bin/bash

        echo "Aurite Agents Setup Script"
        echo "=========================="

        # Check for Docker and Docker Compose
        if ! command -v docker &> /dev/null; then
            echo "ERROR: Docker could not be found. Please install Docker."
            exit 1
        fi

        if ! docker compose version &> /dev/null && ! docker-compose version &> /dev/null ; then
            echo "ERROR: Docker Compose (V2 plugin or standalone) could not be found. Please install Docker Compose."
            exit 1
        fi
        DOCKER_COMPOSE_CMD=$(command -v docker-compose || echo "docker compose")


        # Handle .env file
        ENV_FILE=".env"
        ENV_EXAMPLE_FILE=".env.example"

        if [ -f "$ENV_FILE" ]; then
            echo "WARNING: An existing '$ENV_FILE' file was found."
            read -p "Do you want to replace it with values from '$ENV_EXAMPLE_FILE' and user inputs? (y/N): " confirm_replace
            if [[ "$confirm_replace" != "y" && "$confirm_replace" != "Y" ]]; then
                echo "Skipping .env file modification."
            else
                echo "Backing up existing .env to .env.bak"
                cp "$ENV_FILE" ".env.bak"
                cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
                echo "'$ENV_FILE' has been replaced with '$ENV_EXAMPLE_FILE'."
            fi
        else
            cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
            echo "'$ENV_EXAMPLE_FILE' copied to '$ENV_FILE'."
        fi

        # Prompt for ANTHROPIC_API_KEY
        read -p "Enter your ANTHROPIC_API_KEY: " anthropic_key
        if [ -n "$anthropic_key" ]; then
            # Use a different delimiter for sed if the key might contain slashes
            sed -i.bak "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$anthropic_key|" "$ENV_FILE"
            echo "ANTHROPIC_API_KEY updated in '$ENV_FILE'."
        else
            echo "Skipping ANTHROPIC_API_KEY update (no value provided)."
        fi

        # Generate and set API_KEY
        echo "Generating a new local API_KEY..."
        # Check for openssl, otherwise use a simpler method or ask user
        if command -v openssl &> /dev/null; then
            new_api_key=$(openssl rand -hex 32)
        else
            echo "OpenSSL not found. Using a timestamp-based key (less secure, for local dev only)."
            new_api_key="dev_key_$(date +%s)_$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 8)"
        fi
        sed -i.bak "s|^API_KEY=.*|API_KEY=$new_api_key|" "$ENV_FILE"
        echo "API_KEY updated in '$ENV_FILE'."

        # Project Configuration Path
        CONFIG_PROJECTS_DIR="./config/projects"
        if [ -d "$CONFIG_PROJECTS_DIR" ]; then
            echo "Available project configurations in '$CONFIG_PROJECTS_DIR':"
            projects=()
            i=0
            for file in "$CONFIG_PROJECTS_DIR"/*.json; do
                if [ -f "$file" ]; then
                    projects+=("$(basename "$file")")
                    echo "  $i) $(basename "$file")"
                    i=$((i+1))
                fi
            done

            if [ ${#projects[@]} -eq 0 ]; then
                echo "No project JSON files found in $CONFIG_PROJECTS_DIR."
            else
                read -p "Select a project configuration by number (or press Enter to skip): " project_choice
                if [[ "$project_choice" =~ ^[0-9]+$ ]] && [ "$project_choice" -lt "${#projects[@]}" ]; then
                    selected_project_file_name="${projects[$project_choice]}"
                    # PROJECT_CONFIG_PATH should be relative to the project root (e.g., config/projects/file.json)
                    # This works because the backend container's WORKDIR is /app, and config is mounted to /app/config.
                    rel_project_config_path="config/projects/$selected_project_file_name"
                    # Ensure the sed command correctly escapes the path if it contains special characters, though unlikely for this format.
                    # Using a different delimiter for sed to handle potential slashes in paths, though $rel_project_config_path here is unlikely to have them.
                    sed -i.bak "s|^PROJECT_CONFIG_PATH=.*|PROJECT_CONFIG_PATH=$rel_project_config_path|" "$ENV_FILE"
                    echo "PROJECT_CONFIG_PATH set to '$rel_project_config_path' in '$ENV_FILE'."
                else
                    echo "Skipping project configuration selection or invalid input."
                fi
            fi
        else
            echo "Directory '$CONFIG_PROJECTS_DIR' not found. Skipping project selection."
        fi

        # Clean up sed backup files
        find . -name "*.bak" -type f -delete

        echo "Environment setup complete."

        # Run Docker Compose
        echo "Starting services with Docker Compose..."
        $DOCKER_COMPOSE_CMD up -d --build

        if [ $? -eq 0 ]; then
            echo "Services started successfully!"
            echo "Backend should be available at http://localhost:${PORT:-8000}"
            echo "Frontend should be available at http://localhost:5173"
            echo "PostgreSQL (if configured for external access) on port ${AURITE_DB_PORT:-5432}"
        else
            echo "ERROR: Docker Compose failed to start services. Check the output above."
            exit 1
        fi

        exit 0
        ```
    *   Make the script executable: `chmod +x setup.sh`.
    *   **Verification:**
        *   `setup.sh` is created and executable.
        *   Script correctly handles `.env` creation/replacement.
        *   Script prompts for and updates `ANTHROPIC_API_KEY`.
        *   Script generates and updates `API_KEY`.
        *   Script lists projects and updates `PROJECT_CONFIG_PATH` with an absolute path.
        *   Script attempts to run `docker compose up -d --build`.

## 5. Testing Strategy
*   **README.md:** Manual review of the rendered Markdown to ensure clarity, correctness of instructions, and logical flow. Follow the setup steps manually to verify.
*   **Docker Compose:**
    *   Run `docker compose build` (or the command used by the script, e.g. `docker compose up --build`) to ensure images build successfully.
    *   Run `docker compose up -d`.
    *   Verify all containers (backend, frontend, postgres) are running (`docker compose ps`).
    *   Test backend API endpoint (e.g., `/health` or a simple API call via `curl` or Postman) from the host.
    *   Access frontend UI in a browser (e.g., `http://localhost:5173`) and test an interaction that calls the backend API (e.g., listing projects) to verify Vite proxy and backend connectivity.
    *   Check logs of each container for errors (`docker compose logs backend`, `docker compose logs frontend`).
*   **`setup.sh` Script:**
    *   Test script execution in various scenarios:
        *   No `.env` file exists.
        *   `.env` file exists, user chooses to replace.
        *   `.env` file exists, user chooses not to replace.
        *   User provides `ANTHROPIC_API_KEY`.
        *   User skips `ANTHROPIC_API_KEY`.
        *   User selects a project config.
        *   User skips project config selection.
    *   Verify that the `.env` file is correctly modified after script execution.
    *   Verify that `docker compose up -d --build` is called and services start.
    *   Test on a system without Docker/Docker Compose to verify the prerequisite checks.

## 6. Potential Risks & Mitigation
*   **README Clarity:** Instructions might still be unclear to new users.
    *   **Mitigation:** Get feedback from someone unfamiliar with the project after changes are made.
*   **Docker Configuration Complexity:** Docker setup might have unforeseen issues on different OS or Docker versions.
    *   **Mitigation:** Test on common developer OS (Linux, macOS). Clearly document Docker/Compose version prerequisites if specific versions are needed.
*   **Backend API Path for Proxy:** The assumption about backend API paths (prefixed with `/api` or not) for the Vite proxy might be incorrect.
    *   **Mitigation:** During implementation of Step 2.2, verify the actual backend API route structure. Adjust the `rewrite` rule in `vite.config.ts` or backend FastAPI app's root path as necessary. This is noted in the step.
*   **`.env` Handling in `setup.sh`:** `sed` commands for `.env` modification can be brittle if keys contain special characters or if the `.env.example` format changes significantly.
    *   **Mitigation:** Use robust `sed` patterns. Advise users that `setup.sh` is for initial setup and complex `.env` management might require manual edits.
*   **Absolute Path for `PROJECT_CONFIG_PATH`:** Ensuring the script correctly generates an absolute path that works both locally and inside the backend container if it relies on it. The current `Dockerfile.dev` sets a default `PROJECT_CONFIG_PATH=/app/config/projects/testing_config.json`. If the `.env` file (copied into the container or used by `env_file`) specifies an absolute host path, it won't work unless that path is also mounted and valid inside the container. The `docker-compose.yml` mounts `./config:/app/config`. So, if `PROJECT_CONFIG_PATH` in `.env` is set to `/app/config/projects/some_project.json` by the script (after converting from host absolute path or by using a relative path that becomes `/app/...` inside container), it should work. The script currently generates a host absolute path. This needs to be compatible with the container's view or the application needs to be robust in path handling.
    *   **Mitigation:** The backend should ideally resolve `PROJECT_CONFIG_PATH` relative to a known root within the container (e.g., `/app`). The `setup.sh` should set `PROJECT_CONFIG_PATH=config/projects/your_project.json` (relative path) in the `.env` file. The backend application, when running in Docker, will then interpret this relative to its working directory `/app`. The `Dockerfile.dev` already sets `ENV PROJECT_CONFIG_PATH=/app/config/projects/testing_config.json`. The `.env` file loaded by `docker-compose` will override this. If `PROJECT_CONFIG_PATH` in `.env` is `config/projects/default.json`, then inside the container (WORKDIR /app), it will resolve to `/app/config/projects/default.json`. This is the simplest. The script should write this relative path. I will adjust the script plan.

    *Correction for `setup.sh` regarding `PROJECT_CONFIG_PATH`*:
    The script should set `PROJECT_CONFIG_PATH` to a path relative to the project root, like `config/projects/selected_file.json`. When `docker-compose` uses this `.env` file for the `backend` service (which has `WORKDIR /app`), the application inside the container will see this path relative to `/app`. This is fine because `config` is mounted to `/app/config`.

## 7. Open Questions & Discussion Points
*   Confirm the exact behavior of backend API routes: Are they prefixed with `/api` (e.g., `/api/projects/create`) or at the root (e.g., `/projects/create`)? This impacts the Vite proxy `rewrite` rule. (Assumption for now: backend routes are at root, so rewrite is needed).
*   Should the `setup.sh` script offer to install Python project dependencies (`pip install -e .[dev]`) inside a virtual environment as part of its run? (Currently out of scope, focuses on `.env` and Docker).
*   Should the `setup.sh` script offer to run `yarn install` in the `frontend` directory? (Currently out of scope).

## 8. Rollback Plan (Optional - for critical changes)
*   Revert `README.md` from Git.
*   Delete `frontend/Dockerfile`, `docker-compose.yml`, `setup.sh`.
*   Revert changes to `frontend/vite.config.ts` from Git.
*   Restore `.env` from `.env.bak` if created by the script.
