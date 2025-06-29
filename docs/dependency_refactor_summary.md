# Dependency & Configuration Refactor Summary

This document summarizes the series of improvements made to the project's dependency management (`pyproject.toml`) and startup configuration (`src/aurite/bin/api/api.py`).

## 1. The Initial Problem: Unreliable `pip` Installation

The core motivation for this work was user reports of `pip install` failing. This was caused by a `pyproject.toml` file that contained a long list of both direct and transitive dependencies, creating a complex puzzle for `pip` to solve.

---

## 2. Dependency Issues & Resolutions

We used the `deptry` tool to systematically identify and fix several classes of dependency issues.

### Issue 1: Transitive Dependencies Listed as Direct Dependencies

*   **Problem:** The `dependencies` list in `pyproject.toml` included packages like `httpx`, `anyio`, `pydantic_core`, `click`, and `starlette`. These are not direct dependencies of our `aurite` code; they are dependencies *of our dependencies* (e.g., `fastapi` depends on `httpx` and `starlette`). Listing them explicitly creates a high risk of version conflicts and makes dependency resolution fragile.
*   **Solution:** We removed all transitive dependencies from the main list. We now only list our direct requirements (like `fastapi`, `mcp`, `sqlalchemy`) and trust `pip` to resolve their sub-dependencies correctly. This is the single most important change for installation reliability.

### Issue 2: Missing Core Dependencies

*   **Problem:** During the refactor, we discovered that `termcolor` and `pytz` were being used by core, packaged code (like the logger and the example weather server) but were not listed as direct dependencies. This caused runtime `ImportError` exceptions.
*   **Solution:** We added `termcolor` and `pytz` back to the main `[project.dependencies]` list, ensuring they are always installed.

### Issue 3: Mis-categorized Optional Dependencies

*   **Problem:** We initially treated all optional features (like database drivers and ML tools) as "development" dependencies. `deptry` correctly flagged this as a `DEP004` (Misplaced Development Dependency) error, because code in `src/` was importing packages that were only supposed to be for development.
*   **Solution:** We refined the `deptry` configuration. We now use `pep621_dev_dependency_groups = ["dev"]` to specify that *only* the `[dev]` group is for development. All other groups (`ml`, `postgres`, `gcp`, etc.) are correctly treated as optional *production* dependencies.

### Issue 4: Incorrect `deptry` Configuration

*   **Problem:** We encountered several issues while configuring `deptry` itself:
    1.  It wasn't ignoring the `.venv` directory because we used `exclude` instead of `extend_exclude`.
    2.  It was flagging our own package, `aurite`, as a transitive dependency.
    3.  It couldn't map the package name `psycopg2-binary` to the imported module name `psycopg2`.
*   **Solution:** We made the following corrections to `[tool.deptry]` in `pyproject.toml`:
    1.  Switched to `extend_exclude = ["tests", "docs"]` to ensure `.gitignore` is respected.
    2.  Added `known_first_party = ["aurite"]` to tell `deptry` what our main package is.
    3.  Added a `[tool.deptry.package_module_name_map]` to map `"psycopg2-binary" = "psycopg2"`.

---

## Final Outcome

The project now has a clean, robust, and modern dependency configuration that will be significantly more reliable for users and easier for the team to maintain. The `deptry` audit now passes cleanly, providing a strong guardrail against future dependency issues.
