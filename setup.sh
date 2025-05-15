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
        # If user skips .env modification, we don't need to ask for other .env values
    else
        # This block executes if user chose 'y' to replace or if .env didn't exist
        if [ -f "$ENV_FILE" ] && [[ "$confirm_replace" == "y" || "$confirm_replace" == "Y" ]]; then
             echo "Backing up existing .env to .env.bak"
             cp "$ENV_FILE" ".env.bak"
        fi
        cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
        echo "'$ENV_FILE' created/updated from '$ENV_EXAMPLE_FILE'."

        # Prompt for ANTHROPIC_API_KEY
        read -p "Enter your ANTHROPIC_API_KEY: " anthropic_key
        if [ -n "$anthropic_key" ]; then
            sed -i.bak "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$anthropic_key|" "$ENV_FILE"
            echo "ANTHROPIC_API_KEY updated in '$ENV_FILE'."
        else
            echo "Skipping ANTHROPIC_API_KEY update (no value provided)."
        fi

        # Generate and set API_KEY
        echo "Generating a new local API_KEY..."
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
                    rel_project_config_path="config/projects/$selected_project_file_name"
                    sed -i.bak "s|^PROJECT_CONFIG_PATH=.*|PROJECT_CONFIG_PATH=$rel_project_config_path|" "$ENV_FILE"
                    echo "PROJECT_CONFIG_PATH set to '$rel_project_config_path' in '$ENV_FILE'."
                else
                    echo "Skipping project configuration selection or invalid input."
                fi
            fi
        else
            echo "Directory '$CONFIG_PROJECTS_DIR' not found. Skipping project selection."
        fi
        echo "Note: For the backend Docker container to connect to the PostgreSQL Docker container, AURITE_DB_HOST in '.env' should be 'postgres' (which is the default from .env.example)."

    fi
fi # End of initial if [ -f "$ENV_FILE" ] block

# Clean up sed backup files only if they were created
find . -name "*.bak" -type f -delete

echo "Environment setup complete."

# Ask to install optional ML dependencies
ML_REQUIREMENTS_FILE="ml_requirements.txt"
if [ -f "$ML_REQUIREMENTS_FILE" ]; then
    read -p "Some MCP servers require additional ML packages (e.g., sentence-transformers). Do you want to install them now from '$ML_REQUIREMENTS_FILE'? (y/N): " install_ml_deps
    if [[ "$install_ml_deps" == "y" || "$install_ml_deps" == "Y" ]]; then
        echo "Installing ML dependencies from '$ML_REQUIREMENTS_FILE'..."
        # Ensure pip is available and consider virtual environment
        if command -v python &> /dev/null && python -m venv --help &> /dev/null; then
            # Check if we are in an active virtual environment
            if [ -z "$VIRTUAL_ENV" ]; then
                echo "WARNING: Not currently in a Python virtual environment. Installing packages globally."
                echo "It is highly recommended to use a virtual environment. Activate one and re-run this part or install manually."
                python -m pip install -r "$ML_REQUIREMENTS_FILE"
            else
                echo "Installing ML dependencies into the active virtual environment: $VIRTUAL_ENV"
                pip install -r "$ML_REQUIREMENTS_FILE"
            fi
        else
            echo "WARNING: Python or venv module not found. Cannot automatically install ML packages."
            echo "Please install them manually if needed: pip install -r $ML_REQUIREMENTS_FILE"
        fi
        if [ $? -eq 0 ]; then
            echo "ML dependencies installed successfully."
        else
            echo "ERROR: Failed to install ML dependencies. Please check the output and try manually."
        fi
    else
        echo "Skipping installation of optional ML dependencies."
        echo "If you need them later, you can install them with: pip install -e .[ml] or pip install -r $ML_REQUIREMENTS_FILE"
    fi
else
    echo "Optional ML requirements file '$ML_REQUIREMENTS_FILE' not found. Skipping this step."
fi

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
