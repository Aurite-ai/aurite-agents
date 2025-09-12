"""
Custom exception types for the Aurite framework.

This module defines a hierarchy of custom exceptions to allow for more
specific and predictable error handling across the application.
"""


class AuriteError(Exception):
    """Base exception for all custom errors in the Aurite framework."""

    pass


class ConfigurationError(AuriteError):
    """
    Raised for errors related to loading, parsing, or validating
    component configurations.
    """

    pass


class MCPHostError(AuriteError):
    """
    Raised for errors related to the MCP Host, such as server
    registration failures or communication issues.
    """

    pass


class AgentExecutionError(AuriteError):
    """
    Raised for errors that occur during the execution of an agent's
    conversation loop.
    """

    pass


class WorkflowExecutionError(AuriteError):
    """
    Raised for errors that occur during the execution of a linear or
    custom workflow.
    """

    pass


class MCPServerTimeoutError(MCPHostError):
    """
    Raised when MCP server registration or operation times out.

    Provides structured information about the timeout for better
    error handling in frontend applications.
    """

    def __init__(self, server_name: str, timeout_seconds: float, operation: str = "registration"):
        self.server_name = server_name
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        super().__init__(f"MCP server '{server_name}' {operation} timed out after {timeout_seconds} seconds")


class MaxIterationsReachedError(AuriteError):
    """
    Raised when the max turn limit is reached during agent execution.
    """

    pass


class DuplicateClientIdError(ValueError):
    """Custom exception for duplicate client ID registration attempts."""

    pass


class MCPServerFileNotFoundError(ConfigurationError):
    """
    Raised when an MCP server configuration references a server_path that doesn't exist.

    Provides structured information about the missing file for better
    error handling in frontend applications.
    """

    def __init__(self, server_name: str, server_path: str, context_path: str | None = None):
        self.server_name = server_name
        self.server_path = server_path
        self.context_path = context_path

        if context_path:
            message = (
                f"MCP server '{server_name}' references a non-existent file: {server_path}\n"
                f"Expected location (relative to {context_path}): {server_path}"
            )
        else:
            message = f"MCP server '{server_name}' references a non-existent file: {server_path}"

        super().__init__(message)
