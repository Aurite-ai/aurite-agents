Rules & Violations¶

deptry checks your project against the following rules related to dependencies:
Code 	Description 	More information
DEP001 	Project should not contain missing dependencies 	link
DEP002 	Project should not contain unused dependencies 	link
DEP003 	Project should not use transitive dependencies 	link
DEP004 	Project should not use development dependencies in non-development code 	link
DEP005 	Project should not contain dependencies that are in the standard library 	link

Any of the checks can be disabled with the ignore flag. Specific dependencies or modules can be ignored with the per-rule-ignores flag.
Missing dependencies (DEP001)¶

Python modules that are imported within a project, for which no corresponding packages are found in the dependencies.
Example¶

On a project with the following dependencies:

[project]
dependencies = []

and the following main.py that is the only Python file in the project:

import httpx

def make_http_request():
    return httpx.get("https://example.com")

deptry will report httpx as a missing dependency because it is imported in the project, but not defined in the dependencies.

To fix the issue, httpx should be added to [project.dependencies]:

[project]
dependencies = ["httpx==0.23.1"]

Unused dependencies (DEP002)¶

Dependencies that are required in a project, but are not used within the codebase.

Note

Development dependencies are not considered for this rule, as they are usually meant to only be used outside the codebase (for instance in tests, or as CLI tools for type-checking, formatting, etc.).
Example¶

On a project with the following dependencies:

[project]
dependencies = [
    "httpx==0.23.1",
    "requests==2.28.1",
]

and the following main.py that is the only Python file in the project:

import httpx
import requests

def make_http_request():
    return httpx.get("https://example.com")

deptry will report requests as an unused dependency because it is not used in the project.

To fix the issue, requests should be removed from [project.dependencies]:

[project]
dependencies = ["httpx==0.23.1"]

Transitive dependencies (DEP003)¶

Python modules that are imported within a project, where the corresponding dependencies are in the dependency tree, but not as direct dependencies. For example, assume your project has a .py file that imports module A. However, A is not in your project's dependencies. Instead, another package (B) is in your list of dependencies, which in turn depends on A. Package A should be explicitly added to your project's list of dependencies.
Example¶

On a project with the following dependencies:

[project]
dependencies = [
    # Here `httpx` depends on `certifi` package.
    "httpx==0.23.1",
]

and the following main.py that is the only Python file in the project:

import certifi
import httpx

def make_http_request():
    return httpx.get("https://example.com")

def get_certificates_location():
    return certifi.where()

deptry will report certifi as a transitive dependency because it is used in the project, but not defined as a direct dependency, and is only present in the dependency tree because another dependency depends on it.

To fix the issue, certifi should be explicitly added to [project.dependencies]:

[project]
dependencies = [
    "certifi==2024.7.4",
    "httpx==0.23.1",
]

Misplaced development dependencies (DEP004)¶

Dependencies specified as development ones that should be included as regular dependencies.
Example¶

On a project with the following dependencies:

[project]
dependencies = ["httpx==0.23.1"]

[tool.pdm.dev-dependencies]
test = [
    "orjson==3.8.3",
    "pytest==7.2.0",
]

And the following main.py that is the only Python file in the project:

import httpx
import orjson

def make_http_request():
    return httpx.get("https://example.com")

def dump_json():
    return orjson.dumps({"foo": "bar"})

deptry will report orjson as a misplaced development dependency because it is used in non-development code.

To fix the issue, orjson should be moved from [tool.pdm.dev-dependencies] to [project.dependencies]:

[project]
dependencies = [
    "httpx==0.23.1",
    "orjson==3.8.3",
]

[tool.pdm.dev-dependencies]
test = ["pytest==7.2.0"]

Standard library dependencies (DEP005)¶

Dependencies that are part of the Python standard library should not be defined as dependencies in your project.
Example¶

On a project with the following dependencies:

[project]
dependencies = [
    "asyncio",
]

and the following main.py in the project:

import asyncio

def async_example():
    return asyncio.run(some_coroutine())

deptry will report asyncio as a standard library dependency because it is part of the standard library, yet it is defined as a dependency in the project.

To fix the issue, asyncio should be removed from [project.dependencies]:

[project]
dependencies = []