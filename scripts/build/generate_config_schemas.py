#!/usr/bin/env python3
"""
Generate JSON schemas from Aurite configuration Pydantic models.

This script generates JSON schemas that can be used by IDEs like VS Code
for validation and autocompletion of YAML/JSON configuration files.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

# Add the src directory to the path to ensure we import from local source
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import all the configuration models
from aurite.lib.models.config.components import (
    AgentConfig,
    ClientConfig,
    CustomWorkflowConfig,
    EvaluationConfig,
    GraphWorkflowConfig,
    HostConfig,
    LLMConfig,
    SecurityConfig,
    WorkflowConfig,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def generate_schema_for_model(model_class, component_type: str, include_refs: bool = True) -> Dict[str, Any]:
    """
    Generate a JSON schema for a Pydantic model.

    Args:
        model_class: The Pydantic model class
        component_type: The component type name
        include_refs: Whether to include referenced models in the schema

    Returns:
        JSON schema dictionary
    """
    # Generate base schema from Pydantic model
    # For EvaluationConfig, we need to include EvaluationCase in the schema
    if component_type == "evaluation" and include_refs:
        # Generate schema with all referenced models
        schema = model_class.model_json_schema(mode="validation")
    else:
        schema = model_class.model_json_schema()

    # Add metadata for better IDE experience
    schema["title"] = f"Aurite {component_type.replace('_', ' ').title()} Configuration"
    schema["description"] = f"Configuration schema for {component_type} components in Aurite Agents"

    # Add default values where appropriate
    if "properties" in schema:
        if "type" in schema["properties"]:
            schema["properties"]["type"]["default"] = component_type
            schema["properties"]["type"]["const"] = component_type

    return schema


def generate_multi_component_schema(models_map: Dict[str, type]) -> Dict[str, Any]:
    """
    Generate a schema that supports multiple component types in a single file.

    Args:
        models_map: Mapping of component types to model classes

    Returns:
        JSON schema dictionary supporting multiple component types
    """
    # Create schemas for each component type
    component_schemas = []
    definitions = {}

    for component_type, model_class in models_map.items():
        # Generate schema for each model
        schema = model_class.model_json_schema(mode="validation")

        # Ensure the type field is set correctly
        if "properties" in schema and "type" in schema["properties"]:
            schema["properties"]["type"]["const"] = component_type

        # Collect definitions if they exist
        if "$defs" in schema:
            definitions.update(schema["$defs"])
            # Remove $defs from individual schemas as we'll put them at the root level
            del schema["$defs"]

        component_schemas.append(schema)

    # Create a combined schema using oneOf
    multi_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Aurite Configuration File",
        "description": "Configuration file for Aurite Agents components",
        "oneOf": [
            {
                "type": "array",
                "items": {"oneOf": component_schemas},
                "description": "Array of component configurations",
            },
            {"oneOf": component_schemas, "description": "Single component configuration"},
        ],
    }

    # Add collected definitions at the root level
    if definitions:
        multi_schema["$defs"] = definitions

    return multi_schema


def main():
    """Generate JSON schemas for all Aurite configuration types."""

    # Create schemas directory
    schemas_dir = Path("schemas")
    schemas_dir.mkdir(exist_ok=True)
    logger.info(f"Creating schemas in {schemas_dir}/")

    # Map component types to their Pydantic models
    models_map = {
        "agent": AgentConfig,
        "llm": LLMConfig,
        "mcp_server": ClientConfig,
        "host": HostConfig,
        "linear_workflow": WorkflowConfig,
        "graph_workflow": GraphWorkflowConfig,
        "custom_workflow": CustomWorkflowConfig,
        "evaluation": EvaluationConfig,
        "security": SecurityConfig,
    }

    # Generate individual schemas for each component type
    for component_type, model_class in models_map.items():
        logger.info(f"Generating schema for {component_type}...")
        base_schema = generate_schema_for_model(model_class, component_type)

        # Extract definitions if they exist
        definitions = {}
        if "$defs" in base_schema:
            definitions = base_schema["$defs"]
            # Create a copy of base_schema without $defs for use in oneOf
            base_schema_without_defs = {k: v for k, v in base_schema.items() if k != "$defs"}
        else:
            base_schema_without_defs = base_schema

        # Create a schema that supports both single objects and arrays
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": base_schema.get("title", f"Aurite {component_type} Configuration"),
            "description": f"Configuration schema for {component_type} components (supports both single objects and arrays)",
            "oneOf": [
                {
                    "type": "array",
                    "items": base_schema_without_defs,
                    "description": f"Array of {component_type} configurations",
                },
                base_schema_without_defs,
            ],
        }

        # Add definitions at the root level if they exist
        if definitions:
            schema["$defs"] = definitions

        # Save individual schema
        schema_file = schemas_dir / f"aurite_{component_type}_schema.json"
        with open(schema_file, "w") as f:
            json.dump(schema, f, indent=2)
        logger.info(f"  Saved to {schema_file}")

    # Generate a combined schema for multi-component files
    logger.info("Generating combined schema for multi-component files...")
    multi_schema = generate_multi_component_schema(models_map)

    multi_schema_file = schemas_dir / "aurite_combined_schema.json"
    with open(multi_schema_file, "w") as f:
        json.dump(multi_schema, f, indent=2)
    logger.info(f"  Saved to {multi_schema_file}")

    # Generate VS Code settings file
    vscode_dir = Path(".vscode")
    vscode_dir.mkdir(exist_ok=True)

    # Use the combined schema for all potential configuration files
    # The schema will automatically validate based on the "type" field in each component
    vscode_settings = {
        "yaml.schemas": {
            # Apply combined schema to all YAML files that could be Aurite configs
            # Exclude common non-config patterns
            "./schemas/aurite_combined_schema.json": [
                "**/*.yml",
                "**/*.yaml",
                "!**/node_modules/**",
                "!**/.github/**",
                "!**/dist/**",
                "!**/build/**",
                "!**/*.test.yml",
                "!**/*.test.yaml",
                "!**/*.spec.yml",
                "!**/*.spec.yaml",
                "!**/docker-compose*.yml",
                "!**/docker-compose*.yaml",
                "!**/.gitlab-ci.yml",
                "!**/.travis.yml",
                "!**/mkdocs.yml",
                "!**/pyproject.toml",
            ]
        },
        "json.schemas": [
            {
                # Apply combined schema to all JSON files that could be Aurite configs
                # Exclude common non-config patterns
                "fileMatch": [
                    "**/*.json",
                    "!**/node_modules/**",
                    "!**/package.json",
                    "!**/package-lock.json",
                    "!**/tsconfig.json",
                    "!**/jsconfig.json",
                    "!**/.vscode/**",
                    "!**/dist/**",
                    "!**/build/**",
                    "!**/*.test.json",
                    "!**/*.spec.json",
                    "!**/coverage/**",
                ],
                "url": "./schemas/aurite_combined_schema.json",
            }
        ],
    }
    vscode_settings_file = vscode_dir / "settings.json"

    # Load existing settings if present, otherwise start with empty dict
    existing_settings = {}
    if vscode_settings_file.exists():
        with open(vscode_settings_file, "r") as f:
            content = f.read()
            try:
                existing_settings = json.loads(content)
                logger.info(f"Loaded existing VS Code settings from {vscode_settings_file}")
            except json.JSONDecodeError as e:
                logger.warning(f"Existing VS Code settings file has invalid JSON: {e}")
                logger.warning("Creating backup at .vscode/settings.json.backup")
                # Create a backup of the invalid file
                backup_file = vscode_dir / "settings.json.backup"
                with open(backup_file, "w") as backup_f:
                    backup_f.write(content)

    # Merge yaml.schemas (dict) - remove old patterns and add new combined schema
    if "yaml.schemas" in vscode_settings:
        if "yaml.schemas" not in existing_settings:
            existing_settings["yaml.schemas"] = {}

        # Remove old pattern-based schemas
        old_schemas = [
            "./schemas/aurite_agent_schema.json",
            "./schemas/aurite_llm_schema.json",
            "./schemas/aurite_mcp_server_schema.json",
            "./schemas/aurite_linear_workflow_schema.json",
            "./schemas/aurite_evaluation_schema.json",
        ]
        for old_schema in old_schemas:
            if old_schema in existing_settings["yaml.schemas"]:
                del existing_settings["yaml.schemas"][old_schema]

        # Update with the new combined schema approach
        for schema_path, file_patterns in vscode_settings["yaml.schemas"].items():
            existing_settings["yaml.schemas"][schema_path] = file_patterns

    # Merge json.schemas (list) - remove old patterns and add new combined schema
    if "json.schemas" in vscode_settings:
        existing_json_schemas = existing_settings.get("json.schemas", [])

        # Filter out old Aurite-specific schemas
        old_schema_urls = [
            "./schemas/aurite_agent_schema.json",
            "./schemas/aurite_llm_schema.json",
            "./schemas/aurite_mcp_server_schema.json",
            "./schemas/aurite_linear_workflow_schema.json",
            "./schemas/aurite_evaluation_schema.json",
        ]

        # Keep only non-Aurite schemas or non-old Aurite schemas
        filtered_schemas = [schema for schema in existing_json_schemas if schema.get("url") not in old_schema_urls]

        # Build a map by url for easy update
        url_to_schema = {}
        for schema in filtered_schemas:
            url = schema.get("url", "")
            url_to_schema[url] = schema

        # Add our new combined schema
        for schema in vscode_settings["json.schemas"]:
            url = schema.get("url")
            if url:
                url_to_schema[url] = schema

        # Rebuild the list
        existing_settings["json.schemas"] = list(url_to_schema.values())

    # Write merged settings back to file with proper formatting
    with open(vscode_settings_file, "w") as f:
        json.dump(existing_settings, f, indent=2, ensure_ascii=False)
        f.write("\n")  # Add trailing newline for cleaner git diffs
    logger.info(f"Successfully updated VS Code settings in {vscode_settings_file}")

    logger.info("\n✅ Schema generation complete!")
    logger.info("\nTo use the schemas in VS Code:")
    logger.info("1. Install the YAML extension by Red Hat (if not already installed)")
    logger.info("2. Reload VS Code window (Cmd/Ctrl + Shift + P -> 'Developer: Reload Window')")
    logger.info("3. Open any YAML/JSON config file to see validation and autocomplete in action!")

    return 0


if __name__ == "__main__":
    exit(main())
