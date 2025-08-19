"""
Static file server module for Aurite Studio.

This module provides FastAPI static file serving with SPA routing support
for the pre-built React application assets.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# Import for server configuration
from ..dependencies import get_server_config


def get_static_assets_path() -> Optional[Path]:
    """
    Get the path to static assets directory.
    
    Returns:
        Path to static assets if they exist, None otherwise
    """
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists() and static_dir.is_dir():
        return static_dir
    return None


def setup_static_serving(app: FastAPI, mount_path: str = "/studio") -> bool:
    """
    Setup static file serving for Aurite Studio.
    
    Args:
        app: FastAPI application instance
        mount_path: Path to mount the static files (default: "/studio")
        
    Returns:
        True if static serving was set up successfully, False otherwise
    """
    static_dir = get_static_assets_path()
    
    if not static_dir:
        return False
    
    # Mount static assets (JS, CSS, images, etc.) at /studio/static to match React build expectations
    static_assets_dir = static_dir / "static"
    if static_assets_dir.exists():
        app.mount("/studio/static", StaticFiles(directory=static_assets_dir), name="studio_static_assets")
    
    # Mount studio-specific assets that React expects at /studio/ paths
    @app.get("/studio/favicon.ico")
    async def serve_studio_favicon():
        """Serve favicon from static assets."""
        return serve_spa_file(static_dir, "favicon.ico")
    
    @app.get("/studio/logo.png")
    async def serve_studio_logo():
        """Serve logo from static assets."""
        return serve_spa_file(static_dir, "logo.png")
    
    @app.get("/studio/manifest.json")
    async def serve_studio_manifest():
        """Serve manifest from static assets."""
        return serve_spa_file(static_dir, "manifest.json")
    
    @app.get("/studio/apple-touch-icon.png")
    async def serve_studio_apple_touch_icon():
        """Serve apple touch icon from static assets."""
        return serve_spa_file(static_dir, "apple-touch-icon.png")
    
    @app.get("/studio/robots.txt")
    async def serve_studio_robots():
        """Serve robots.txt from static assets."""
        return serve_spa_file(static_dir, "robots.txt")
    
    @app.get("/studio/sitemap.xml")
    async def serve_studio_sitemap():
        """Serve sitemap.xml from static assets."""
        return serve_spa_file(static_dir, "sitemap.xml")
    
    @app.get("/studio/browserconfig.xml")
    async def serve_studio_browserconfig():
        """Serve browserconfig.xml from static assets."""
        return serve_spa_file(static_dir, "browserconfig.xml")
    
    # SPA routing - serve index.html for all studio routes
    @app.get(f"{mount_path}/{{path:path}}")
    async def serve_studio_spa(path: str):
        """Serve the React SPA for all studio routes."""
        return serve_spa_file(static_dir, "")  # Always serve index.html for SPA routing
    
    # Root studio route
    @app.get(mount_path)
    async def serve_studio_root():
        """Serve the React SPA for the root studio route."""
        return serve_spa_file(static_dir, "")
    
    return True


def serve_spa_file(static_dir: Path, path: str):
    """
    Serve SPA files with proper fallback to index.html and template injection.
    
    Args:
        static_dir: Directory containing static assets
        path: Requested path
        
    Returns:
        FileResponse for the requested file or HTMLResponse with injected config for index.html
    """
    # Handle root path or SPA routes - serve index.html with template injection
    if not path or path == "/" or not (static_dir / path).exists():
        return serve_injected_html(static_dir / "index.html")
    
    # Check if specific file exists
    file_path = static_dir / path
    if file_path.exists() and file_path.is_file():
        # For HTML files, inject configuration
        if file_path.suffix.lower() == '.html':
            return serve_injected_html(file_path)
        
        # For other files, serve directly
        media_type = get_media_type(file_path.suffix)
        return FileResponse(file_path, media_type=media_type)
    
    # For all other routes (React Router paths), serve index.html with injection
    return serve_injected_html(static_dir / "index.html")


def serve_injected_html(html_file_path: Path) -> HTMLResponse:
    """
    Serve HTML file with server configuration injected.
    
    Args:
        html_file_path: Path to the HTML file to serve
        
    Returns:
        HTMLResponse with injected configuration
    """
    try:
        # Read the HTML template
        html_content = html_file_path.read_text(encoding='utf-8')
        
        # Get server configuration
        server_config = get_server_config()
        
        if server_config:
            # Get version info
            try:
                from importlib.metadata import version
                aurite_version = version("aurite")
            except Exception:
                aurite_version = "unknown"
            
            # Replace template placeholders with actual values
            html_content = html_content.replace('{{API_KEY}}', server_config.API_KEY or '')
            html_content = html_content.replace('{{API_BASE_URL}}', f'http://localhost:{server_config.PORT}')
            html_content = html_content.replace('{{SERVER_PORT}}', str(server_config.PORT))
            html_content = html_content.replace('{{ENVIRONMENT}}', 'production')
            html_content = html_content.replace('{{VERSION}}', aurite_version)
        else:
            # Fallback values if server config is not available
            html_content = html_content.replace('{{API_KEY}}', '')
            html_content = html_content.replace('{{API_BASE_URL}}', 'http://localhost:8000')
            html_content = html_content.replace('{{SERVER_PORT}}', '8000')
            html_content = html_content.replace('{{ENVIRONMENT}}', 'production')
            html_content = html_content.replace('{{VERSION}}', 'unknown')
        
        return HTMLResponse(content=html_content, media_type="text/html")
        
    except Exception as e:
        # If template injection fails, serve the file directly
        return FileResponse(html_file_path, media_type="text/html")


def get_media_type(file_extension: str) -> str:
    """
    Get appropriate media type for file extension.
    
    Args:
        file_extension: File extension (including dot)
        
    Returns:
        Appropriate media type string
    """
    media_types = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".eot": "application/vnd.ms-fontobject",
        ".xml": "application/xml",
        ".txt": "text/plain",
    }
    
    return media_types.get(file_extension.lower(), "application/octet-stream")


def is_static_assets_available() -> bool:
    """
    Check if static assets are available for serving.
    
    Returns:
        True if static assets directory exists and contains index.html
    """
    static_dir = get_static_assets_path()
    if not static_dir:
        return False
    
    index_file = static_dir / "index.html"
    return index_file.exists()


def get_static_assets_info() -> dict:
    """
    Get information about available static assets.
    
    Returns:
        Dictionary with static assets information
    """
    static_dir = get_static_assets_path()
    
    if not static_dir:
        return {
            "available": False,
            "path": None,
            "files": 0,
            "size_mb": 0
        }
    
    try:
        # Count files and calculate total size
        files = list(static_dir.rglob('*'))
        file_count = len([f for f in files if f.is_file()])
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        
        return {
            "available": True,
            "path": str(static_dir),
            "files": file_count,
            "size_mb": round(total_size / 1024 / 1024, 2)
        }
    except Exception:
        return {
            "available": False,
            "path": str(static_dir),
            "files": 0,
            "size_mb": 0
        }


def setup_studio_routes_with_static(app: FastAPI) -> bool:
    """
    Setup Aurite Studio routes with static file serving.
    
    This is the main function to call when setting up the FastAPI app
    to serve Aurite Studio as static files.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        True if setup was successful, False otherwise
    """
    if not is_static_assets_available():
        return False
    
    # Setup static file serving at /studio
    success = setup_static_serving(app, "/studio")
    
    if success:
        # Add a redirect from root to studio (optional)
        @app.get("/")
        async def redirect_to_studio():
            """Redirect root to studio interface."""
            return HTMLResponse(
                content='<script>window.location.href="/studio";</script>',
                status_code=200
            )
    
    return success
