# Implementation Plan: Poetry Migration

**Version:** 1.0
**Date:** 2025-06-30
**Author(s):** Ryan, Gemini

## 1. Goals
*   Migrate the project's build system from `setuptools` to `Poetry`.
*   Use Poetry to manage dependency versioning.
*   Simplify the package publishing process.

## 2. Scope
*   **In Scope:**
    *   Modifying `pyproject.toml` to be compatible with Poetry.
    *   Translating `MANIFEST.in` rules to `pyproject.toml`.
    *   Generating a `poetry.lock` file.
    *   Deleting the `MANIFEST.in` file.
*   **Out of Scope:**
    *   Changing any application logic.
    *   Modifying dependency versions until after the initial migration is complete.

## 3. Implementation Steps

1.  **Step 1: Modify `pyproject.toml`**
    *   **File(s):** `pyproject.toml`
    *   **Action:**
        *   Replace the `[build-system]` section to use `poetry.core.masonry.api`.
        *   Create a `[tool.poetry]` section and move project metadata (name, version, description, authors, readme, license, keywords, classifiers, urls) into it.
        *   Define the package structure using `tool.poetry.packages = [{ include = "aurite", from = "src" }]`.
        *   Replicate `MANIFEST.in` functionality by adding `tool.poetry.include` to bring in the `src/aurite/packaged` directory and other necessary files.
        *   Move `[project.dependencies]` to `[tool.poetry.dependencies]`.
        *   Move `[project.optional-dependencies]` to `[tool.poetry.group.<name>.dependencies]`.
        *   Move `[project.scripts]` to `[tool.poetry.scripts]`.
        *   Remove the `[tool.setuptools]` section entirely.
    *   **Verification:** The `pyproject.toml` file is syntactically correct and reflects the Poetry configuration structure.

2.  **Step 2: Lock Dependencies**
    *   **Action:** Run the command `poetry lock --no-update`.
    *   **Verification:** A `poetry.lock` file is created in the project root, containing a resolved list of all project dependencies and their exact versions.

3.  **Step 3: Install Dependencies**
    *   **Action:** Run the command `poetry install --all-extras`.
    *   **Verification:** A Poetry-managed virtual environment is created, and all dependencies (including optional groups) are installed successfully.

4.  **Step 4: Clean Up `MANIFEST.in`**
    *   **Action:** Delete the `MANIFEST.in` file.
    *   **Verification:** The `MANIFEST.in` file is no longer present in the project root.

5.  **Step 5: Final Documentation**
    *   **Action:** Explain the commands for future use: `poetry add`, `poetry update`, and `poetry publish --build`.
    *   **Verification:** The user understands how to manage dependencies and publish the package using Poetry.
