import datetime
import json
import re
import uuid


def create_postman_environment_from_dotenv(dotenv_path, output_path):
    """
    Reads a .env file, parses its contents, and creates a Postman environment JSON file.

    Args:
        dotenv_path (str): The path to the .env file.
        output_path (str): The path where the output JSON file will be saved.
    """
    values = []
    try:
        with open(dotenv_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line.startswith("#") or not line:
                    continue

                # Use regex to handle potential edge cases like values with '='
                match = re.match(r"^\s*([\w.-]+)\s*=\s*(.*?)?\s*$", line)
                if match:
                    key, value = match.groups()
                    # If value is None (empty), treat it as an empty string
                    value = value or ""
                    values.append({"key": key, "value": value, "enabled": True})
    except FileNotFoundError:
        print(f"Error: The file at {dotenv_path} was not found.")
        return

    postman_env = {
        "id": str(uuid.uuid4()),
        "name": "Aurite Agents Environment",
        "values": values,
        "_postman_variable_scope": "environment",
        "_postman_exported_at": datetime.datetime.utcnow().isoformat() + "Z",
        "_postman_exported_using": "Cline-Agent/1.0",
    }

    with open(output_path, "w") as f:
        json.dump(postman_env, f, indent=4)

    print(f"Successfully created Postman environment file at: {output_path}")


if __name__ == "__main__":
    create_postman_environment_from_dotenv(".env", "postman_environment.json")
