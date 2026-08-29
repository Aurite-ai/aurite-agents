#!/usr/bin/env python3
"""
Generate JSON schemas from Aurite configuration Pydantic models.

This script generates JSON schemas that can be used by IDEs like VS Code
for validation and autocompletion of YAML/JSON configuration files.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

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


def enhance_path_field(field_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance a Path field's JSON schema representation with validation.

    Args:
        field_schema: The field's schema dictionary

    Returns:
        Enhanced schema with better path validation
    """
    # Pattern for validating file paths:
    # - Must start with a letter, number, dot, or path separator
    # - Can contain letters, numbers, underscores, hyphens, dots, slashes
    # - Spaces are technically allowed but discouraged
    # - No special shell characters like |, <, >, &, ;, $, `, etc.
    # This catches most problematic cases while allowing valid paths
    path_pattern = r"^[a-zA-Z0-9\._\-/\\~][a-zA-Z0-9\._\-/\\ ~]*$"

    # VS Code specific fields for better UX
    pattern_error_msg = (
        "Invalid path format. Avoid special characters like |, <, >, &, ;, $, `. "
        "Spaces are allowed but not recommended - use underscores or hyphens instead."
    )

    # Enhanced description with examples
    enhanced_description = field_schema.get("description", "")
    if enhanced_description and not enhanced_description.endswith("."):
        enhanced_description += "."
    enhanced_description += (
        " Examples: 'mcp_servers/weather_server.py', './scripts/my_server.py', "
        "'~/projects/server.py'. Avoid spaces in paths when possible."
    )

    # If the field can be a path or null, simplify and enhance the schema
    if "anyOf" in field_schema:
        has_path_format = False
        cleaned_types = []

        for type_option in field_schema["anyOf"]:
            # Skip redundant path format entries
            if type_option.get("format") == "path":
                has_path_format = True
                # Keep just one string type with format and pattern
                if not any(t.get("type") == "string" and "format" not in t for t in cleaned_types):
                    cleaned_types.append(
                        {
                            "type": "string",
                            "format": "path",
                            "pattern": path_pattern,
                            "patternErrorMessage": pattern_error_msg,
                            "description": enhanced_description,
                            "markdownDescription": f"**File path** - {enhanced_description}",
                        }
                    )
            elif type_option.get("type") == "string" and not has_path_format:
                # Replace plain string with formatted and validated string
                cleaned_types.append(
                    {
                        "type": "string",
                        "format": "path",
                        "pattern": path_pattern,
                        "patternErrorMessage": pattern_error_msg,
                        "description": enhanced_description,
                        "markdownDescription": f"**File path** - {enhanced_description}",
                    }
                )
                has_path_format = True
            elif type_option.get("type") != "string":
                # Keep non-string types (like null)
                cleaned_types.append(type_option)

        # Update the original description for the overall field
        field_schema["description"] = enhanced_description

        if len(cleaned_types) == 1:
            # If only one type remains, flatten it
            field_schema.update(cleaned_types[0])
            del field_schema["anyOf"]
        elif len(cleaned_types) > 1:
            field_schema["anyOf"] = cleaned_types

    # For direct string types, add path format and pattern
    elif field_schema.get("type") == "string":
        field_schema["format"] = "path"
        field_schema["pattern"] = path_pattern
        field_schema["patternErrorMessage"] = pattern_error_msg
        field_schema["description"] = enhanced_description
        field_schema["markdownDescription"] = f"**File path** - {enhanced_description}"

    return field_schema


def enhance_capabilities_field(field_schema: Dict[str, Any], component_type: str) -> Dict[str, Any]:
    """
    Ensure capabilities fields have proper enum restrictions.

    Args:
        field_schema: The field's schema dictionary
        component_type: The component type (e.g., "mcp_server")

    Returns:
        Enhanced schema with proper enum restrictions
    """
    # For capabilities field in mcp_server/ClientConfig
    if component_type == "mcp_server":
        # The capabilities should be restricted to the same literals as RootConfig
        field_schema["items"] = {"enum": ["tools", "prompts", "resources"], "type": "string"}

    return field_schema


def post_process_schema(schema: Dict[str, Any], component_type: str) -> Dict[str, Any]:
    """
    Post-process a schema to enhance type support.

    Args:
        schema: The generated JSON schema
        component_type: The type of component

    Returns:
        Enhanced schema
    """
    # Process properties
    if "properties" in schema:
        # Enhance server_path field for mcp_server
        if component_type == "mcp_server" and "server_path" in schema["properties"]:
            schema["properties"]["server_path"] = enhance_path_field(schema["properties"]["server_path"])

        # Enhance module_path field for custom_workflow
        if component_type == "custom_workflow" and "module_path" in schema["properties"]:
            schema["properties"]["module_path"] = enhance_path_field(schema["properties"]["module_path"])

        # Enhance capabilities field for mcp_server
        if component_type == "mcp_server" and "capabilities" in schema["properties"]:
            schema["properties"]["capabilities"] = enhance_capabilities_field(
                schema["properties"]["capabilities"], component_type
            )

    return schema


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

    # Apply post-processing to enhance type support
    schema = post_process_schema(schema, component_type)

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

        # Apply post-processing to enhance type support
        schema = post_process_schema(schema, component_type)

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
    logger.info(f"Generating schemas in {schemas_dir}/")

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
        logger.debug(f"Generating schema for {component_type}...")
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
        logger.debug(f"  Saved to {schema_file}")

    # Generate a combined schema for multi-component files
    logger.info("Generating combined schema for multi-component files...")
    multi_schema = generate_multi_component_schema(models_map)

    multi_schema_file = schemas_dir / "aurite_schema.json"
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
            "./schemas/aurite_schema.json": [
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
                "url": "./schemas/aurite_schema.json",
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

    # Merge yaml.schemas (dict)
    if "yaml.schemas" in vscode_settings:
        if "yaml.schemas" not in existing_settings:
            existing_settings["yaml.schemas"] = {}

        # Update with the new combined schema approach
        for schema_path, file_patterns in vscode_settings["yaml.schemas"].items():
            existing_settings["yaml.schemas"][schema_path] = file_patterns

    # Merge json.schemas (list)
    if "json.schemas" in vscode_settings:
        existing_json_schemas = existing_settings.get("json.schemas", [])

        # Build a map by url for easy update
        url_to_schema = {}
        for schema in existing_json_schemas:
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
