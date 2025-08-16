#!/usr/bin/env python3
"""
Test script to verify the async shutdown fixes for litellm client.
This should run without showing the colorlog AttributeError or unclosed session warnings.
"""

import asyncio
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from aurite import Aurite


async def test_shutdown():
    """Test that shutdown happens cleanly without errors."""
    print("Starting Aurite test...")

    # Create an Aurite instance
    aurite = Aurite()

    # Initialize it (this will set up the host and other components)
    await aurite._ensure_initialized()

    print("Aurite initialized successfully")

    # Simulate some work
    await asyncio.sleep(0.1)

    print("Shutting down Aurite...")

    # Explicitly shutdown
    await aurite.kernel.shutdown()

    print("Shutdown complete")


def main():
    """Run the test."""
    try:
        asyncio.run(test_shutdown())
        print("\nTest completed successfully!")
        print("If you don't see any AttributeError or 'Unclosed client session' warnings above,")
        print("then the fixes are working correctly.")
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
