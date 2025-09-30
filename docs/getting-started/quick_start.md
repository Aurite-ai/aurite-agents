# :material-flash: Quick Start

Get up and running with Aurite in just a few minutes!

---

## 1. Install Aurite

- Set up Python 3.12+ and a virtual environment.
- Install the `aurite` package:
  ```bash
  pip install aurite
  ```

<!-- prettier-ignore -->
!!! tip "Need more details?"
    See the [Package Installation Guide](./installation_guides/package_installation_guide.md) for step-by-step instructions.

---

## 2. Initialize Your Workspace & Project

Run the interactive wizard from your chosen directory:

```bash
aurite init
```

This creates your workspace, first project, and example configurations.

<!-- prettier-ignore -->
!!! info "Learn More"
    For details on projects and workspaces, see [Projects and Workspaces](../usage/config/projects_and_workspaces.md).

---

## 3. Run a Built-In Agent

Try out the Weather Agent with a single command:

```bash
aurite run "Weather Agent" "Weather in London?"
```

<!-- prettier-ignore -->
??? example "Example Output"
    ```
      The weather in London is currently 15°C, rainy, with 90% humidity.
    ```

</details>

---

## Next Steps

- Explore more CLI commands in the [CLI Reference](../usage/cli_reference.md).
- Edit configurations with:
  ```bash
  aurite edit
  ```
- Start the API server:
  ```bash
  aurite api
  ```

<!-- prettier-ignore -->
!!! tip "Ready to build?"
    You're set to start building with Aurite. Dive into configuration and workflow customization to unlock advanced features!
