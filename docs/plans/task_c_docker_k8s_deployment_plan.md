# Implementation Plan: Task C - Dockerfile Verification & GKE Deployment Testing

**Version:** 1.1
**Date:** 2025-05-14
**Author(s):** Ryan, Gemini
**Related Design Document (Optional):** N/A (Referencing `docs/plans/overarching_open_source_plan.md` and `k8s/README.md`)

## 1. Goals
*   Verify and update `Dockerfile.dev`, `Dockerfile` (non-dev), and `.dockerignore` for building the `aurite-agents` backend.
*   Test the containerized application locally using both Dockerfiles, `scripts/run-container.sh` (for `Dockerfile.dev`), and the Postman collection `tests/api/main_server.postman_collection.json`.
*   Prepare Kubernetes deployment configurations for the `aurite-agents` backend using the non-dev Docker image.
*   Test deployment to a GKE Autopilot cluster, including a dry-run.
*   Verify the deployed application's basic functionality in GKE.

## 2. Scope
*   **In Scope:**
    *   Review and necessary modifications to `Dockerfile.dev` and `Dockerfile` (non-dev).
    *   Review and necessary modifications to `.dockerignore`.
    *   Review and necessary modifications to `scripts/run-container.sh` (for `Dockerfile.dev` local testing).
    *   Local Docker build and run for both Dockerfiles.
    *   Local API testing using the Postman collection against containers from both Dockerfiles.
    *   Review and adaptation of existing Kubernetes manifest files (from `k8s/` directory, focusing on backend deployment, using the image from `Dockerfile` (non-dev)).
    *   Creation of new Kubernetes manifest files if necessary for the backend.
    *   `kubectl apply --dry-run=client` (or server) for deployment validation.
    *   Actual `kubectl apply` to GKE Autopilot.
    *   Basic health checks and API endpoint testing on the GKE deployment.
*   **Out of Scope (Optional but Recommended):**
    *   Frontend deployment (contents of `frontend/` folder).
    *   Comprehensive performance or stress testing in GKE.
    *   Setting up new GKE clusters or advanced GKE configurations beyond basic deployment.
    *   CI/CD pipeline integration.
    *   Full E2E testing of all agent functionalities in GKE.

## 3. Prerequisites (Optional)
*   GKE Autopilot cluster is accessible and `kubectl` is configured to connect to it.
*   Google Cloud SDK (`gcloud`) is installed and configured.
*   Docker is installed and running locally.
*   Postman CLI (Newman) is installed for automated collection runs (or manual Postman app usage with `tests/api/main_server.postman_environment.json`).
*   The API key (`RwkWJFhApciiUSyH3B/Ad6T46kIxbu9gtAU`) is ready to be configured as a Kubernetes Secret in GKE.

## 4. Implementation Steps

**Phase 1: Dockerfile and Local Container Verification**

1.  **Step 1.1: Review `Dockerfile.dev`**
    *   **File(s):** `Dockerfile.dev`
    *   **Action:**
        *   Ensure Python version (3.12-slim) is appropriate.
        *   Verify build dependencies are necessary and minimal.
        *   Confirm `COPY` instructions correctly include `src/` and `config/`.
        *   Check `pip install -e .[dev]` is still the desired installation method.
        *   Verify runtime dependencies are correct.
        *   Ensure user `appuser` (UID 1000) creation and usage is correct.
        *   Validate `COPY --from=builder` stages.
        *   Check cache directory creation and permissions: `/app/cache`.
        *   Verify environment variables: `PYTHONPATH=/app`, `PYTHONUNBUFFERED=1`, `ENV=development`, `CACHE_DIR=/app/cache`, `PROJECT_CONFIG_PATH=/app/config/projects/testing_config.json`, `LOG_LEVEL=DEBUG`.
        *   **Add `ENV AURITE_ALLOW_DYNAMIC_REGISTRATION=true` to allow Postman dynamic registration tests.**
        *   Confirm `EXPOSE 8000`.
        *   Review `HEALTHCHECK` command. Ensure `/health` is the correct endpoint.
        *   Review `CMD`: `python -m uvicorn src.bin.api:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/src`.
    *   **Verification:** Visual review.

2.  **Step 1.2: Review `Dockerfile` (non-dev)**
    *   **File(s):** `Dockerfile`
    *   **Action:**
        *   Similar review points as `Dockerfile.dev`.
        *   Ensure `ENV=production` (or similar, not `development`).
        *   Ensure `LOG_LEVEL=INFO` (or as appropriate for production-like testing).
        *   **The `CMD` should NOT include `--reload` or `--reload-dir`. Example: `CMD ["python", "-m", "uvicorn", "src.bin.api:app", "--host", "0.0.0.0", "--port", "8000"]`.**
        *   **Add `ENV AURITE_ALLOW_DYNAMIC_REGISTRATION=true` to allow Postman dynamic registration tests (for consistency in this testing phase).**
        *   Ensure `PROJECT_CONFIG_PATH=/app/config/projects/testing_config.json`.
    *   **Verification:** Visual review. Dockerfile is suitable for a more production-like build.

3.  **Step 1.3: Review `.dockerignore`**
    *   **File(s):** `.dockerignore`
    *   **Action:**
        *   Ensure all unnecessary files/directories are ignored.
        *   Verify essential files (`pyproject.toml`, `src/`, `config/`) are NOT ignored.
        *   Remove `!README.md` if not intended for backend images.
    *   **Verification:** Visual review.

4.  **Step 1.4: Review and Update `scripts/run-container.sh`**
    *   **File(s):** `scripts/run-container.sh`
    *   **Action:**
        *   Ensure it targets `Dockerfile.dev` for local development iteration.
        *   Confirm `PROJECT_ROOT`, `.env` loading (for local convenience, not for GKE image).
        *   Check `docker build` and `docker run` commands.
    *   **Verification:** Visual review. Script functions for local `Dockerfile.dev` testing.

5.  **Step 1.5: Build Docker Images Locally**
    *   **Action:**
        *   Build dev image: `docker build -t aurite-agents-dev -f Dockerfile.dev .` (or use `scripts/run-container.sh`).
        *   Build non-dev image: `docker build -t aurite-agents-prodlike -f Dockerfile .`
    *   **Verification:** Both Docker images build successfully.

6.  **Step 1.6: Run Containers Locally & Test with Postman**
    *   **Action:**
        *   For `aurite-agents-dev`: Run using `scripts/run-container.sh` or manually: `docker run --rm -it -p 8000:8000 --env-file .env aurite-agents-dev`.
        *   For `aurite-agents-prodlike`: Run manually: `docker run --rm -it -p 8001:8000 --env-file .env aurite-agents-prodlike` (use a different host port like 8001 to avoid conflict if testing simultaneously, or test sequentially).
        *   For each running container:
            *   Update Postman `base_url` variable (e.g., `http://localhost:8000` or `http://localhost:8001`).
            *   Use `tests/api/main_server.postman_environment.json` for `api_key`.
            *   Run Postman collection: `newman run tests/api/main_server.postman_collection.json -e tests/api/main_server.postman_environment.json`.
    *   **Verification:** Both containers start. Application logs indicate normal operation. All Postman tests pass against both containers.

**Phase 2: Kubernetes Configuration and GKE Dry-Run (using `aurite-agents-prodlike` image)**

1.  **Step 2.1: Review Existing Kubernetes Manifests for Backend**
    *   **File(s):** `k8s/config/app/deployment.yaml`, `k8s/config/app/service.yaml`, `k8s/config/app/app-config.yaml` (and any other relevant backend configs).
    *   **Action:**
        *   Adapt `deployment.yaml`:
            *   Update `spec.template.spec.containers[0].image` to point to the `aurite-agents-prodlike` image in the registry (e.g., `gcr.io/YOUR_PROJECT/aurite-agents:prodlike-latest`).
            *   Verify container `port` is 8000.
            *   Environment variables:
                *   `PROJECT_CONFIG_PATH` should be `/app/config/projects/testing_config.json` (mounted from ConfigMap).
                *   `AURITE_API_KEY` should be sourced from a Kubernetes Secret.
                *   `AURITE_ALLOW_DYNAMIC_REGISTRATION=true` (for this test deployment).
                *   Other necessary env vars (e.g., `ENV=production`, `LOG_LEVEL=INFO`).
            *   Review resource requests/limits.
            *   Check readiness/liveness probes (path `/health`, port 8000).
        *   Adapt `service.yaml`: Target port 8000.
        *   Create/Adapt `ConfigMap` for `testing_config.json`:
            *   Name: e.g., `aurite-agent-config`
            *   Data: Key `testing_config.json`, value is the content of `config/projects/testing_config.json`.
            *   Mount this ConfigMap into the pod at `/app/config/projects/testing_config.json`.
        *   Prepare `Secret` for `AURITE_API_KEY`:
            *   Name: e.g., `aurite-agent-secrets`
            *   Data: Key `AURITE_API_KEY`, value `RwkWJFhApciiUSyH3B/Ad6T46kIxbu9gtAU`.
    *   **Verification:** Manifests are updated for the `aurite-agents-prodlike` image and GKE environment.

2.  **Step 2.2: Push `aurite-agents-prodlike` Image to Registry**
    *   **Action:**
        *   Tag: `docker tag aurite-agents-prodlike gcr.io/YOUR_PROJECT/aurite-agents:prodlike-latest` (replace with your actual registry path).
        *   Push: `docker push gcr.io/YOUR_PROJECT/aurite-agents:prodlike-latest`.
    *   **Verification:** Image pushed successfully.

3.  **Step 2.3: Kubernetes Deployment Dry-Run**
    *   **Action:**
        *   Ensure namespace, RBAC, network policies are applied in GKE.
        *   Create the `ConfigMap` (for `testing_config.json`) and `Secret` (for `AURITE_API_KEY`) in GKE.
        *   Dry-run deployment: `kubectl apply -f k8s/config/app/deployment.yaml --dry-run=client`.
        *   Dry-run service: `kubectl apply -f k8s/config/app/service.yaml --dry-run=client`.
    *   **Verification:** Dry-run commands execute without errors.

**Phase 3: GKE Deployment and Verification**

1.  **Step 3.1: Deploy to GKE**
    *   **Action:**
        *   Apply ConfigMap and Secret (if not done in dry-run prep).
        *   Apply Deployment: `kubectl apply -f k8s/config/app/deployment.yaml`.
        *   Apply Service: `kubectl apply -f k8s/config/app/service.yaml`.
    *   **Verification:** `kubectl apply` commands succeed. Pods created and `Running`. Logs healthy.

2.  **Step 3.2: Verify Deployment in GKE**
    *   **Action:**
        *   `kubectl get pods -n your-namespace`, `kubectl get svc -n your-namespace`.
        *   `kubectl logs -n your-namespace <your-app-pod-name>`.
        *   Port-forward: `kubectl port-forward svc/<your-service-name> 8080:8000 -n your-namespace`.
    *   **Verification:** Pods running, logs healthy, service accessible via port-forward.

3.  **Step 3.3: Basic API Testing on GKE Deployment**
    *   **Action:**
        *   Update Postman `base_url` to `http://localhost:8080` (with port-forward).
        *   Use `tests/api/main_server.postman_environment.json` for `api_key`.
        *   Run health check and key API endpoints from Postman collection.
    *   **Verification:** Basic API tests pass.

## 5. Testing Strategy
*   **Local Docker:** Build success for both Dockerfiles. Container run success. Postman collection pass against both.
*   **Kubernetes Dry-Run:** `kubectl apply --dry-run` success for backend manifests.
*   **GKE Deployment:** Pods running, logs healthy, service accessible.
*   **GKE API Tests:** Key Postman requests pass.

## 6. Potential Risks & Mitigation (Optional)
*   **Risk:** Dockerfile issues.
    *   **Mitigation:** Thorough review and iterative local fixing.
*   **Risk:** Config discrepancies (local `.env` vs. K8s ConfigMap/Secret).
    *   **Mitigation:** Careful K8s manifest creation and `testing_config.json` review.
*   **Risk:** K8s RBAC/Network Policy issues.
    *   **Mitigation:** Review `k8s/README.md`, check GKE logs, `kubectl describe pod`.
*   **Risk:** Postman test failures due to GKE environment specifics.
    *   **Mitigation:** Correct Postman environment for GKE testing (port-forward URL).

## 7. Open Questions & Discussion Points (Optional)
*   (Addressed for now, can add more later if they arise)
