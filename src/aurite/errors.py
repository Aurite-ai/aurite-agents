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
    Raised for errors that occur during the execution of a simple or
    custom workflow.
    """

    pass
