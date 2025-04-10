# Production Readiness Plan (Security, Packaging, Docker)

**Date:** 2025-04-10
**Status:** Proposed

## 1. Overview

This plan outlines the steps to enhance the Aurite Agents framework for production use and portability, focusing on three key areas:
1.  **Production Security:** Integrating GCP Secrets Manager for secure handling of environment variables/secrets.
2.  **Packaging:** Turning the framework into an installable Python package.
3.  **Containerization:** Creating and testing Dockerfiles for development and production deployment of the API server.

## 2. Goals

*   Securely manage sensitive configuration (API keys, credentials) required by MCP servers in production environments.
*   Enable easy installation and usage of the framework in different projects and environments.
*   Provide reliable container images for deploying the framework's API server.
*   Ensure the framework is extensible for future secret management solutions (e.g., AWS Secrets Manager).

## 3. High-Level Approach

### 3.1. Production Security (GCP Secrets Manager)

*   **Detailed Plan:** `docs/plans/production_security_plan.md` (To be created/refined)
*   **Key Steps:**
    *   Extend `ClientConfig` model (`src/host/models.py`) to allow specifying GCP secret IDs and corresponding environment variable names.
    *   Enhance `SecurityManager` (`src/host/foundation/security.py`) to use `google-cloud-secret-manager` library and Application Default Credentials (ADC) to fetch secrets.
    *   Modify `MCPHost` (`src/host/host.py`) to use the `SecurityManager` to resolve secrets specified in `ClientConfig` and inject them into the environment dictionary passed to the MCP server subprocess (`StdioServerParameters`).
    *   Update configuration loading (`src/config.py`) to handle the new `ClientConfig` fields.
    *   Add unit and integration tests to verify secret resolution and injection.
    *   Update documentation (`README.md`, `docs/framework_guide.md`, potentially `docs/security.md`).

### 3.2. Packaging (`pyproject.toml`)

*   **Detailed Plan:** (To be created)
*   **Key Steps:**
    *   Review and update `pyproject.toml`:
        *   Ensure all necessary metadata (name, version, author, description, license, etc.) is present.
        *   Verify `dependencies` list is accurate (including `google-cloud-secret-manager`).
        *   Verify `[project.optional-dependencies]` (like `dev`) are correct.
        *   Consider adding `[project.scripts]` to create command-line entry points for `src/bin/api.py`, `src/bin/cli.py`, `src/bin/worker.py`.
    *   Build source distribution (`sdist`) and wheel (`bdist_wheel`) using `python -m build`.
    *   Test local installation (`pip install dist/*.whl`) in a clean virtual environment.
    *   Test importing and using core components (e.g., `MCPHost`, `Agent`) after installation.
    *   Decide on distribution strategy (internal artifact repository, private PyPI, public PyPI). Initially target internal use.

### 3.3. Containerization (Docker)

*   **Detailed Plan:** (To be created)
*   **Key Steps:**
    *   Review and correct `Dockerfile` (production) and `Dockerfile.dev` (development):
        *   Ensure base images are appropriate (`python:3.12-slim`).
        *   Verify build stages and dependency installation (use the built wheel for production).
        *   Correct `CMD` instruction to run the FastAPI server (`src/bin/api.py`, likely via `uvicorn src.bin.api:app ...` or `python -m src.bin.api`).
        *   Confirm exposed ports (`EXPOSE`) match the application's configuration (default 8000).
        *   Validate `HEALTHCHECK` instruction targets the correct port and path (`/health`).
        *   Ensure non-root user (`appuser`) is used correctly.
    *   Integrate GCP Secrets Management:
        *   Determine how ADC will be provided to the container (e.g., mounting service account keys, workload identity). Update Dockerfiles or add documentation/scripts as needed.
    *   Build Docker images (`docker build ...`).
    *   Test container startup and health checks (`docker run ...`).
    *   Test API functionality by sending requests to the containerized application.

## 4. Next Steps

1.  Refine and finalize the detailed plan for Production Security (`docs/plans/production_security_plan.md`).
2.  Implement the Production Security feature.
3.  Create detailed plans for Packaging and Containerization.
4.  Implement Packaging and Containerization features.
