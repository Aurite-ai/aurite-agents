import os

from fastapi import APIRouter

from . import config_routes, execution_routes, system_routes, testing_routes, tools_routes

main_router = APIRouter()

main_router.include_router(tools_routes.router)
main_router.include_router(config_routes.router)
main_router.include_router(execution_routes.router)
main_router.include_router(testing_routes.router)


if os.getenv("INCLUDE_SYSTEM_ROUTER", "false").lower() == "true":
    main_router.include_router(system_routes.router)

__all__ = ["main_router"]
