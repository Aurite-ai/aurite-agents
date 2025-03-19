"""
MCP Server for planning functionality.

This server provides:
1. A planning prompt that guides an LLM to create structured plans
2. Tools for plan management:
   - save_plan: Save a plan to disk with metadata
   - list_plans: List available plans with optional filtering
3. Resources for plan retrieval and analysis
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# MCP imports
from mcp.server.fastmcp import FastMCP, Context

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
PLANS_DIR = Path(__file__).parent / "plans"
PLANS_DIR.mkdir(exist_ok=True)

# Create the MCP server
mcp = FastMCP("Planning Assistant")

# In-memory cache for plans
plans_cache = {}


# Load existing plans into memory
def load_plans():
    """Load all existing plans into memory for faster access"""
    global plans_cache

    logger.info(f"Loading plans from: {PLANS_DIR}")

    if not PLANS_DIR.exists():
        logger.warning(f"Plans directory does not exist: {PLANS_DIR}")
        return

    try:
        # Get all plan files
        plan_files = list(PLANS_DIR.glob("*.txt"))

        for plan_path in plan_files:
            plan_name = plan_path.stem
            metadata_path = PLANS_DIR / f"{plan_name}.meta.json"

            # Load plan content
            with open(plan_path, "r") as f:
                plan_content = f.read()

            # Load metadata if available
            metadata = {}
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    try:
                        metadata = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse metadata for plan: {plan_name}"
                        )

            # Store in cache
            plans_cache[plan_name] = {
                "content": plan_content,
                "metadata": metadata,
                "path": str(plan_path),
            }

        logger.info(f"Loaded {len(plans_cache)} plans into memory")
    except Exception as e:
        logger.error(f"Failed to load plans: {e}")


# Load plans at startup
load_plans()


@mcp.tool()
async def save_plan(
    plan_name: str,
    plan_content: str,
    tags: Optional[List[str]] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Save a plan to disk with optional tags.

    Args:
        plan_name: Name of the plan (without extension)
        plan_content: Content of the plan to save
        tags: Optional tags for categorizing the plan

    Returns:
        Dictionary with results of the operation
    """
    # Sanitize plan name to make it safe for filesystem
    plan_name = plan_name.replace("/", "_").replace("\\", "_")

    # Create plan file path
    plan_path = PLANS_DIR / f"{plan_name}.txt"

    # Create plan metadata
    metadata = {
        "name": plan_name,
        "tags": tags or [],
        "created_at": str(datetime.now()),
    }

    # Save plan content to file
    try:
        logger.info(f"Saving plan: {plan_name}")

        with open(plan_path, "w") as f:
            f.write(plan_content)

        # Also save metadata
        metadata_path = PLANS_DIR / f"{plan_name}.meta.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Update cache
        plans_cache[plan_name] = {
            "content": plan_content,
            "metadata": metadata,
            "path": str(plan_path),
        }

        return {
            "success": True,
            "message": f"Plan '{plan_name}' saved successfully",
            "path": str(plan_path),
        }

    except Exception as e:
        logger.error(f"Error saving plan: {e}")
        return {
            "success": False,
            "message": f"Failed to save plan: {str(e)}",
        }


@mcp.tool()
async def list_plans(tag: Optional[str] = None, ctx: Context = None) -> Dict[str, Any]:
    """
    List all available plans, optionally filtered by tag.

    Args:
        tag: Optional tag to filter plans by

    Returns:
        Dictionary with list of available plans
    """
    try:
        logger.info(f"Listing plans{' with tag: ' + tag if tag else ''}")

        # Filter plans by tag if specified
        if tag:
            filtered_plans = {
                name: plan
                for name, plan in plans_cache.items()
                if tag in plan["metadata"].get("tags", [])
            }
        else:
            filtered_plans = plans_cache

        # Format plan information
        plan_list = []
        for name, plan in filtered_plans.items():
            metadata = plan["metadata"]
            plan_list.append(
                {
                    "name": name,
                    "created_at": metadata.get("created_at", "Unknown"),
                    "tags": metadata.get("tags", []),
                    "path": plan["path"],
                }
            )

        return {"success": True, "plans": plan_list, "count": len(plan_list)}

    except Exception as e:
        logger.error(f"Error listing plans: {e}")
        return {
            "success": False,
            "message": f"Failed to list plans: {str(e)}",
        }


@mcp.prompt("create_plan_prompt")
def create_plan_prompt() -> str:
    """
    Generate a structured planning prompt.

    Returns:
        Structured planning prompt
    """
    # Build the structured prompt
    prompt = """
# Planning Task

You are an AI planning assistant. Your job is to create a detailed, structured plan.

## EXTREMELY IMPORTANT INSTRUCTIONS

- ONLY include the plan content in your response
- DO NOT include meta-commentary or your thinking process
- DO NOT include <thinking> tags or any explanations of your thought process
- DO NOT include phrases like "here's the plan" or "I've created a plan"
- Start directly with the plan content (e.g., "# Plan Title")
- NEVER include any text about saving the plan or what you've created
- DO NOT explain what you just did or will do before or after the plan
- NEVER include any text before the plan title or after the plan content
- Focus on creating specific, actionable steps

Your plan should be realistic, well-structured, and actionable. Include clear steps, timeframes,
resources needed, and success metrics.
"""

    return prompt


@mcp.resource("planning://plan/{plan_name}")
def plan_resource(plan_name: str) -> str:
    """
    Get a saved plan as a formatted resource.

    Args:
        plan_name: Name of the plan to retrieve
    """
    if plan_name not in plans_cache:
        return "# Error\n\nPlan not found. Please check the plan name or create a new plan."

    plan = plans_cache[plan_name]
    metadata = plan["metadata"]

    # Format as markdown
    result = f"# Plan: {plan_name}\n\n"

    # Add metadata
    result += "## Metadata\n\n"
    result += f"- **Created**: {metadata.get('created_at', 'Unknown')}\n"
    if "tags" in metadata and metadata["tags"]:
        result += f"- **Tags**: {', '.join(metadata['tags'])}\n"

    result += "\n## Content\n\n"
    result += plan["content"]

    return result


# Allow direct execution of the server
if __name__ == "__main__":
    mcp.run()
