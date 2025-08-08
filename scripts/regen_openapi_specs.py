# scripts/regen_openapi_specs.py
import json
import sys

import requests
import yaml

OPENAPI_URL = "http://localhost:8000/openapi.json"
OUTPUT_YAML_FILE = "openapi.yaml"
OUTPUT_JSON_FILE = "openapi.json"


# Custom string class to represent literal block scalars
class literal_str(str):
    pass


def literal_presenter(dumper, data):
    """Custom presenter for the literal_str class."""
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


# Add the custom presenter to the YAML dumper
yaml.add_representer(literal_str, literal_presenter)


def regenerate_schema():
    """Fetches the OpenAPI schema, saves it as JSON, converts it to YAML, and saves it."""
    print(f"Fetching OpenAPI schema from {OPENAPI_URL}...")
    try:
        response = requests.get(OPENAPI_URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: Could not connect to the server at {OPENAPI_URL}.", file=sys.stderr)
        print(f"Please ensure the Aurite API server is running. Details: {e}", file=sys.stderr)
        sys.exit(1)

    openapi_json = response.json()

    # --- Save JSON ---
    print(f"Writing updated schema to {OUTPUT_JSON_FILE}...")
    try:
        with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(openapi_json, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Add newline at end of file
    except IOError as e:
        print(f"Error: Could not write to {OUTPUT_JSON_FILE}. Details: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Save YAML ---
    print("Converting JSON schema to YAML...")
    # Use the custom literal_str class for the description
    if "description" in openapi_json.get("info", {}):
        openapi_json["info"]["description"] = literal_str(openapi_json["info"]["description"])

    try:
        yaml_string = yaml.dump(
            openapi_json,
            sort_keys=False,
            indent=2,
            allow_unicode=True,
            default_flow_style=False,
        )
    except yaml.YAMLError as e:
        print(f"Error: Failed to convert JSON to YAML. Details: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Writing updated schema to {OUTPUT_YAML_FILE}...")
    try:
        with open(OUTPUT_YAML_FILE, "w", encoding="utf-8") as f:
            f.write(yaml_string)
    except IOError as e:
        print(f"Error: Could not write to {OUTPUT_YAML_FILE}. Details: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nSuccessfully regenerated {OUTPUT_JSON_FILE} and {OUTPUT_YAML_FILE}!")


if __name__ == "__main__":
    regenerate_schema()
