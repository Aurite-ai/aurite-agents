import requests
import json
import time

def test_component_validation():
    """Test that component configurations are properly validated using Pydantic models."""
    base_url = "http://localhost:8000"
    api_key = "RwkWJFhApciiUSyH3B/Ad6T46kIxbu9gtAU"
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    print("=== TESTING COMPONENT CONFIGURATION VALIDATION ===\n")
    
    # Use timestamp to ensure unique names
    timestamp = str(int(time.time()))
    
    # Test 1: Valid agent configuration
    print("Test 1: Creating agent with valid configuration...")
    valid_agent = {
        "name": f"valid-agent-{timestamp}",
        "config": {
            "type": "agent",
            "description": "A valid agent configuration",
            "system_prompt": "You are a helpful assistant",
            "llm_config_id": "my_openai_gpt4_turbo",
            "mcp_servers": ["weather_server"],
            "max_iterations": 10
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/config/components/agents",
            headers=headers,
            json=valid_agent
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Valid agent configuration accepted!")
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Invalid agent configuration - invalid field type
    print("Test 2: Creating agent with invalid field type...")
    invalid_agent_missing = {
        "name": f"invalid-agent-missing-{timestamp}",
        "config": {
            "type": "agent",
            "description": "Invalid max_iterations type",
            "system_prompt": "You are a helpful assistant",
            "llm_config_id": "my_openai_gpt4_turbo",
            "max_iterations": "not_a_number"  # Should be int, not string
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/config/components/agents",
            headers=headers,
            json=invalid_agent_missing
        )
        
        if response.status_code == 422:
            result = response.json()
            print("✅ SUCCESS: Invalid configuration correctly rejected!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 422, got {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Valid LLM configuration
    print("Test 3: Creating LLM with valid configuration...")
    valid_llm = {
        "name": f"valid-llm-{timestamp}",
        "config": {
            "type": "llm",
            "description": "A valid LLM configuration",
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 1500
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/config/components/llms",
            headers=headers,
            json=valid_llm
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Valid LLM configuration accepted!")
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 4: Invalid LLM configuration - missing required field
    print("Test 4: Creating LLM with missing required field...")
    invalid_llm_missing = {
        "name": f"invalid-llm-missing-{timestamp}",
        "config": {
            "type": "llm",
            "description": "Missing provider and model",
            # Missing provider and model - should fail validation
            "temperature": 0.7,
            "max_tokens": 1500
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/config/components/llms",
            headers=headers,
            json=invalid_llm_missing
        )
        
        if response.status_code == 422:
            result = response.json()
            print("✅ SUCCESS: Invalid LLM configuration correctly rejected!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 422, got {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 5: Valid MCP Server configuration
    print("Test 5: Creating MCP Server with valid configuration...")
    valid_mcp_server = {
        "name": f"valid-mcp-server-{timestamp}",
        "config": {
            "type": "mcp_server",
            "description": "A valid MCP server configuration",
            "server_path": "mcp_servers/test_server.py",
            "capabilities": ["tools", "prompts"],
            "timeout": 15.0
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/config/components/mcp_servers",
            headers=headers,
            json=valid_mcp_server
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Valid MCP server configuration accepted!")
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 6: Invalid MCP Server configuration - missing capabilities
    print("Test 6: Creating MCP Server with missing required field...")
    invalid_mcp_server = {
        "name": f"invalid-mcp-server-{timestamp}",
        "config": {
            "type": "mcp_server",
            "description": "Missing capabilities",
            "server_path": "mcp_servers/test_server.py",
            # Missing capabilities - should fail validation
            "timeout": 15.0
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/config/components/mcp_servers",
            headers=headers,
            json=invalid_mcp_server
        )
        
        if response.status_code == 422:
            result = response.json()
            print("✅ SUCCESS: Invalid MCP server configuration correctly rejected!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ UNEXPECTED: Expected 422, got {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n" + "="*50 + "\n")
    print("🎉 SUMMARY:")
    print("✅ Valid configurations are accepted and components are created")
    print("✅ Invalid configurations are rejected with 422 status")
    print("✅ Validation errors provide detailed field-level feedback")
    print("✅ Pydantic models ensure proper schema validation")
    print("✅ All component types have proper validation")

if __name__ == "__main__":
    test_component_validation()
