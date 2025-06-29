# Dependency Audit Guide (`deptry`)

This document provides a guide to understanding the output of the `deptry .` command after the dependency refactoring. While the command still reports issues, they are now understood and considered safe within our project's structure.

## 1. Overview of `deptry` Warnings

After refactoring `pyproject.toml` to use optional dependency groups, `deptry` still flags several types of issues. This is expected. Here is a breakdown of what each warning means and why it is not a critical problem for us.

### `DEP001`: Missing Dependency (e.g., `mem0`)

-   **Warning:** `src/aurite/components/servers/memory/mem0_server.py:4:1: DEP001 'mem0' imported but missing from the dependency definitions`
-   **Explanation:** This warning occurs because the `mem0` library (from the `mem0ai` package) is intentionally not in the core `[project.dependencies]` list. It resides in the `[project.optional-dependencies.tools]` group.
-   **Why it's safe:** `deptry`, by default, only scans for core dependencies. This code is only meant to be run if a user explicitly installs the optional "tools" dependencies (`pip install aurite[tools]`). This warning confirms that we have correctly isolated the dependency.

### `DEP002`: Unused Dependency (e.g., `pytest`, `numpy`, `PyMySQL`)

-   **Warning:** `pyproject.toml: DEP002 'pytest' defined as a dependency but not used in the codebase`
-   **Explanation:** This warning flags packages listed in `pyproject.toml` that are not imported within the main `src/aurite/` source directory.
-   **Why it's safe:** This is the entire point of optional dependencies.
    -   `pytest`, `mypy`, and `deptry` are in the `[dev]` group and are only used for testing and analysis, not in the framework's runtime code.
    -   `numpy` and `pandas` are in the `[ml]` group for optional machine learning features.
    -   `PyMySQL` is in the `[mysql]` group and is only used if the user wants to connect to a MySQL database.
    -   This warning confirms that these packages are correctly isolated from the core codebase.

### `DEP003`: Transitive Dependency Import (e.g., `httpx`, `anyio`, `IPython`)

-   **Warning:** `src/aurite/host/foundation/clients.py:18:8: DEP003 'httpx' imported but it is a transitive dependency`
-   **Explanation:** This is the most common remaining warning. It means that our code imports a package (like `httpx`) that we did not explicitly list in our core dependencies.
-   **Why it's safe (and a good sign!):** This confirms our refactoring was successful. We are correctly relying on our direct dependencies (`fastapi`, `mcp`, `jupyter`, etc.) to manage their own sub-dependencies. `fastapi`, for example, requires `httpx`. By not specifying `httpx` ourselves, we avoid version conflicts and let `fastapi` manage its own requirements. This makes our package much more robust. The warnings for `IPython` are similar; it's a dependency of `jupyter`.

## 2. Achieving a "Clean" `deptry` Report

While these warnings are safe, a clean "zero-issue" report is always preferable for continuous integration (CI) pipelines. We can configure `deptry` to ignore these known and accepted issues by adding an exclusion list to `pyproject.toml`.

I will add this configuration for you in the next step. This will tell `deptry` to ignore these specific warnings, resulting in a clean bill of health and ensuring that only *new, unexpected* dependency issues get flagged in the future.
