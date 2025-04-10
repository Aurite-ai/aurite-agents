# Packaging Implementation Plan

**Date:** 2025-04-10
**Status:** Proposed
**Related Plan:** `docs/plans/production_readiness_plan.md`

## 1. Goal

Configure the `aurite-agents` project to be buildable and installable as a standard Python package using `pip`.

## 2. Background

Currently, the project is run directly from the source or installed in editable mode (`pip install -e .`). To make the framework portable for use in other projects or for deployment, it needs to be packaged correctly. This involves configuring `pyproject.toml` according to PEP 621 and related standards.

## 3. Implementation Steps

1.  **Review & Update `pyproject.toml` (`[project]` section):**
    *   Verify/add essential metadata:
        *   `name = "aurite-agents"` (Exists)
        *   `version = "0.2.0"` (Exists - consider bumping if significant changes were made)
        *   `description = "..."` (Exists)
        *   `readme = "README.md"` (Exists)
        *   `requires-python = ">=3.12"` (Exists)
        *   `license = { text = "Specify License (e.g., MIT, Apache-2.0) or file = 'LICENSE' }" }` (Add appropriate license)
        *   `authors = [ { name = "Your Name/Company", email = "your@email.com" } ]` (Add author info)
        *   `keywords = ["ai", "agent", "mcp", "framework"]` (Add relevant keywords)
        *   `classifiers = [ ... ]` (Add relevant PyPI classifiers, e.g., `Programming Language :: Python :: 3.12`, `License :: OSI Approved :: ...`, `Topic :: Scientific/Engineering :: Artificial Intelligence`)
    *   Verify `dependencies`: Ensure all runtime dependencies are listed (already includes `google-cloud-secret-manager`).
    *   Verify `[project.optional-dependencies]`: Ensure `dev` dependencies like `pytest-timeout` are correct.

2.  **Configure Package Discovery (`[tool.setuptools.packages.find]`):**
    *   Verify the current settings are correct for finding the `src` package:
      ```toml
      [tool.setuptools.packages.find]
      where = ["."]
      include = ["src*"]
      namespaces = false
      ```
    *   (This looks correct as it should find the `src` directory containing the main code).

3.  **Configure Script Entry Points (`[project.scripts]`):**
    *   Review existing scripts: `start-api`, `start-worker`, `run-cli`.
    *   Ensure they point to the correct function/object within the modules in `src/bin/`.
        *   `start-api = "src.bin.api:start"` (Looks correct)
        *   `start-worker = "src.bin.worker:main"` (Verify `main` is the intended entry point function in `worker.py`)
        *   `run-cli = "src.bin.cli:app"` (Looks correct for Typer)
    *   These allow running the commands directly after `pip install`.

4.  **Build the Package:**
    *   Ensure `build` package is installed (`pip install build`).
    *   Run the build command from the project root:
        ```bash
        python -m build
        ```
    *   Verify that `sdist` (`.tar.gz`) and `wheel` (`.whl`) files are created in the `dist/` directory.

5.  **Test Local Installation:**
    *   Create a *new, separate* temporary directory and virtual environment outside the project directory.
    *   Activate the new virtual environment.
    *   Install the built wheel file from the project's `dist/` directory:
        ```bash
        pip install /path/to/aurite-agents/dist/aurite_agents-*.whl
        ```
    *   Test basic import: `python -c "from src.host import MCPHost; print('Import OK')"`
    *   Test running scripts (if entry points were configured): `start-api --help` (this might fail if it requires env vars/config not present, but should show help).

6.  **Documentation:**
    *   Update `README.md` or `usage_guide.md` installation instructions to include installing the built package (`pip install .` or `pip install dist/...whl`) as an alternative to editable install.
    *   Briefly mention the available command-line scripts if entry points were added.

## 4. Considerations

*   **Versioning:** Decide on a versioning scheme (e.g., SemVer). Bump the version in `pyproject.toml` if necessary.
*   **License:** Choose and specify an appropriate license. If intended for internal use only, state that clearly or use a custom license file.
*   **Distribution:** While this plan focuses on local build/install, the next step would be publishing to a package index (Private PyPI, Gemfury, GitHub Packages, etc.) if needed for wider internal distribution.

## 5. Next Steps

*   Review and approve this plan.
*   Proceed with implementation step-by-step, starting with updating `pyproject.toml`.
