# Renamed from VALID_CONFIG_DATA_FULL
VALID_PROJECT_CONFIG_INLINE_DEFS = {
    "name": "TestHostFromJson",
    "clients": [
        {
            "client_id": "client1",
            "server_path": "dummy_server1.py",  # Path relative to project root
            "capabilities": ["tools"],
            "roots": [],
        }
    ],
    "agent_configs": [  # Renamed key
        {
            "name": "Agent1",
            "system_prompt": "Prompt for Agent1",
            "client_ids": ["client1"],
            "model": "model-a",
            "temperature": "0.8",  # String to test conversion
            "max_tokens": "2000",  # String to test conversion
            "max_iterations": "8",  # String to test conversion
            "include_history": "false",  # String to test conversion
        },
        {
            "name": "Agent2",
            "client_ids": [
                "client1",
                "client2",
            ],  # client2 doesn't exist in clients, but that's ok for loading
            "model": "model-b",
            # Other params missing, should use defaults or None
        },
    ],
    "simple_workflow_configs": [  # Renamed key
        {
            "name": "Workflow1",
            "description": "A test workflow",
            "steps": ["Agent1", "Agent2"],  # References agents defined above
        },
        {"name": "WorkflowEmpty", "steps": []},
    ],
    "custom_workflow_configs": [  # Renamed key
        {
            "name": "CustomWF1",
            "module_path": "custom/wf1.py",  # Relative path
            "class_name": "WorkflowClass1",
            "description": "My first custom workflow",
        },
        {
            "name": "CustomWF2_NoDesc",
            "module_path": "another/path/wf2.py",
            "class_name": "MyWF",
        },
    ],
    "llm_configs": [  # Add LLM configs section here as well
        {
            "llm_id": "llm_default",
            "provider": "anthropic",
            "model_name": "claude-3-haiku-20240307",
            "temperature": "0.5",
            "max_tokens": "1024",
            "default_system_prompt": "Default LLM prompt.",
        },
        {
            "llm_id": "llm_opus",
            "provider": "anthropic",
            "model_name": "claude-3-opus-20240229",
        },
    ],
}

VALID_CONFIG_DATA_NO_AGENTS = {
    "name": "TestHostNoAgents",
    "clients": [
        {
            "client_id": "client_no_agent",
            "server_path": "dummy_server_na.py",
            "capabilities": ["prompts"],
            "roots": [],
        }
    ],
    # "agents" key is missing
    # "workflows" key is also missing
}

VALID_CONFIG_DATA_NO_WORKFLOWS = {  # New test case
    "name": "TestHostNoWorkflows",
    "clients": [],
    "agents": [{"name": "AgentOnly"}],
    # "workflows" key is missing
    # "custom_workflows" key is also missing
}

VALID_CONFIG_DATA_NO_CUSTOM_WORKFLOWS = {  # New test case
    "name": "TestHostNoCustomWorkflows",
    "clients": [],
    "agents": [{"name": "AgentOnly"}],
    "workflows": [{"name": "RegularWF", "steps": ["AgentOnly"]}],
    # "custom_workflows" key is missing
}


INVALID_CONFIG_DATA_AGENT_MISSING_NAME = {
    "name": "TestHostInvalidAgent",
    "clients": [],
    "agents": [
        {
            # "name": "AgentMissingName", # Name is missing
            "system_prompt": "This agent is invalid",
            "client_ids": [],
        }
    ],
}

INVALID_CONFIG_DATA_WORKFLOW_MISSING_NAME = {  # New test case
    "name": "TestHostInvalidWorkflow",
    "clients": [],
    "agents": [{"name": "AgentWF"}],
    "workflows": [
        {
            # "name": "WorkflowMissingName", # Name is missing
            "steps": ["AgentWF"]
        }
    ],
}

INVALID_CONFIG_DATA_WORKFLOW_UNKNOWN_AGENT = {  # New test case
    "name": "TestHostWorkflowUnknownAgent",
    "clients": [],
    "agents": [{"name": "KnownAgent"}],
    "workflows": [
        {
            "name": "WorkflowBadStep",
            "steps": ["KnownAgent", "UnknownAgent"],  # References an agent not defined
        }
    ],
}

INVALID_CONFIG_DATA_CUSTOM_WORKFLOW_MISSING_NAME = {
    "name": "TestHostInvalidCustomWF_NoName",
    "clients": [],
    "agents": [],
    "custom_workflows": [
        {
            # "name": "MissingName",
            "module_path": "path/to/file.py",
            "class_name": "MyClass",
        }
    ],
}

INVALID_CONFIG_DATA_CUSTOM_WORKFLOW_MISSING_PATH = {
    "name": "TestHostInvalidCustomWF_NoPath",
    "clients": [],
    "agents": [],
    "custom_workflows": [
        {
            "name": "MissingPath",
            # "module_path": "path/to/file.py",
            "class_name": "MyClass",
        }
    ],
}

INVALID_CONFIG_DATA_CUSTOM_WORKFLOW_MISSING_CLASS = {
    "name": "TestHostInvalidCustomWF_NoClass",
    "clients": [],
    "agents": [],
    "custom_workflows": [
        {
            "name": "MissingClass",
            "module_path": "path/to/file.py",
            # "class_name": "MyClass"
        }
    ],
}


INVALID_CONFIG_DATA_AGENT_BAD_TYPE = {
    "name": "TestHostInvalidAgentType",
    "clients": [],
    "agents": [
        {
            "name": "AgentBadTemp",
            "temperature": "not-a-number",  # Invalid type
        }
    ],
}

# --- LLM Config Test Data ---

VALID_CONFIG_DATA_WITH_LLM = {
    "name": "TestHostWithLLM",
    "clients": [],
    "agents": [],
    "llms": [
        {
            "llm_id": "llm_1",
            "provider": "anthropic",
            "model_name": "claude-3-haiku-20240307",
            "temperature": "0.6",
            "max_tokens": "2048",
        },
        {
            "llm_id": "llm_2_defaults",
            "provider": "anthropic",
            "model_name": "claude-3-sonnet-20240229",
        },
    ],
}

INVALID_CONFIG_DATA_LLM_MISSING_ID = {
    "name": "TestHostInvalidLLM_NoID",
    "clients": [],
    "agents": [],
    "llms": [
        {
            # "llm_id": "missing_id",
            "provider": "anthropic",
            "model_name": "claude-3-haiku-20240307",
        }
    ],
}

INVALID_CONFIG_DATA_LLM_BAD_TYPE = {
    "name": "TestHostInvalidLLM_BadType",
    "clients": [],
    "agents": [],
    "llms": [
        {
            "llm_id": "bad_temp_llm",
            "provider": "anthropic",
            "model_name": "claude-3-haiku-20240307",
            "temperature": "very_high",  # Invalid type
        }
    ],
}

# --- New Individual Component Fixtures ---

VALID_CLIENT_CONFIG_DATA_MINIMAL = {
    "client_id": "test_client_min",
    "server_path": "fixtures/servers/dummy_server.py",  # Relative to project root
    "capabilities": ["tools"],
    "roots": [],
}

VALID_CLIENT_CONFIG_DATA_FULL = {
    "client_id": "test_client_full",
    "server_path": "fixtures/servers/another_dummy_server.py",  # Relative to project root
    "capabilities": ["prompts", "tools"],
    "roots": [{"uri": "file://./test_root", "name": "Test Root", "capabilities": ["read"]}],
    "timeout": 15.0,
    "routing_weight": 0.8,
    "exclude": ["excluded_tool_1"],
    "gcp_secrets": [{"secret_id": "projects/p/secrets/s/versions/l", "env_var_name": "MY_SECRET"}],
}

VALID_LLM_CONFIG_DATA = {
    "llm_id": "test_llm_fixture",
    "provider": "anthropic",
    "model_name": "claude-3-sonnet-20240229",
    "temperature": 0.7,
    "max_tokens": 1500,
    "default_system_prompt": "You are a test LLM.",
}

VALID_AGENT_CONFIG_DATA = {
    "name": "test_agent_fixture",
    "llm_config_id": "test_llm_fixture",
    "client_ids": ["test_client_min"],
    "system_prompt": "This is a test agent.",
    "model": "claude-3-opus-20240229",  # Override
    "temperature": 0.9,
    "max_tokens": 2500,
    "max_iterations": 5,
    "include_history": True,
    "exclude_components": ["excluded_prompt_1"],
}

VALID_SIMPLE_WORKFLOW_CONFIG_DATA = {
    "name": "test_simple_workflow_fixture",
    "description": "A simple test workflow fixture.",
    "steps": ["test_agent_fixture"],
}

VALID_CUSTOM_WORKFLOW_CONFIG_DATA = {
    "name": "test_custom_workflow_fixture",
    "module_path": "fixtures/custom_workflows/dummy_custom_wf.py",  # Relative to project root
    "class_name": "DummyCustomWorkflow",
    "description": "A custom test workflow fixture.",
}

# --- Invalid Individual Component Fixtures ---

INVALID_CLIENT_CONFIG_MISSING_ID = {
    # "client_id": "missing_client_id", # ID is missing
    "server_path": "fixtures/servers/dummy_server.py",
    "capabilities": ["tools"],
    "roots": [],
}

INVALID_AGENT_CONFIG_BAD_TEMP_TYPE = {
    "name": "test_agent_bad_temp",
    "temperature": "not-a-float",  # Invalid type
}


# --- New Project Configuration Fixture with References ---

VALID_PROJECT_CONFIG_WITH_REFS = {
    "name": "TestProjectWithReferences",
    "description": "A project that references external component files.",
    "clients": ["test_client_min", "test_client_full"],  # IDs of client components
    "llm_configs": ["test_llm_fixture"],  # ID of an LLM component
    "agent_configs": ["test_agent_fixture"],  # Name/ID of an agent component
    "simple_workflow_configs": ["test_simple_workflow_fixture"],
    "custom_workflow_configs": ["test_custom_workflow_fixture"],
}
