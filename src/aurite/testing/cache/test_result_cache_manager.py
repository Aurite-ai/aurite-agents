"""
Test result cache manager with TTL support for framework-agnostic testing.

This module provides caching for test results with configurable time-to-live (TTL)
to enable cross-framework test result sharing and avoid redundant testing.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from aurite.lib.storage.sessions.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class TestResultCacheManager(CacheManager):
    """
    Extended cache manager for test results with TTL support.

    Provides caching for framework-agnostic test results with configurable
    time-to-live (TTL) to enable result sharing across frameworks.
    """

    # Default TTL values in seconds
    DEFAULT_TTL_MCP = 86400  # 24 hours for MCP servers (100% agnostic)
    DEFAULT_TTL_LLM = 86400  # 24 hours for LLM tests (100% agnostic)
    DEFAULT_TTL_AGENT = 14400  # 4 hours for agent tests (60% agnostic)
    DEFAULT_TTL_WORKFLOW = 3600  # 1 hour for workflow tests (20% agnostic)

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the test result cache manager.

        Args:
            cache_dir: Directory to store cache files. Defaults to .aurite_test_cache
        """
        # Use a different default directory for test results
        if cache_dir is None:
            cache_dir = Path(".aurite_test_cache")

        super().__init__(cache_dir)
        logger.info(f"TestResultCacheManager initialized with cache_dir: {self._cache_dir.absolute()}")

    def _get_test_result_file(self, component_id: str, test_type: str) -> Path:
        """
        Get the file path for a test result.

        Args:
            component_id: Unique identifier for the component being tested
            test_type: Type of test (mcp, llm, agent, workflow)

        Returns:
            Path to the test result cache file
        """
        # Sanitize inputs to prevent directory traversal
        safe_component_id = "".join(c for c in component_id if c.isalnum() or c in "-_")
        safe_test_type = "".join(c for c in test_type if c.isalnum() or c in "-_")

        # Create subdirectory for test type if it doesn't exist
        type_dir = self._cache_dir / safe_test_type
        type_dir.mkdir(exist_ok=True)

        return type_dir / f"{safe_component_id}.json"

    def _is_expired(self, timestamp: str, ttl_seconds: int) -> bool:
        """
        Check if a cached result has expired based on TTL.

        Args:
            timestamp: ISO format timestamp of when the result was cached
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if expired, False otherwise
        """
        try:
            cached_time = datetime.fromisoformat(timestamp)
            expiry_time = cached_time + timedelta(seconds=ttl_seconds)
            return datetime.now() > expiry_time
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid timestamp format: {timestamp}, error: {e}")
            return True  # Treat invalid timestamps as expired

    def get_test_result(
        self, component_id: str, test_type: str, ttl_override: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached test result if it exists and hasn't expired.

        Args:
            component_id: Unique identifier for the component
            test_type: Type of test (mcp, llm, agent, workflow)
            ttl_override: Optional TTL override in seconds

        Returns:
            The cached test result dict if valid, None if not found or expired
        """
        # Determine TTL based on test type
        ttl_map = {
            "mcp": self.DEFAULT_TTL_MCP,
            "llm": self.DEFAULT_TTL_LLM,
            "agent": self.DEFAULT_TTL_AGENT,
            "workflow": self.DEFAULT_TTL_WORKFLOW,
        }
        ttl_seconds = ttl_override or ttl_map.get(test_type, self.DEFAULT_TTL_AGENT)

        # Check if we have this result in memory cache first
        cache_key = f"{test_type}:{component_id}"
        if cache_key in self._result_cache:
            cached_data = self._result_cache[cache_key]
            if not self._is_expired(cached_data.get("timestamp", ""), ttl_seconds):
                logger.info(f"Cache hit (memory) for {cache_key}")
                return cached_data
            else:
                logger.info(f"Cache expired (memory) for {cache_key}")
                del self._result_cache[cache_key]

        # Try to load from disk
        result_file = self._get_test_result_file(component_id, test_type)
        if result_file.exists():
            try:
                with open(result_file, "r") as f:
                    cached_data = json.load(f)

                # Check if expired
                if not self._is_expired(cached_data.get("timestamp", ""), ttl_seconds):
                    # Update memory cache
                    self._result_cache[cache_key] = cached_data
                    logger.info(f"Cache hit (disk) for {cache_key}")
                    return cached_data
                else:
                    logger.info(f"Cache expired (disk) for {cache_key}")
                    # Delete expired file
                    result_file.unlink()
            except Exception as e:
                logger.error(f"Failed to load test result from {result_file}: {e}")

        logger.info(f"Cache miss for {cache_key}")
        return None

    def save_test_result(
        self, component_id: str, test_type: str, test_result: Dict[str, Any], ttl_override: Optional[int] = None
    ):
        """
        Save a test result to cache with TTL metadata.

        Args:
            component_id: Unique identifier for the component
            test_type: Type of test (mcp, llm, agent, workflow)
            test_result: The test result data to cache
            ttl_override: Optional TTL override in seconds
        """
        # Determine TTL
        ttl_map = {
            "mcp": self.DEFAULT_TTL_MCP,
            "llm": self.DEFAULT_TTL_LLM,
            "agent": self.DEFAULT_TTL_AGENT,
            "workflow": self.DEFAULT_TTL_WORKFLOW,
        }
        ttl_seconds = ttl_override or ttl_map.get(test_type, self.DEFAULT_TTL_AGENT)

        # Add metadata to the result
        cached_data = {
            **test_result,
            "component_id": component_id,
            "test_type": test_type,
            "timestamp": datetime.now().isoformat(),
            "ttl_seconds": ttl_seconds,
            "expires_at": (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat(),
        }

        # Update memory cache
        cache_key = f"{test_type}:{component_id}"
        self._result_cache[cache_key] = cached_data

        # Save to disk
        result_file = self._get_test_result_file(component_id, test_type)
        try:
            with open(result_file, "w") as f:
                json.dump(cached_data, f, indent=2)
            logger.info(f"Saved test result for {cache_key} to {result_file}")
        except Exception as e:
            logger.error(f"Failed to save test result to {result_file}: {e}")

    def invalidate_test_result(self, component_id: str, test_type: str) -> bool:
        """
        Invalidate (delete) a cached test result.

        Args:
            component_id: Unique identifier for the component
            test_type: Type of test (mcp, llm, agent, workflow)

        Returns:
            True if deleted successfully, False if not found
        """
        cache_key = f"{test_type}:{component_id}"

        # Remove from memory
        exists_in_memory = self._result_cache.pop(cache_key, None) is not None

        # Remove from disk
        result_file = self._get_test_result_file(component_id, test_type)
        exists_on_disk = False
        if result_file.exists():
            try:
                result_file.unlink()
                exists_on_disk = True
            except Exception as e:
                logger.error(f"Failed to delete test result file {result_file}: {e}")

        return exists_in_memory or exists_on_disk

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "memory_entries": len(self._result_cache),
            "disk_entries": 0,
            "by_type": {"mcp": 0, "llm": 0, "agent": 0, "workflow": 0},
            "expired": 0,
            "valid": 0,
        }

        # Count disk entries and check expiry
        for test_type in ["mcp", "llm", "agent", "workflow"]:
            type_dir = self._cache_dir / test_type
            if type_dir.exists():
                for result_file in type_dir.glob("*.json"):
                    stats["disk_entries"] += 1
                    try:
                        with open(result_file, "r") as f:
                            data = json.load(f)

                        ttl = data.get("ttl_seconds", 86400)
                        if self._is_expired(data.get("timestamp", ""), ttl):
                            stats["expired"] += 1
                        else:
                            stats["valid"] += 1
                            stats["by_type"][test_type] += 1
                    except Exception:
                        pass

        return stats

    def cleanup_expired(self) -> int:
        """
        Remove all expired test results from cache.

        Returns:
            Number of expired entries removed
        """
        removed_count = 0

        # Clean memory cache
        keys_to_remove = []
        for cache_key, cached_data in self._result_cache.items():
            ttl = cached_data.get("ttl_seconds", 86400)
            if self._is_expired(cached_data.get("timestamp", ""), ttl):
                keys_to_remove.append(cache_key)

        for key in keys_to_remove:
            del self._result_cache[key]
            removed_count += 1

        # Clean disk cache
        for test_type in ["mcp", "llm", "agent", "workflow"]:
            type_dir = self._cache_dir / test_type
            if type_dir.exists():
                for result_file in type_dir.glob("*.json"):
                    try:
                        with open(result_file, "r") as f:
                            data = json.load(f)

                        ttl = data.get("ttl_seconds", 86400)
                        if self._is_expired(data.get("timestamp", ""), ttl):
                            result_file.unlink()
                            removed_count += 1
                    except Exception as e:
                        logger.warning(f"Error checking/removing {result_file}: {e}")

        logger.info(f"Cleaned up {removed_count} expired test results")
        return removed_count
