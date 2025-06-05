from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from pathlib import Path
import importlib.resources
import typer  # Though not used directly in this file, good for consistency if we add CLI elements here later

# Configure basic logging for this module
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_static_ui_path() -> Path:
    """
    Retrieves the path to the packaged 'aurite/static_ui' directory
    where frontend assets are expected.
    """
    try:
        static_ui_path = importlib.resources.files("aurite").joinpath(
            "packaged/static_ui"
        )
        if not static_ui_path.exists():
            # Fallback to the source directory if packaged path doesn't exist
            static_ui_path = importlib.resources.files("aurite").joinpath("static_ui")
        if not static_ui_path.is_dir():
            logger.warning(
                f"Packaged static UI directory not found at {static_ui_path}. "
                "Ensure 'frontend/dist' contents were copied to 'src/aurite/static_ui' before build, "
                "and 'recursive-include src/aurite/static_ui *' is in MANIFEST.in."
            )
        return static_ui_path
    except Exception as e:
        logger.error(f"Error locating 'aurite/static_ui' path: {e}")
        raise FileNotFoundError(
            "Could not locate the 'aurite/static_ui' directory within the package. "
            "Ensure it's correctly included and accessible."
        ) from e


app = FastAPI(title="Aurite Studio Server")

static_ui_dir = get_static_ui_path()
assets_dir = static_ui_dir / "assets"

if assets_dir.is_dir():
    logger.info(f"Serving static assets from: {assets_dir}")
    app.mount(
        "/assets",
        StaticFiles(directory=assets_dir),
        name="frontend-assets",
    )
else:
    logger.warning(
        f"Frontend assets directory not found at {assets_dir}. "
        "The Studio UI may not load correctly. Ensure the frontend is built and packaged."
    )


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_react_app(full_path: str):  # Parameter name 'full_path' is conventional
    index_path = static_ui_dir / "index.html"
    if not index_path.is_file():
        logger.error(f"index.html not found at {index_path}")
        raise HTTPException(
            status_code=404, detail="index.html not found in frontend distribution."
        )
    return FileResponse(index_path)


def start_studio_server(host: str = "127.0.0.1", port: int = 8080):
    """
    Starts the Uvicorn server for the Aurite Studio.
    """
    # Critical checks before starting the server
    current_static_ui_dir = get_static_ui_path()  # Re-call for fresh path
    index_html_path = current_static_ui_dir / "index.html"
    assets_path = current_static_ui_dir / "assets"

    if not current_static_ui_dir.is_dir():
        print(f"Error: Static UI directory not found at '{current_static_ui_dir}'.")
        print(
            "Please ensure 'frontend/dist/*' was copied to 'src/aurite/static_ui/' before building."
        )
        raise typer.Exit(code=1)

    if not index_html_path.is_file():
        print(
            f"Error: 'index.html' not found in static UI directory at '{index_html_path}'."
        )
        print(
            "Please ensure 'frontend/dist/index.html' was copied to 'src/aurite/static_ui/'."
        )
        raise typer.Exit(code=1)

    if not assets_path.is_dir():
        print(
            f"Error: 'assets' directory not found in static UI directory at '{assets_path}'."
        )
        print(
            "Please ensure 'frontend/dist/assets/' was copied to 'src/aurite/static_ui/'."
        )
        raise typer.Exit(code=1)

    logger.info(f"Attempting to start Aurite Studio server at http://{host}:{port}")
    logger.info(f"Serving frontend from: {current_static_ui_dir}")

    # Uvicorn will use the 'app' instance defined globally in this module.
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    # This allows running the studio server directly for testing, e.g., python -m aurite.cli.studio_server
    # However, the primary entry point will be via the 'aurite studio' CLI command.
    print("Starting Aurite Studio server directly for testing...")
    start_studio_server()
