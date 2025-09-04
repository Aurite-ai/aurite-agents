#!/bin/bash
# =============================================================================
# Aurite Agents Framework - Docker Entrypoint Script
# =============================================================================
# This script handles initialization, project detection, and service startup
# for the Aurite Agents Docker container.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [[ "${LOG_LEVEL}" == "DEBUG" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Function to check if we're in a valid Aurite project
check_aurite_project() {
    log_debug "Checking for .aurite file in current directory: $(pwd)"

    if [[ -f ".aurite" ]]; then
        log_info "Found .aurite file - valid Aurite project detected"
        return 0
    fi

    # Check parent directories (ConfigManager searches upward)
    local current_dir="$(pwd)"
    local parent_dir="$(dirname "$current_dir")"

    while [[ "$parent_dir" != "/" && "$parent_dir" != "$current_dir" ]]; do
        log_debug "Checking parent directory: $parent_dir"
        if [[ -f "$parent_dir/.aurite" ]]; then
            log_info "Found .aurite file in parent directory: $parent_dir"
            return 0
        fi
        current_dir="$parent_dir"
        parent_dir="$(dirname "$current_dir")"
    done

    log_warn "No .aurite file found in current directory or parent directories"
    return 1
}

# Function to initialize a new Aurite project
init_aurite_project() {
    log_info "Initializing new Aurite project..."

    # Check if directory is empty (except for hidden files)
    if [[ $(ls -A . 2>/dev/null | grep -v '^\.' | wc -l) -gt 0 ]]; then
        log_error "Directory is not empty. Cannot initialize project in non-empty directory."
        log_error "Please mount an empty directory or an existing Aurite project."
        exit 1
    fi

    # Set up Python path for aurite CLI
    export PYTHONPATH="/app/src:$PYTHONPATH"

    # Create a default workspace in the current directory
    log_info "Creating workspace 'default_workspace'..."
    if python -m aurite.bin.cli.main init --workspace default_workspace; then
        log_info "Workspace created successfully"
    else
        log_error "Failed to create workspace"
        return 1
    fi

    # Create a default project within the workspace
    log_info "Creating project 'default'..."
    if python -m aurite.bin.cli.main init --project default; then
        log_info "Project created successfully"
    else
        log_error "Failed to create project"
        return 1
    fi

    log_info "Aurite initialization complete!"

    # Change to the project directory so the API server can find the .aurite file
    log_info "Changing to project directory: default"
    cd default

    return 0
}

# Function to validate required environment variables
validate_environment() {
    log_debug "Validating environment variables..."

    # Check for API_KEY (required for API server)
    if [[ -z "${API_KEY}" ]]; then
        log_error "API_KEY environment variable is required"
        log_error "Please set API_KEY to a secure value for API authentication"
        exit 1
    fi

    # Validate database configuration if enabled
    if [[ "${AURITE_ENABLE_DB}" == "true" ]]; then
        log_info "Database mode enabled - validating database configuration..."

        if [[ "${AURITE_DB_TYPE}" == "postgres" ]]; then
            local missing_vars=()
            [[ -z "${AURITE_DB_HOST}" ]] && missing_vars+=("AURITE_DB_HOST")
            [[ -z "${AURITE_DB_USER}" ]] && missing_vars+=("AURITE_DB_USER")
            [[ -z "${AURITE_DB_PASSWORD}" ]] && missing_vars+=("AURITE_DB_PASSWORD")
            [[ -z "${AURITE_DB_NAME}" ]] && missing_vars+=("AURITE_DB_NAME")

            if [[ ${#missing_vars[@]} -gt 0 ]]; then
                log_error "PostgreSQL database configuration incomplete"
                log_error "Missing required environment variables: ${missing_vars[*]}"
                exit 1
            fi

            log_info "PostgreSQL configuration validated"
        elif [[ "${AURITE_DB_TYPE}" == "sqlite" ]]; then
            log_info "SQLite configuration - using path: ${AURITE_DB_PATH}"
            # Ensure the directory exists
            mkdir -p "$(dirname "${AURITE_DB_PATH}")"
        else
            log_error "Invalid AURITE_DB_TYPE: ${AURITE_DB_TYPE}"
            log_error "Supported values: sqlite, postgres"
            exit 1
        fi
    else
        log_info "File-based mode enabled - no database configuration needed"
    fi
}

# Function to wait for database (if using PostgreSQL)
wait_for_database() {
    if [[ "${AURITE_ENABLE_DB}" == "true" && "${AURITE_DB_TYPE}" == "postgres" ]]; then
        log_info "Waiting for PostgreSQL database to be ready..."

        local max_attempts=30
        local attempt=1

        while [[ $attempt -le $max_attempts ]]; do
            if python3 -c "
import psycopg2
import sys
try:
    conn = psycopg2.connect(
        host='${AURITE_DB_HOST}',
        port='${AURITE_DB_PORT:-5432}',
        user='${AURITE_DB_USER}',
        password='${AURITE_DB_PASSWORD}',
        database='${AURITE_DB_NAME}',
        connect_timeout=5
    )
    conn.close()
    print('Database connection successful')
    sys.exit(0)
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
                log_info "Database is ready!"
                break
            fi

            log_info "Database not ready yet (attempt $attempt/$max_attempts), waiting 2 seconds..."
            sleep 2
            ((attempt++))
        done

        if [[ $attempt -gt $max_attempts ]]; then
            log_error "Database failed to become ready after $max_attempts attempts"
            exit 1
        fi
    fi
}

# Function to display startup information
display_startup_info() {
    log_info "=============================================="
    log_info "Aurite Agents Framework v0.3.28"
    log_info "=============================================="
    log_info "Working directory: $(pwd)"
    log_info "Python path: ${PYTHONPATH}"
    log_info "API server: http://0.0.0.0:${AURITE_API_PORT}"
    log_info "Database mode: ${AURITE_ENABLE_DB}"
    if [[ "${AURITE_ENABLE_DB}" == "true" ]]; then
        log_info "Database type: ${AURITE_DB_TYPE}"
    fi
    log_info "Log level: ${LOG_LEVEL}"
    log_info "=============================================="
}

# Main execution
main() {
    log_info "Starting Aurite Agents container..."

    # Display startup information
    display_startup_info

    # Validate environment variables
    validate_environment

    # Check if we have a valid Aurite project
    if ! check_aurite_project; then
        if [[ "${AURITE_AUTO_INIT}" == "true" ]]; then
            log_info "AURITE_AUTO_INIT is enabled - initializing new project"
            init_aurite_project
        else
            log_error "No Aurite project found and auto-initialization is disabled"
            log_error ""
            log_error "To fix this issue, you can:"
            log_error "1. Mount an existing Aurite project directory to /app/project"
            log_error "2. Enable auto-initialization with -e AURITE_AUTO_INIT=true"
            log_error "3. Initialize manually: docker exec -it <container> aurite init"
            log_error ""
            log_error "Example with existing project:"
            log_error "  docker run -v /path/to/my-project:/app/project aurite/aurite-agents"
            log_error ""
            log_error "Example with auto-init:"
            log_error "  docker run -v /path/to/empty-dir:/app/project -e AURITE_AUTO_INIT=true aurite/aurite-agents"
            exit 1
        fi
    fi

    # Wait for database if needed
    wait_for_database

    # Set up Python path
    export PYTHONPATH="/app/src:${PYTHONPATH}"

    log_info "Starting application with command: $*"

    # Execute the provided command
    exec "$@"
}

# Handle special cases for direct command execution
if [[ "$1" == "bash" || "$1" == "sh" || "$1" == "/bin/bash" || "$1" == "/bin/sh" ]]; then
    log_info "Starting interactive shell..."
    exec "$@"
elif [[ "$1" == "aurite" ]]; then
    log_info "Running aurite CLI command..."
    export PYTHONPATH="/app/src:${PYTHONPATH}"
    exec python -c "from aurite.bin.cli import app; import sys; sys.argv = ['aurite'] + sys.argv[1:]; app()" "${@:2}"
elif [[ "$1" == "python" && "$2" == "-m" && "$3" == "aurite"* ]]; then
    log_info "Running aurite Python module..."
    export PYTHONPATH="/app/src:${PYTHONPATH}"
    exec "$@"
else
    # Run main initialization logic
    main "$@"
fi
