from __future__ import annotations

import asyncio
import importlib.metadata
import logging
import os
import platform
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel

from ...dependencies import get_api_key, get_aurite

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["System Management"])


class SystemInfo(BaseModel):
    """System information response model."""

    platform: str
    platform_version: str
    python_version: str
    python_implementation: str
    hostname: str
    cpu_count: int
    architecture: str
    os_details: Dict[str, str]


class FrameworkVersion(BaseModel):
    """Framework version information."""

    version: str
    name: str
    description: str
    authors: List[str]
    license: str
    repository: str
    python_requirement: str


class SystemCapabilities(BaseModel):
    """System capabilities information."""

    mcp_support: bool
    api_enabled: bool
    cli_enabled: bool
    tui_enabled: bool
    available_transports: List[str]
    supported_llm_providers: List[str]
    storage_backends: List[str]
    optional_features: Dict[str, bool]


class EnvironmentVariable(BaseModel):
    """Environment variable model."""

    name: str
    value: Optional[str]
    is_sensitive: bool = False


class EnvironmentUpdate(BaseModel):
    """Request model for updating environment variables."""

    variables: Dict[str, str]


class DependencyInfo(BaseModel):
    """Dependency information model."""

    name: str
    version: str
    location: Optional[str]
    summary: Optional[str]


class DependencyHealth(BaseModel):
    """Dependency health check result."""

    name: str
    installed: bool
    version: Optional[str]
    importable: bool
    error: Optional[str]


class SystemMetrics(BaseModel):
    """System metrics model."""

    timestamp: datetime
    cpu_percent: float
    memory_usage: Dict[str, Any]
    disk_usage: Dict[str, Any]
    process_info: Dict[str, Any]
    python_info: Dict[str, Any]


class ActiveProcess(BaseModel):
    """Active process information."""

    name: str
    pid: int
    status: str
    cpu_percent: float
    memory_percent: float
    create_time: datetime
    cmdline: List[str]


class HealthCheckResult(BaseModel):
    """Comprehensive health check result."""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    components: Dict[str, Dict[str, Any]]
    issues: List[str]


# Sensitive environment variable patterns
SENSITIVE_ENV_PATTERNS = [
    "KEY",
    "SECRET",
    "PASSWORD",
    "TOKEN",
    "CREDENTIAL",
    "AUTH",
    "PRIVATE",
]


def is_sensitive_env_var(name: str) -> bool:
    """Check if an environment variable name suggests it contains sensitive data."""
    upper_name = name.upper()
    return any(pattern in upper_name for pattern in SENSITIVE_ENV_PATTERNS)


@router.get("/info", response_model=SystemInfo)
async def get_system_info(api_key: str = Security(get_api_key)):
    """
    Get detailed system information including platform, Python version, and hardware details.
    """
    try:
        # Get CPU count, handling potential errors
        try:
            cpu_count = os.cpu_count() or 1
        except Exception:
            cpu_count = 1

        return SystemInfo(
            platform=platform.system(),
            platform_version=platform.version(),
            python_version=sys.version.split()[0],
            python_implementation=platform.python_implementation(),
            hostname=platform.node(),
            cpu_count=cpu_count,
            architecture=platform.machine(),
            os_details={
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            },
        )
    except Exception as e:
        logger.error(f"Error getting system info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get system info: {str(e)}") from e


@router.get("/version", response_model=FrameworkVersion)
async def get_framework_version(api_key: str = Security(get_api_key)):
    """
    Get Aurite Framework version information.
    """
    try:
        # Try to get package metadata
        try:
            metadata = importlib.metadata.metadata("aurite")
            version = metadata.get("Version", "unknown")
            description = metadata.get("Summary", "Aurite Agents Framework")
            authors = []

            # Parse authors from metadata
            author_entries = metadata.get_all("Author-email", [])
            if author_entries:
                for entry in author_entries:
                    if "<" in entry and ">" in entry:
                        name = entry.split("<")[0].strip()
                        if name:  # Only add if name exists
                            authors.append(name)
                        else:
                            # If no name before email, use the email
                            authors.append(entry)
                    else:
                        authors.append(entry)

            # If no authors found in metadata, check Author field
            if not authors:
                author_names = metadata.get_all("Author", [])
                if author_names:
                    authors.extend(author_names)

            # Get repository URL
            repo_url = "https://github.com/Aurite-ai/aurite-agents"
            for url in metadata.get_all("Project-URL", []):
                if "Repository" in url:
                    repo_url = url.split(",", 1)[1].strip()
                    break

        except Exception:
            # Fallback to hardcoded values if metadata not available
            version = "0.3.26"
            description = "Aurite Agents is an agent development and runtime framework."
            authors = ["Ryan W", "Blake R", "Patrick W", "Jiten O"]
            repo_url = "https://github.com/Aurite-ai/aurite-agents"

        return FrameworkVersion(
            version=version,
            name="Aurite Agents",
            description=description,
            authors=authors,
            license="MIT",
            repository=repo_url,
            python_requirement=">=3.11,<4.0.0",
        )
    except Exception as e:
        logger.error(f"Error getting framework version: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get version info: {str(e)}") from e


@router.get("/capabilities", response_model=SystemCapabilities)
async def get_system_capabilities(api_key: str = Security(get_api_key)):
    """
    List system capabilities and available features.
    """
    # Check for optional dependencies
    optional_features = {}

    # Check for ML dependencies
    try:
        import pandas  # type: ignore # noqa: F401

        optional_features["pandas"] = True
    except ImportError:
        optional_features["pandas"] = False

    try:
        # Try importing sentence_transformers if available
        __import__("sentence_transformers")
        optional_features["sentence_transformers"] = True
    except ImportError:
        optional_features["sentence_transformers"] = False

    # Set ml_support based on both dependencies
    optional_features["ml_support"] = optional_features.get("pandas", False) and optional_features.get(
        "sentence_transformers", False
    )

    # Check for storage dependencies
    try:
        import redis  # noqa: F401

        optional_features["redis_cache"] = True
    except ImportError:
        optional_features["redis_cache"] = False

    try:
        import psycopg2  # noqa: F401

        optional_features["postgresql"] = True
    except ImportError:
        optional_features["postgresql"] = False

    try:
        import mem0  # noqa: F401

        optional_features["mem0_memory"] = True
    except ImportError:
        optional_features["mem0_memory"] = False

    # Get supported LLM providers from litellm
    supported_llm_providers = [
        "openai",
        "anthropic",
        "azure",
        "google",
        "cohere",
        "replicate",
        "huggingface",
        "together_ai",
        "openrouter",
        "vertex_ai",
        "bedrock",
        "ollama",
        "groq",
        "deepseek",
    ]

    return SystemCapabilities(
        mcp_support=True,
        api_enabled=True,
        cli_enabled=True,
        tui_enabled=True,
        available_transports=["stdio", "local", "http_stream"],
        supported_llm_providers=supported_llm_providers,
        storage_backends=["sqlite", "json", "redis", "postgresql"],
        optional_features=optional_features,
    )


@router.get("/environment", response_model=List[EnvironmentVariable])
async def get_environment_variables(api_key: str = Security(get_api_key)):
    """
    Get environment variables (sensitive values are masked).
    """
    env_vars = []

    for name, value in os.environ.items():
        is_sensitive = is_sensitive_env_var(name)

        env_vars.append(
            EnvironmentVariable(
                name=name,
                value="***MASKED***" if is_sensitive else value,
                is_sensitive=is_sensitive,
            )
        )

    # Sort by name for consistency
    env_vars.sort(key=lambda x: x.name)

    return env_vars


@router.put("/environment")
async def update_environment_variables(
    update: EnvironmentUpdate,
    api_key: str = Security(get_api_key),
):
    """
    Update environment variables (only non-sensitive variables can be updated).
    """
    updated = []
    errors = []

    for name, value in update.variables.items():
        if is_sensitive_env_var(name):
            errors.append(f"Cannot update sensitive variable: {name}")
            continue

        try:
            os.environ[name] = value
            updated.append(name)
        except Exception as e:
            logger.error(f"Failed to update {name}: {e}", exc_info=True)
            errors.append(f"Failed to update {name}: An internal error occurred.")

    return {
        "updated": updated,
        "errors": errors,
        "status": "partial" if errors else "success",
    }


@router.get("/dependencies", response_model=List[DependencyInfo])
async def list_dependencies(api_key: str = Security(get_api_key)):
    """
    List all installed Python dependencies.
    """
    dependencies = []

    try:
        # Get all installed distributions
        for dist in importlib.metadata.distributions():
            try:
                # Get location safely - just leave it as None for now
                # since getting the actual location is complex and varies by Python version
                location = None

                dependencies.append(
                    DependencyInfo(
                        name=dist.name,
                        version=dist.version,
                        location=location,
                        summary=dist.metadata.get("Summary"),
                    )
                )
            except Exception as e:
                logger.warning(f"Error getting info for {dist.name}: {e}")

        # Sort by name
        dependencies.sort(key=lambda x: x.name.lower())

    except Exception as e:
        logger.error(f"Error listing dependencies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list dependencies: {str(e)}") from e

    return dependencies


@router.post("/dependencies/check", response_model=List[DependencyHealth])
async def check_dependency_health(api_key: str = Security(get_api_key)):
    """
    Check the health of critical dependencies.
    """
    # List of critical dependencies to check
    critical_deps = [
        "mcp",
        "pydantic",
        "fastapi",
        "uvicorn",
        "litellm",
        "openai",
        "sqlalchemy",
        "typer",
        "textual",
        "rich",
        "httpx",
        "anyio",
    ]

    results = []

    for dep_name in critical_deps:
        health = DependencyHealth(
            name=dep_name,
            installed=False,
            version=None,
            importable=False,
            error=None,
        )

        try:
            # Check if installed
            dist = importlib.metadata.distribution(dep_name)
            health.installed = True
            health.version = dist.version

            # Try to import it
            try:
                importlib.import_module(dep_name.replace("-", "_"))
                health.importable = True
            except ImportError as e:
                health.error = f"Import failed: {str(e)}"

        except importlib.metadata.PackageNotFoundError:
            health.error = "Package not found"
        except Exception as e:
            health.error = str(e)

        results.append(health)

    return results


@router.get("/monitoring/metrics", response_model=SystemMetrics)
async def get_system_metrics(api_key: str = Security(get_api_key)):
    """
    Get current system metrics including CPU, memory, and disk usage.
    """
    try:
        # Try to use psutil if available
        try:
            import psutil

            # Get current process
            process = psutil.Process()

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free,
            }

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_usage = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
            }

            # Process info
            process_info = {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "memory_info": process.memory_info()._asdict(),
                "num_threads": process.num_threads(),
            }

        except ImportError:
            # Fallback if psutil not available
            import resource

            cpu_percent = 0.0

            # Basic memory info from resource module
            usage = resource.getrusage(resource.RUSAGE_SELF)
            memory_usage = {
                "max_rss": usage.ru_maxrss,
                "percent": 0.0,
            }

            disk_usage = {"percent": 0.0}

            process_info = {
                "pid": os.getpid(),
                "user_time": usage.ru_utime,
                "system_time": usage.ru_stime,
            }

        # Python-specific info
        import gc

        python_info = {
            "gc_counts": gc.get_count(),
            "gc_stats": gc.get_stats() if hasattr(gc, "get_stats") else [],
            "thread_count": len(asyncio.all_tasks()),
        }

        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            process_info=process_info,
            python_info=python_info,
        )

    except Exception as e:
        logger.error(f"Error getting system metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}") from e


@router.get("/monitoring/active", response_model=List[ActiveProcess])
async def list_active_processes(api_key: str = Security(get_api_key)):
    """
    List active Aurite-related processes.
    """
    processes = []

    try:
        import psutil

        current_pid = os.getpid()

        # Get current process and its children
        try:
            current_process = psutil.Process(current_pid)

            # Add current process
            processes.append(
                ActiveProcess(
                    name=current_process.name(),
                    pid=current_process.pid,
                    status=current_process.status(),
                    cpu_percent=current_process.cpu_percent(),
                    memory_percent=current_process.memory_percent(),
                    create_time=datetime.fromtimestamp(current_process.create_time()),
                    cmdline=current_process.cmdline(),
                )
            )

            # Add child processes
            for child in current_process.children(recursive=True):
                try:
                    processes.append(
                        ActiveProcess(
                            name=child.name(),
                            pid=child.pid,
                            status=child.status(),
                            cpu_percent=child.cpu_percent(),
                            memory_percent=child.memory_percent(),
                            create_time=datetime.fromtimestamp(child.create_time()),
                            cmdline=child.cmdline(),
                        )
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except psutil.NoSuchProcess:
            pass

    except ImportError:
        # If psutil not available, return minimal info
        processes.append(
            ActiveProcess(
                name="aurite-api",
                pid=os.getpid(),
                status="running",
                cpu_percent=0.0,
                memory_percent=0.0,
                create_time=datetime.now(),
                cmdline=sys.argv,
            )
        )

    return processes


@router.get("/health", response_model=HealthCheckResult)
async def comprehensive_health_check(
    api_key: str = Security(get_api_key),
    aurite=Depends(get_aurite),
):
    """
    Perform a comprehensive health check of all system components.
    """
    issues = []
    components = {}

    # Check API health
    components["api"] = {
        "status": "healthy",
        "uptime": time.time() - aurite._start_time if hasattr(aurite, "_start_time") else 0,
    }

    # Check ConfigManager
    try:
        config_manager = aurite.get_config_manager()
        components["config_manager"] = {
            "status": "healthy",
            "project_root": str(config_manager.project_root),
            "cache_enabled": hasattr(config_manager, "_cache"),
        }
    except Exception as e:
        components["config_manager"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        issues.append(f"ConfigManager error: {e}")

    # Check MCPHost
    try:
        if aurite.kernel.host:
            host = aurite.kernel.host
            components["mcp_host"] = {
                "status": "healthy",
                "registered_servers": len(host.registered_server_names),
                "available_tools": len(host.tools),
            }
        else:
            components["mcp_host"] = {
                "status": "degraded",
                "error": "MCPHost not initialized",
            }
            issues.append("MCPHost not initialized")
    except Exception as e:
        components["mcp_host"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        issues.append(f"MCPHost error: {e}")

    # Check AuriteEngine
    try:
        if aurite.kernel.execution:
            components["execution_facade"] = {
                "status": "healthy",
                "ready": True,
            }
        else:
            components["execution_facade"] = {
                "status": "degraded",
                "error": "AuriteEngine not initialized",
            }
            issues.append("AuriteEngine not initialized")
    except Exception as e:
        components["execution_facade"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        issues.append(f"AuriteEngine error: {e}")

    # Check database connectivity
    try:
        # This would check actual database connection if implemented
        components["database"] = {
            "status": "healthy",
            "type": "sqlite",
        }
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        issues.append(f"Database error: {e}")

    # Determine overall status
    if any(comp.get("status") == "unhealthy" for comp in components.values()):
        overall_status = "unhealthy"
    elif any(comp.get("status") == "degraded" for comp in components.values()):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthCheckResult(
        status=overall_status,
        timestamp=datetime.now(),
        components=components,
        issues=issues,
    )
