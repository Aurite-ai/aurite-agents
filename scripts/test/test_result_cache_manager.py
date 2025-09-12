#!/usr/bin/env python3
"""
Test script for TestResultCacheManager functionality.

This script validates that the test result cache manager correctly:
1. Caches test results with TTL
2. Returns cached results when valid
3. Expires results after TTL
4. Handles different test types with appropriate TTLs
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aurite.testing.cache import TestResultCacheManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_test_result(component_id: str, test_type: str, quality_score: float = 0.95, security_score: float = 0.98):
    """Create a sample test result."""
    return {
        "component_id": component_id,
        "framework": "universal" if test_type in ["mcp", "llm"] else "aurite",
        "is_agnostic": test_type in ["mcp", "llm"],
        "cross_framework_validity": test_type in ["mcp", "llm"],
        "quality_score": quality_score,
        "security_score": security_score,
        "test_patterns_executed": ["basic_functionality", "error_handling", "security_validation"],
        "validated_tool_calls": [
            {
                "tool": "get_weather",
                "input": {"city": "San Francisco"},
                "expected_output": {"temperature": 65, "conditions": "sunny"},
            }
        ]
        if test_type == "mcp"
        else [],
        "performance_metrics": {"avg_response_time_ms": 150, "p95_response_time_ms": 250, "p99_response_time_ms": 500},
        "test_execution_time": datetime.now().isoformat(),
        "inherited_by": ["agent", "workflow"] if test_type in ["mcp", "llm"] else [],
    }


async def test_basic_caching():
    """Test basic save and retrieve functionality."""
    print("\n=== Testing Basic Caching ===")

    # Create cache manager with temp directory
    cache_dir = Path(".test_cache_temp")
    cache_manager = TestResultCacheManager(cache_dir)

    try:
        # Save a test result
        component_id = "weather_mcp_server"
        test_type = "mcp"
        test_result = create_test_result(component_id, test_type)

        print(f"Saving test result for {component_id}...")
        cache_manager.save_test_result(component_id, test_type, test_result)

        # Retrieve the result
        print(f"Retrieving test result for {component_id}...")
        cached_result = cache_manager.get_test_result(component_id, test_type)

        if cached_result:
            print("✓ Successfully retrieved cached result")
            print(f"  - Component: {cached_result['component_id']}")
            print(f"  - Quality Score: {cached_result['quality_score']}")
            print(f"  - Security Score: {cached_result['security_score']}")
            print(f"  - Expires at: {cached_result['expires_at']}")
        else:
            print("✗ Failed to retrieve cached result")
            return False

        # Test cache hit from memory
        print("\nTesting memory cache hit...")
        cached_result2 = cache_manager.get_test_result(component_id, test_type)
        if cached_result2:
            print("✓ Memory cache hit successful")
        else:
            print("✗ Memory cache hit failed")
            return False

        return True

    finally:
        # Cleanup
        import shutil

        if cache_dir.exists():
            shutil.rmtree(cache_dir)


async def test_ttl_expiration():
    """Test TTL expiration functionality."""
    print("\n=== Testing TTL Expiration ===")

    # Create cache manager with temp directory
    cache_dir = Path(".test_cache_temp")
    cache_manager = TestResultCacheManager(cache_dir)

    try:
        # Save a test result with very short TTL (2 seconds)
        component_id = "short_ttl_test"
        test_type = "workflow"  # Use workflow for shorter default TTL
        test_result = create_test_result(component_id, test_type)

        print("Saving test result with 2-second TTL...")
        cache_manager.save_test_result(component_id, test_type, test_result, ttl_override=2)

        # Verify it's retrievable immediately
        cached_result = cache_manager.get_test_result(component_id, test_type, ttl_override=2)
        if cached_result:
            print("✓ Result retrievable immediately after saving")
        else:
            print("✗ Result not retrievable immediately")
            return False

        # Wait for expiration
        print("Waiting 3 seconds for TTL expiration...")
        await asyncio.sleep(3)

        # Try to retrieve expired result
        expired_result = cache_manager.get_test_result(component_id, test_type, ttl_override=2)
        if expired_result is None:
            print("✓ Expired result correctly not returned")
        else:
            print("✗ Expired result incorrectly returned")
            return False

        return True

    finally:
        # Cleanup
        import shutil

        if cache_dir.exists():
            shutil.rmtree(cache_dir)


async def test_different_test_types():
    """Test different test types with their default TTLs."""
    print("\n=== Testing Different Test Types ===")

    # Create cache manager with temp directory
    cache_dir = Path(".test_cache_temp")
    cache_manager = TestResultCacheManager(cache_dir)

    try:
        test_types = ["mcp", "llm", "agent", "workflow"]
        expected_ttls = {
            "mcp": 86400,  # 24 hours
            "llm": 86400,  # 24 hours
            "agent": 14400,  # 4 hours
            "workflow": 3600,  # 1 hour
        }

        # Save results for each type
        for test_type in test_types:
            component_id = f"test_{test_type}_component"
            test_result = create_test_result(component_id, test_type)

            print(f"Saving {test_type} test result...")
            cache_manager.save_test_result(component_id, test_type, test_result)

            # Retrieve and verify TTL
            cached_result = cache_manager.get_test_result(component_id, test_type)
            if cached_result:
                actual_ttl = cached_result.get("ttl_seconds")
                expected_ttl = expected_ttls[test_type]
                if actual_ttl == expected_ttl:
                    print(f"✓ {test_type}: TTL = {actual_ttl}s (correct)")
                else:
                    print(f"✗ {test_type}: TTL = {actual_ttl}s (expected {expected_ttl}s)")
                    return False
            else:
                print(f"✗ Failed to retrieve {test_type} result")
                return False

        # Check cache statistics
        print("\nCache Statistics:")
        stats = cache_manager.get_cache_stats()
        print(f"  - Memory entries: {stats['memory_entries']}")
        print(f"  - Disk entries: {stats['disk_entries']}")
        print(f"  - By type: {stats['by_type']}")
        print(f"  - Valid: {stats['valid']}")
        print(f"  - Expired: {stats['expired']}")

        return True

    finally:
        # Cleanup
        import shutil

        if cache_dir.exists():
            shutil.rmtree(cache_dir)


async def test_cache_invalidation():
    """Test cache invalidation functionality."""
    print("\n=== Testing Cache Invalidation ===")

    # Create cache manager with temp directory
    cache_dir = Path(".test_cache_temp")
    cache_manager = TestResultCacheManager(cache_dir)

    try:
        # Save a test result
        component_id = "invalidation_test"
        test_type = "mcp"
        test_result = create_test_result(component_id, test_type)

        print("Saving test result...")
        cache_manager.save_test_result(component_id, test_type, test_result)

        # Verify it exists
        if cache_manager.get_test_result(component_id, test_type):
            print("✓ Result exists in cache")
        else:
            print("✗ Result not found in cache")
            return False

        # Invalidate the result
        print("Invalidating cached result...")
        if cache_manager.invalidate_test_result(component_id, test_type):
            print("✓ Result invalidated successfully")
        else:
            print("✗ Failed to invalidate result")
            return False

        # Verify it's gone
        if cache_manager.get_test_result(component_id, test_type) is None:
            print("✓ Result no longer in cache")
        else:
            print("✗ Result still in cache after invalidation")
            return False

        return True

    finally:
        # Cleanup
        import shutil

        if cache_dir.exists():
            shutil.rmtree(cache_dir)


async def test_cleanup_expired():
    """Test cleanup of expired entries."""
    print("\n=== Testing Cleanup of Expired Entries ===")

    # Create cache manager with temp directory
    cache_dir = Path(".test_cache_temp")
    cache_manager = TestResultCacheManager(cache_dir)

    try:
        # Save some results with very short TTL
        for i in range(3):
            component_id = f"cleanup_test_{i}"
            test_type = "workflow"
            test_result = create_test_result(component_id, test_type)

            print(f"Saving result {i + 1}/3 with 1-second TTL...")
            cache_manager.save_test_result(component_id, test_type, test_result, ttl_override=1)

        # Save one with long TTL
        long_ttl_id = "long_ttl_component"
        cache_manager.save_test_result(long_ttl_id, "mcp", create_test_result(long_ttl_id, "mcp"))

        # Wait for short TTL results to expire
        print("Waiting 2 seconds for expiration...")
        await asyncio.sleep(2)

        # Run cleanup
        print("Running cleanup...")
        removed_count = cache_manager.cleanup_expired()
        print(f"✓ Removed {removed_count} expired entries")

        # Verify long TTL result still exists
        if cache_manager.get_test_result(long_ttl_id, "mcp"):
            print("✓ Long TTL result still exists")
        else:
            print("✗ Long TTL result was incorrectly removed")
            return False

        # Verify short TTL results are gone
        for i in range(3):
            component_id = f"cleanup_test_{i}"
            if cache_manager.get_test_result(component_id, "workflow", ttl_override=1) is None:
                print(f"✓ Expired result {i + 1} correctly removed")
            else:
                print(f"✗ Expired result {i + 1} still exists")
                return False

        return True

    finally:
        # Cleanup
        import shutil

        if cache_dir.exists():
            shutil.rmtree(cache_dir)


async def main():
    """Run all tests."""
    print("=" * 60)
    print("TestResultCacheManager Test Suite")
    print("=" * 60)

    tests = [
        ("Basic Caching", test_basic_caching),
        ("TTL Expiration", test_ttl_expiration),
        ("Different Test Types", test_different_test_types),
        ("Cache Invalidation", test_cache_invalidation),
        ("Cleanup Expired", test_cleanup_expired),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}", exc_info=True)
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("All tests PASSED! ✓")
    else:
        print("Some tests FAILED! ✗")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
