#!/bin/bash
# =============================================================================
# Aurite Agents Framework - Docker Entrypoint Script
# =============================================================================
# This script provides a minimal, context-aware entrypoint for the Aurite
# base Docker image. It only enforces requirements when actually needed.
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

# Function to set up Python path
setup_python_path() {
    export PYTHONPATH="/usr/local/lib/python3.12/site-packages:${PYTHONPATH}"
    log_debug "Python path set: ${PYTHONPATH}"
}

# Function to validate API server requirements
validate_api_requirements() {
    log_info "Validating API server requirements..."

    # API_KEY is required for API server
    if [[ -z "${API_KEY}" ]]; then
        log_warn "API_KEY environment variable is not set"
        log_warn "The API server requires authentication. Please set API_KEY to a secure value."
        log_warn "Example: -e API_KEY=$(openssl rand -hex 32)"
        # Don't exit - let the API server handle the missing key
    fi

    # Check for .aurite file (optional for API, just warn)
    if [[ ! -f ".aurite" && ! -f "../.aurite" && ! -f "../../.aurite" ]]; then
        log_warn "No .aurite file found - API may not have access to project configurations"
        log_info "To create a project: aurite init --project myproject"
    fi
}

# Function to wait for database (if using PostgreSQL)
wait_for_database() {
    if [[ "${AURITE_ENABLE_DB}" == "true" && "${AURITE_DB_TYPE}" == "postgres" ]]; then
        log_info "Database mode enabled - waiting for PostgreSQL..."

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

            log_debug "Database not ready (attempt $attempt/$max_attempts), waiting..."
            sleep 2
            ((attempt++))
        done

        if [[ $attempt -gt $max_attempts ]]; then
            log_error "Database failed to become ready after $max_attempts attempts"
            log_error "Continuing anyway - API may fail to connect to database"
        fi
    fi
}

# Function to export configurations to database
export_configurations() {
    # Check if auto-export is enabled (default is true unless explicitly disabled)
    if [[ "${AURITE_AUTO_EXPORT}" == "false" ]]; then
        log_info "AURITE_AUTO_EXPORT is disabled - skipping configuration export"
        return 0
    fi

    if [[ "${AURITE_ENABLE_DB}" == "true" ]]; then
        log_info "Auto-exporting configurations to database..."
        log_debug "This will sync all configurations from files to the database"

        # Run the export command
        if python -m aurite.bin.cli.main export 2>&1 | while IFS= read -r line; do
            # Log each line from the export command with [EXPORT] prefix
            echo -e "${BLUE}[EXPORT]${NC} $line"
        done; then
            log_info "Configuration export completed successfully"
        else
            log_warn "Configuration export failed or partially completed"
            log_warn "The API will continue but may use outdated configurations"
            # Don't exit on failure - the API can still run
        fi
    else
        log_debug "Database mode is disabled - skipping configuration export"
    fi
}

# Function to display startup banner
display_banner() {
    log_info "=============================================="
    log_info "Aurite Agents Framework v0.4.0"
    log_info "=============================================="
    log_info "Container mode: $1"
    log_info "Working directory: $(pwd)"
    if [[ "${AURITE_ENABLE_DB}" == "true" ]]; then
        log_info "Database: ${AURITE_DB_TYPE}"
    fi
    log_info "=============================================="
}

# Main execution logic
main() {
    # Always set up Python path
    setup_python_path

    # Determine what we're running based on the command
    case "$1" in
        # Interactive shells - just pass through
        bash|sh|/bin/bash|/bin/sh)
            log_info "Starting interactive shell..."
            exec "$@"
            ;;

        # Aurite CLI - minimal setup
        aurite)
            display_banner "CLI"
            exec python -m aurite.bin.cli.main "${@:2}"
            ;;

        # Python module execution
        python)
            if [[ "$2" == "-m" ]]; then
                case "$3" in
                    # API server via module
                    uvicorn*|aurite.bin.api*)
                        display_banner "API Server"
                        validate_api_requirements
                        wait_for_database
                        export_configurations
                        exec "$@"
                        ;;
                    # Aurite CLI via module
                    aurite.bin.cli*)
                        display_banner "CLI"
                        exec "$@"
                        ;;
                    # Other Python modules
                    *)
                        log_debug "Running Python module: $3"
                        exec "$@"
                        ;;
                esac
            else
                # Regular Python execution
                exec "$@"
            fi
            ;;

        # Direct uvicorn execution (API server)
        uvicorn*)
            display_banner "API Server"
            validate_api_requirements
            wait_for_database
            export_configurations
            exec "$@"
            ;;

        # Any other command - just pass through
        *)
            log_debug "Executing command: $1"
            exec "$@"
            ;;
    esac
}

# Run main logic with all arguments (including those from CMD if no args provided)
main "$@"
