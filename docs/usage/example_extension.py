"""
Example API Extension for Aurite Framework

This example shows how to create a custom API extension that adds
new endpoints to the Aurite API server.

To use this extension:
1. Save this file in a location importable by Python
2. Set the environment variable:
   export AURITE_API_EXTENSIONS="docs.usage.example_extension.CustomRAGExtension"
3. Start the API: aurite api start
4. Access the new endpoint at http://localhost:8000/custom/rag
"""

from fastapi import APIRouter, Depends, Query, Security
from typing import Dict, Any

# Import from extension submodule to avoid circular imports
from aurite.bin.api.extension import Extension, application
from aurite.bin.dependencies import (
    get_api_key,
    get_config_manager,
    get_execution_facade,
)


class CustomRAGExtension(Extension):
    """
    Example extension that adds a custom RAG (Retrieval Augmented Generation) endpoint.

    This extension demonstrates:
    - Creating custom endpoints
    - Accessing the Aurite instance
    - Using Aurite's dependency injection
    - Executing agents programmatically
    """

    def __call__(self, app):
        """Register the custom router with the FastAPI app."""
        router = APIRouter(prefix="/custom", tags=["Custom Endpoints"])

        @router.get("/rag")
        async def rag_endpoint(
            question: str = Query(..., description="Question to answer using RAG"),
            agent_name: str = Query("rag_agent", description="Name of the agent to use"),
            api_key: str = Security(get_api_key),
            config_manager=Depends(get_config_manager),
            engine=Depends(get_execution_facade),
        ) -> Dict[str, Any]:
            """
            Run a RAG query using an Aurite agent.

            This endpoint:
            1. Takes a question as input
            2. Executes a configured RAG agent
            3. Returns the agent's response
            """
            # You can also access the Aurite instance directly
            aurite = application.get()

            # Execute the agent
            result = await engine.run_agent(
                agent_name=agent_name, user_message=question
            )

            return {
                "question": question,
                "agent_used": agent_name,
                "status": result.status,
                "answer": result.final_output,
                "session_id": result.session_id,
            }

        @router.get("/hello")
        @router.get("/hello")
        async def hello_endpoint(api_key: str = Security(get_api_key)) -> Dict[str, Any]:
            """
            Simple hello endpoint that demonstrates accessing Aurite components.
            """
            # Access the Aurite instance
            aurite = application.get()

            # Access components through the Aurite instance
            config_manager = aurite.get_config_manager()
            host = aurite.kernel.host

            response: Dict[str, Any] = {
                "message": "Hello from custom extension!",
                "project_root": str(config_manager.project_root),
            }

            # Add host information if available
            if host:
                response["registered_servers"] = list(host.registered_server_names)
                response["available_tools_count"] = len(host.tools)

            return response
        @router.post("/batch-agents")
        async def batch_agents_endpoint(
            questions: list[str],
            agent_name: str = Query("default_agent", description="Agent to use"),
            api_key: str = Security(get_api_key),
            engine=Depends(get_execution_facade),
        ) -> Dict[str, Any]:
            """
            Execute multiple agent queries in sequence.

            This demonstrates how extensions can orchestrate multiple agent calls.
            """
            results = []

            for question in questions:
                result = await engine.run_agent(
                    agent_name=agent_name, user_message=question
                )
                results.append(
                    {
                        "question": question,
                        "answer": result.final_output,
                        "status": result.status,
                    }
                )

            return {
                "agent_name": agent_name,
                "total_questions": len(questions),
                "results": results,
            }

        # Register all endpoints
        app.include_router(router)


class SimpleExtension(Extension):
    """
    Minimal extension example showing the simplest possible extension.
    """

    def __call__(self, app):
        """Register a simple endpoint."""
        router = APIRouter(prefix="/simple", tags=["Simple Example"])

        @router.get("/ping")
        async def ping():
            """Simple ping endpoint - no authentication required for demo."""
            return {"message": "pong"}

        app.include_router(router)


# You can have multiple extensions in one file
# To load both: AURITE_API_EXTENSIONS="docs.usage.example_extension.CustomRAGExtension,docs.usage.example_extension.SimpleExtension"