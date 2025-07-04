# Implementation Plan: Host Manager Refactor

**Version:** 1.0
**Date:** 2025-07-04
**Author(s):** Ryan, Gemini
**Related Design Document (Optional):** N/A

## 1. Goals
*   Refactor the `Aurite` class in `src/aurite/host_manager.py` to improve performance by avoiding repeated initialization and shutdown of its core components.
*   Implement a lazy-initialization pattern so that the core engine is started only on the first use.
*   Eliminate boilerplate pass-through methods on the `Aurite` class using a dynamic proxy pattern (`__getattr__`).
*   Improve code clarity by renaming `_AuriteCore` to `AuriteKernel` to better reflect its role.
*   Retain the robust, guaranteed shutdown behavior provided by the existing wrapper pattern.

## 2. Scope
*   **In Scope:**
    *   `src/aurite/host_manager.py`: This is the only file that will be modified.
*   **Out of Scope:**
    *   No other files will be changed. The public API of the `Aurite` class will remain functionally identical, ensuring no breaking changes for end-users.

## 3. Implementation Steps

### Step 1: Rename `_AuriteCore` to `AuriteKernel`
*   **File(s):** `src/aurite/host_manager.py`
*   **Action:**
    *   Perform a find-and-replace within the file.
    *   Change the class name from `_AuriteCore` to `AuriteKernel`.
    *   Update all internal references to the class, primarily within the `Aurite` class constructor (`self._core = _AuriteCore()` -> `self.kernel = AuriteKernel()`).
    *   Update docstrings and log messages to reflect the new name.
*   **Verification:**
    *   The file should be internally consistent with the new `AuriteKernel` name.

### Step 2: Implement Lazy Initialization in `Aurite`
*   **File(s):** `src/aurite/host_manager.py`
*   **Action:**
    *   In the `Aurite` class `__init__` method, add a new instance attribute: `self._initialized = False`.
    *   Create a new private async method `_ensure_initialized` within the `Aurite` class.
        ```python
        async def _ensure_initialized(self):
            """Initializes the kernel on the first call."""
            if not self._initialized:
                await self.kernel.initialize()
                self._initialized = True
        ```
*   **Verification:**
    *   The new method and attribute are correctly defined within the `Aurite` class.

### Step 3: Replace Pass-Through Methods with `__getattr__`
*   **File(s):** `src/aurite/host_manager.py`
*   **Action:**
    *   Delete the existing `run_agent`, `run_simple_workflow`, and `run_custom_workflow` methods from the `Aurite` class.
    *   Implement the `__getattr__` method in the `Aurite` class to dynamically proxy calls to the `AuriteKernel`.
        ```python
        def __getattr__(self, name: str) -> Any:
            """
            Dynamically proxies method calls to the underlying AuriteKernel,
            wrapping them with the initialization logic.
            """
            attr = getattr(self.kernel, name)
            if callable(attr):
                async def wrapper(*args, **kwargs):
                    await self._ensure_initialized()
                    return await attr(*args, **kwargs)
                return wrapper
            else:
                return attr
        ```
*   **Verification:**
    *   The old `run_*` methods are removed.
    *   The `__getattr__` method is implemented as specified.

### Step 4: Update Remaining Methods and Finalize
*   **File(s):** `src/aurite/host_manager.py`
*   **Action:**
    *   Update the `__del__` method to reference `self.kernel` instead of `self._core`.
    *   Update the `__aenter__` and `__aexit__` methods to reference `self.kernel`.
    *   Modify the `unregister_server` method to use the new lazy initialization: `await self._ensure_initialized()`.
    *   Ensure the `get_config_manager` method correctly references `self.kernel.get_config_manager()`.
*   **Verification:**
    *   All references to the old `_core` attribute are updated to `kernel`.
    *   The `unregister_server` method correctly calls `_ensure_initialized`.

## 4. Testing Strategy
*   **Manual Verification:**
    *   After the refactoring is complete, the `scripts/temp_agent_runner.py` script will be used for verification.
    *   **Expected Behavior:** The script should run successfully, producing the same output as before. Crucially, logs should show the `AuriteKernel` initializing only *once* when `run_agent` is first called, not on every call. The shutdown message should appear at the very end when the script finishes.
