#!/usr/bin/env python3
"""Check include_history configuration for agents and workflows."""

import json
from pathlib import Path

config_path = Path("tests/fixtures/workspace/shared_configs/example_multi_component.json")

with open(config_path, "r") as f:
    configs = json.load(f)

print("=== Include History Configuration ===\n")

print("Agents:")
for config in configs:
    if config.get("type") == "agent":
        include_history = config.get("include_history", "not set")
        print(f"  - {config['name']}: include_history={include_history}")

print("\nWorkflows:")
for config in configs:
    if config.get("type") == "linear_workflow":
        include_history = config.get("include_history", "not set")
        print(f"  - {config['name']}: include_history={include_history}")
        if "steps" in config:
            print(f"    Steps: {', '.join(config['steps'])}")
