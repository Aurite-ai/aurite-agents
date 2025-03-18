"""
MCP Server for planning functionality.

This server provides:
1. A planning prompt that guides an LLM to create structured plans
2. A tool to save plans to disk for later reference
3. A resource to retrieve saved plans
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

# Path to store plans
PLANS_DIR = Path(__file__).parent / "plans"
PLANS_DIR.mkdir(exist_ok=True)

# Create the MCP server
mcp = FastMCP("Planning Assistant")

# Dictionary to store plans in memory (for faster access)
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
def save_plan(
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
        ctx.info(f"Saving plan: {plan_name}")

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
def list_plans(tag: Optional[str] = None, ctx: Context = None) -> Dict[str, Any]:
    """
    List all available plans, optionally filtered by tag.

    Args:
        tag: Optional tag to filter plans by

    Returns:
        Dictionary with list of available plans
    """
    try:
        ctx.info(f"Listing plans{' with tag: ' + tag if tag else ''}")

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


@mcp.prompt()
def planning_prompt(task: str, timeframe: str = None, resources: str = None) -> str:
    """
    Generate a structured planning prompt.

    Args:
        task: The task to create a plan for
        timeframe: Optional timeframe for the plan (e.g., '1 day', '1 week', '1 month')
        resources: Optional comma-separated list of available resources

    Returns:
        Structured planning prompt
    """
    # Build the structured prompt
    prompt = f"""
# Planning Task

You are an AI planning assistant. Your job is to create a detailed, structured plan for the following task:

## Task Description
{task}

"""
    # Add timeframe if provided
    if timeframe:
        prompt += f"""
## Timeframe
{timeframe}
"""

    # Add resources if provided
    if resources:
        # Convert comma-separated string to list of bullet points
        resources_list = [r.strip() for r in resources.split(",")]
        resources_text = "\n".join(
            [f"- {resource}" for resource in resources_list if resource]
        )

        if resources_text:
            prompt += f"""
## Available Resources
{resources_text}
"""

    # Add standard planning structure
    prompt += """
## Planning Guidelines

Create a structured plan that includes:

1. **Objective**: Clear statement of the goal and success criteria
2. **Key Steps**: Ordered list of major steps to accomplish the task
3. **Timeline**: Estimated time for each step
4. **Dependencies**: Any dependencies between steps
5. **Resources Required**: What's needed for each step
6. **Potential Challenges**: Risks and mitigation strategies
7. **Success Metrics**: How to measure if the plan succeeded

Your plan should be realistic, well-structured, and actionable.
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


@mcp.prompt()
def plan_analysis_prompt(plan_name: str = "") -> str:
    """
    Create a prompt for analyzing an existing plan.

    Args:
        plan_name: Name of the plan to analyze
    """
    if plan_name and plan_name in plans_cache:
        return f"""I'd like to analyze the existing plan named "{plan_name}".

Please help me:
1. Review the plan structure and content
2. Identify any gaps or inconsistencies
3. Suggest improvements to the plan
4. Evaluate if the plan is realistic and achievable
5. Consider potential risks that might not be addressed

You can access the full plan using the planning://plan/{plan_name} resource.
"""
    else:
        return """I'd like to analyze an existing plan.

Please first list the available plans using the list_plans tool, then I'll select one for analysis.
"""


# Allow direct execution of the server
if __name__ == "__main__":
    mcp.run()
