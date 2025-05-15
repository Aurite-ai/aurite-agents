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
