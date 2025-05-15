#!/bin/bash

# Define some colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Aurite Agents Setup Script${NC}"
echo -e "${BLUE}==========================${NC}"

# Check for Docker and Docker Compose
echo -e "\n${YELLOW}Checking prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker could not be found. Please install Docker.${NC}"
    exit 1
fi

if ! docker compose version &> /dev/null && ! docker-compose version &> /dev/null ; then
    echo -e "${RED}ERROR: Docker Compose (V2 plugin or standalone) could not be found. Please install Docker Compose.${NC}"
    exit 1
fi
DOCKER_COMPOSE_CMD=$(command -v docker-compose || echo "docker compose")
echo -e "${GREEN}Docker and Docker Compose found.${NC}"


# Handle .env file
echo -e "\n${YELLOW}Configuring .env file...${NC}"
ENV_FILE=".env"
ENV_EXAMPLE_FILE=".env.example"
NEW_API_KEY_VALUE="" # Variable to store the new API key if generated

if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}WARNING: An existing '$ENV_FILE' file was found.${NC}"
    read -p "Do you want to replace it with values from '$ENV_EXAMPLE_FILE' and user inputs? (y/N): " confirm_replace
    if [[ "$confirm_replace" != "y" && "$confirm_replace" != "Y" ]]; then
        echo "Skipping .env file modification."
    else
        if [ -f "$ENV_FILE" ] && [[ "$confirm_replace" == "y" || "$confirm_replace" == "Y" ]]; then
             echo "Backing up existing .env to .env.bak"
             cp "$ENV_FILE" ".env.bak"
        fi
        cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
        echo "'$ENV_FILE' created/updated from '$ENV_EXAMPLE_FILE'."

        read -p "Enter your ANTHROPIC_API_KEY: " anthropic_key
        if [ -n "$anthropic_key" ]; then
            sed -i.bak "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$anthropic_key|" "$ENV_FILE"
            echo -e "${GREEN}ANTHROPIC_API_KEY updated in '$ENV_FILE'.${NC}"
        else
            echo "Skipping ANTHROPIC_API_KEY update (no value provided)."
        fi

        echo "Generating a new local API_KEY..."
        if command -v openssl &> /dev/null; then
            NEW_API_KEY_VALUE=$(openssl rand -hex 32)
        else
            echo -e "${YELLOW}OpenSSL not found. Using a timestamp-based key (less secure, for local dev only).${NC}"
            NEW_API_KEY_VALUE="dev_key_$(date +%s)_$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 8)"
        fi
        sed -i.bak "s|^API_KEY=.*|API_KEY=$NEW_API_KEY_VALUE|" "$ENV_FILE"
        echo -e "${GREEN}API_KEY updated in '$ENV_FILE'.${NC}"
        echo -e "Your new API_KEY for the frontend UI is: ${GREEN}${NEW_API_KEY_VALUE}${NC}"
        echo -e "${YELLOW}Please copy this key. You will need it to authenticate with the API via the UI.${NC}"


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
        echo -e "${GREEN}Note: For the backend Docker container to connect to the PostgreSQL Docker container, AURITE_DB_HOST in '.env' should be 'postgres' (which is the default from .env.example).${NC}"

    fi
fi

# Clean up sed backup files only if they were created
find . -name "*.bak" -type f -delete &> /dev/null # Suppress output of find

echo -e "\n${GREEN}Environment setup phase complete.${NC}"

# Ask to install optional ML dependencies
echo -e "\n${YELLOW}Optional ML Dependencies...${NC}"
ML_REQUIREMENTS_FILE="ml_requirements.txt"
if [ -f "$ML_REQUIREMENTS_FILE" ]; then
    read -p "Some MCP servers require additional ML packages (e.g., sentence-transformers). Do you want to install them now from '$ML_REQUIREMENTS_FILE'? (y/N): " install_ml_deps
    if [[ "$install_ml_deps" == "y" || "$install_ml_deps" == "Y" ]]; then
        echo "Installing ML dependencies from '$ML_REQUIREMENTS_FILE'..."
        if command -v python &> /dev/null && python -m venv --help &> /dev/null; then
            if [ -z "$VIRTUAL_ENV" ]; then
                echo -e "${YELLOW}WARNING: Not currently in a Python virtual environment. Installing packages globally.${NC}"
                echo -e "${YELLOW}It is highly recommended to use a virtual environment. Activate one and re-run this part or install manually.${NC}"
                python -m pip install -r "$ML_REQUIREMENTS_FILE"
            else
                echo "Installing ML dependencies into the active virtual environment: $VIRTUAL_ENV"
                pip install -r "$ML_REQUIREMENTS_FILE"
            fi
        else
            echo -e "${YELLOW}WARNING: Python or venv module not found. Cannot automatically install ML packages.${NC}"
            echo "Please install them manually if needed: pip install -r $ML_REQUIREMENTS_FILE"
        fi
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}ML dependencies installed successfully.${NC}"
        else
            echo -e "${RED}ERROR: Failed to install ML dependencies. Please check the output and try manually.${NC}"
        fi
    else
        echo "Skipping installation of optional ML dependencies."
        echo "If you need them later, you can install them with: pip install -e .[ml] or pip install -r $ML_REQUIREMENTS_FILE"
    fi
else
    echo "Optional ML requirements file '$ML_REQUIREMENTS_FILE' not found. Skipping this step."
fi

# Run Docker Compose
echo -e "\n${YELLOW}Starting services with Docker Compose...${NC}"
$DOCKER_COMPOSE_CMD up -d --build

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Services started successfully!${NC}"
    echo -e "Backend should be available at ${BLUE}http://localhost:${PORT:-8000}${NC}"
    echo -e "Frontend should be available at ${BLUE}http://localhost:5173${NC}"
    # PostgreSQL is not exposed to host by default, so no message for it.
    if [ -n "$NEW_API_KEY_VALUE" ]; then
      echo -e "\n${YELLOW}Remember your API Key for the frontend UI: ${GREEN}${NEW_API_KEY_VALUE}${NC}"
    fi
else
    echo -e "\n${RED}ERROR: Docker Compose failed to start services. Check the output above.${NC}"
    exit 1
fi

exit 0
