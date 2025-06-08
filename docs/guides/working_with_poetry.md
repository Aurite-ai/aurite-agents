# How to Work with Poetry

This guide explains what Poetry is, how it differs from a `setuptools`-based project, and how you would configure your `pyproject.toml` to use it.

## 1. What is Poetry?

Poetry is a tool for Python dependency management and packaging. It simplifies project setup by managing a dedicated virtual environment for your project, resolving complex dependency graphs, and providing a streamlined workflow for building and publishing your package.

Its primary goals are:
*   **Integrated Tooling:** One tool to manage dependencies, build, and publish.
*   **Deterministic Builds:** It uses a `poetry.lock` file to ensure that you get the same versions of dependencies every time you install your project.
*   **Simplified `pyproject.toml`:** It centralizes all project metadata, dependencies, and tool configuration in the `pyproject.toml` file under its own `[tool.poetry]` section.

## 2. `setuptools` vs. Poetry: A Comparison

Your current `pyproject.toml` uses `setuptools`. Let's see how it compares to a Poetry configuration.

### Your Current `setuptools` Configuration

Your project metadata and dependencies are defined under the standard `[project]` table, and the build system is explicitly set to `setuptools`.

```toml
# pyproject.toml (Current setuptools setup)

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "aurite"
version = "0.3.6"
dependencies = [
    "mcp>=1.8.1",
    "httpx>=0.28.1",
    # ... and so on
]

[project.optional-dependencies]
dev = [
    "pytest-timeout>=2.3.1",
    # ...
]

[project.scripts]
aurite = "aurite.bin.cli.main:app"

[tool.setuptools]
include-package-data = true
package-dir = {"" = "src"}
```

### Equivalent Poetry Configuration

If you were to use Poetry, the configuration would be consolidated under the `[tool.poetry]` section. The `[project]` table would be removed.

```toml
# pyproject.toml (Equivalent Poetry setup)

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "aurite"
version = "0.3.6"
description = "Aurite Agent Development and Runtime Framework"
authors = ["Ryan W <ryan@aurite.ai>", "Blake R <blake@aurite.ai>", "Patrick W <patrick@aurite.ai>"]
readme = "README.md"
license = "Proprietary" # Assumed, specify your license
homepage = "https://github.com/Aurite-ai/aurite-agents"
repository = "https://github.com/Aurite-ai/aurite-agents"
keywords = ["ai", "agent", "mcp", "framework", "llm", "anthropic"]
packages = [{include = "aurite", from = "src"}]

[tool.poetry.dependencies]
python = ">=3.11"
mcp = ">=1.8.1"
httpx = ">=0.28.1"
# ... all other dependencies from [project.dependencies] go here

[tool.poetry.group.dev.dependencies]
pytest-timeout = ">=2.3.1"
# ... all other dependencies from [project.optional-dependencies].dev go here

[tool.poetry.extras]
ml = ["pandas>=2.2.3", "numpy>=1.26.2,<2.1"]

[tool.poetry.scripts]
aurite = "aurite.bin.cli.main:app"

# Note: The [tool.setuptools] section would be removed entirely.
# The [tool.pytest.ini_options] and [tool.mypy] sections would remain unchanged.
```

**Key Differences:**
*   **`[build-system]`:** Now points to `poetry.core.masonry.api`.
*   **`[tool.poetry]`:** This new section holds all the metadata that was previously in `[project]`.
*   **`[tool.poetry.dependencies]`:** This is where your main project dependencies live.
*   **`[tool.poetry.group.dev.dependencies]`:** This is how Poetry manages development-only dependencies. You can install them with `poetry install --with dev`.
*   **`[tool.poetry.extras]`:** This defines optional dependencies that can be installed with the package (e.g., `pip install aurite[ml]`).
*   **`packages`:** The `packages` key tells Poetry where to find the source code (in the `src` directory).

## 3. Common Poetry Workflow

If you were using Poetry, your workflow would revolve around these commands:

1.  **`poetry install`**:
    *   Reads `pyproject.toml`.
    *   Creates a virtual environment for the project if one doesn't exist.
    *   Installs all required dependencies.
    *   Creates a `poetry.lock` file to lock the exact versions of all packages.

2.  **`poetry add <package-name>`**:
    *   Adds a new dependency to `[tool.poetry.dependencies]` in `pyproject.toml`.
    *   Installs the package and updates `poetry.lock`.
    *   To add a dev dependency: `poetry add <package-name> --group dev`.

3.  **`poetry run <command>`**:
    *   Runs a command inside the Poetry-managed virtual environment. For example: `poetry run pytest`.

4.  **`poetry build`**:
    *   Builds the source archive and wheel, placing them in the `dist/` directory.

5.  **`poetry publish`**:
    *   Publishes your package to a repository like PyPI. It can be configured to point to TestPyPI as well.
    *   Example: `poetry publish --repository testpypi`.

Migrating from `setuptools` to Poetry is a significant change, but many developers find its integrated workflow and dependency management capabilities to be very powerful.
