#!/usr/bin/env python3
"""
Test script to diagnose and fix Swagger UI static assets issue.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx
import uvicorn
from fastapi import FastAPI


async def test_swagger_ui_assets():
    """Test if Swagger UI assets are accessible."""

    print("Testing Swagger UI assets accessibility...")

    # Test URLs that should be served by FastAPI internally
    test_urls = [
        "http://localhost:8000/api-docs",
        "http://localhost:8000/openapi.json",
        "http://localhost:8000/swagger/swagger-ui-bundle.js",
        "http://localhost:8000/swagger/swagger-ui.css",
    ]

    async with httpx.AsyncClient() as client:
        for url in test_urls:
            try:
                response = await client.get(url, timeout=5.0)
                print(f"✓ {url} -> {response.status_code}")
                if response.status_code == 404:
                    print(f"  ❌ 404 Error for {url}")
            except Exception as e:
                print(f"  ❌ Error accessing {url}: {e}")


def create_minimal_test_app():
    """Create a minimal FastAPI app to test Swagger UI."""

    app = FastAPI(title="Test API", docs_url="/api-docs", redoc_url="/redoc", openapi_url="/openapi.json")

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    return app


async def test_minimal_app():
    """Test with a minimal FastAPI app."""

    print("\n" + "=" * 50)
    print("Testing with minimal FastAPI app...")
    print("=" * 50)

    app = create_minimal_test_app()

    # Start server in background
    config = uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="error")
    server = uvicorn.Server(config)

    # Run server in background task
    server_task = asyncio.create_task(server.serve())

    # Wait a moment for server to start
    await asyncio.sleep(2)

    # Test the minimal app
    test_urls = [
        "http://localhost:8001/api-docs",
        "http://localhost:8001/openapi.json",
        "http://localhost:8001/swagger/swagger-ui-bundle.js",
        "http://localhost:8001/swagger/swagger-ui.css",
    ]

    async with httpx.AsyncClient() as client:
        for url in test_urls:
            try:
                response = await client.get(url, timeout=5.0)
                print(f"✓ {url} -> {response.status_code}")
                if response.status_code == 404:
                    print(f"  ❌ 404 Error for {url}")
                elif response.status_code == 200:
                    content_type = response.headers.get("content-type", "unknown")
                    print(f"  ✓ Content-Type: {content_type}")
            except Exception as e:
                print(f"  ❌ Error accessing {url}: {e}")

    # Stop the server
    server.should_exit = True
    await server_task


def check_fastapi_version():
    """Check FastAPI version for compatibility."""
    try:
        import fastapi

        print(f"FastAPI version: {fastapi.__version__}")

        # Check if this version has known Swagger UI issues
        version_parts = fastapi.__version__.split(".")
        major, minor = int(version_parts[0]), int(version_parts[1])

        if major == 0 and minor >= 100:
            print("✓ FastAPI version should support automatic Swagger UI serving")
        else:
            print("⚠ FastAPI version might have Swagger UI serving issues")

    except ImportError:
        print("❌ FastAPI not found")


async def main():
    """Main test function."""

    print("Swagger UI Assets Diagnostic Tool")
    print("=" * 40)

    # Check FastAPI version
    check_fastapi_version()

    # Test current server (if running)
    print("\nTesting current server at localhost:8000...")
    await test_swagger_ui_assets()

    # Test minimal app
    await test_minimal_app()

    print("\n" + "=" * 50)
    print("Diagnosis complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
