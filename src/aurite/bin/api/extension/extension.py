"""
Base Extension class for Aurite API extensions.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


class Extension(ABC):
    """
    Base class for Aurite API extensions.

    Extensions allow users to add custom endpoints to the Aurite API
    that can interact with the Aurite instance, ConfigManager, MCPHost,
    and other framework components.

    Example:
        ```python
        from fastapi import APIRouter
        from aurite.bin.api.extension import Extension, application

        class MyExtension(Extension):
            '''Custom extension with RAG endpoint.'''

            def __call__(self, app):
                router = APIRouter(prefix="/custom", tags=["Custom"])

                @router.get("/hello")
                def hello():
                    # Access Aurite instance
                    aurite = application.get()
                    return {"message": "Hello from custom endpoint"}

                app.include_router(router)
        ```
    """

    @abstractmethod
    def __call__(self, app: "FastAPI") -> None:
        """
        Register routes and configure the extension.

        Args:
            app: The FastAPI application instance
        """
        pass


__all__ = ["Extension"]
