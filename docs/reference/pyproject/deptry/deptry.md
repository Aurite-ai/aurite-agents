# Deptry: Dependency Linting for a Healthy Project

This document provides an overview of `deptry`, our dependency linting tool. It explains what `deptry` is, how it's configured in our project, and the role it plays in maintaining a clean and reliable `pyproject.toml`.

## A. What is Deptry?

`deptry` is a command-line tool that scans our project for dependency-related issues. Its primary job is to ensure that the dependencies listed in `pyproject.toml` are perfectly aligned with the packages actually imported and used in our Python source code.

It acts as a **linter for our dependencies**, helping us catch common problems that can lead to installation failures, bloated environments, and runtime errors.

## B. Our Deptry Configuration: The Gold Standard

`deptry` is configured in the `[tool.deptry]` section of our `pyproject.toml` and is automatically run as part of our pre-commit hooks. Through careful configuration and dependency management, we have achieved the ideal state: **our project passes `deptry` with zero `per_rule_ignores`**.

This means our `pyproject.toml` is a perfectly accurate and verifiable representation of our project's dependencies. Here’s how we achieved this and what the key settings do.

### Core Configuration Settings

Our clean run is made possible by four key settings that work in harmony:

1.  **`known_first_party = ["aurite"]`**
    *   **Purpose:** This tells `deptry` that `aurite` is our own local package. It prevents `deptry` from flagging our internal imports (e.g., `from aurite.host import ...`) as missing third-party dependencies.

2.  **`extend_exclude = ["tests", "docs"]`**
    *   **Purpose:** This instructs `deptry` to only scan our application's source code (`src/aurite`). By excluding the `tests` directory, we prevent `deptry` from checking our test files, which correctly import development-only dependencies like `pytest`. This eliminates false "misplaced dependency" errors.

3.  **`package_module_name_map`**
    *   **Purpose:** This is the key that unlocked our ability to remove all ignore rules. It creates an explicit map between the name of a package we install (e.g., `google-cloud-secret-manager`) and the different name of the module we import in the code (e.g., `google`). Without this map, `deptry` would see an unused package and a missing import, forcing us to use ignore rules.

### Understanding the Violations We Now Prevent

Our configuration automatically prevents the common dependency issues that `deptry` checks for:

*   **`DEP001: Missing dependency`**: If we `import` a package but forget to add it to `pyproject.toml`, `deptry` will fail the pre-commit hook, forcing us to add it.
*   **`DEP002: Unused dependency`**: If we remove a feature and forget to remove its dependency from `pyproject.toml`, `deptry` will flag it as unused, helping us keep the project lean.
*   **`DEP003: Transitive dependency`**: If we start importing a sub-dependency (e.g., a dependency of `fastapi`), `deptry` will raise an error, forcing us to make that dependency an explicit, direct dependency of our own project. This prevents future breakages.
*   **`DEP004: Misplaced development dependency`**: `deptry` will immediately catch any attempt to import a dev-only tool (like `alembic` or `pytest`) into our main application code.

## C. Deptry's Role in Our Workflow (vs. Poetry)

It's important to understand the distinct and complementary roles of `deptry` and `Poetry` in our project.

*   **Poetry is the Project and Dependency Manager.**
    *   **Responsibilities:**
        *   Managing the official list of project dependencies.
        *   Resolving, installing, and locking dependency versions (`poetry.lock`).
        *   Building and publishing the `aurite` package to PyPI.
        *   Providing an isolated virtual environment for development.

*   **Deptry is the Dependency Linter/Auditor.**
    *   **Responsibilities:**
        *   Ensuring no packages are imported that aren't listed in `pyproject.toml` (no missing dependencies).
        *   Ensuring no packages are listed in `pyproject.toml` that aren't actually used (no unused dependencies).
        *   Ensuring we don't import sub-dependencies directly (no transitive dependencies).

In short: **Poetry *manages* the dependencies, and Deptry *audits* them** to make sure the list managed by Poetry is a correct and minimal reflection of what our code actually needs.
