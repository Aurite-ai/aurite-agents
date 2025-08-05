#!/usr/bin/env python3
"""
Test script to verify that the import fix resolves the ModuleNotFoundError.
This script tests the specific functionality that was failing.
"""

import requests
import json
import sys

def test_linear_workflow_creation():
    """Test creating a linear workflow via the API endpoint that was failing."""
    
    # API endpoint that was failing
    url = "http://127.0.0.1:8000/config/components/linear_workflow"
    
    # Sample linear workflow configuration
    test_workflow = {
        "name": "test_workflow_import_fix",
        "description": "Test workflow to verify import fix",
        "steps": ["agent1", "agent2"]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("Testing POST /config/components/linear_workflow...")
        print(f"Payload: {json.dumps(test_workflow, indent=2)}")
        
        response = requests.post(url, json=test_workflow, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Import fix worked! API endpoint is now functional.")
            return True
        elif response.status_code == 500:
            print("❌ FAILED: Still getting 500 error. Import fix may not have resolved the issue.")
            return False
        else:
            print(f"⚠️  UNEXPECTED: Got status code {response.status_code}. This may be a different issue.")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR: Could not connect to the API server.")
        print("Make sure the Aurite API server is running on http://127.0.0.1:8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: Request timed out.")
        return False
    except Exception as e:
        print(f"❌ ERROR: Unexpected error occurred: {e}")
        return False

def test_import_directly():
    """Test the import directly to verify it works."""
    try:
        print("Testing direct import of config models...")
        from aurite.lib.models.config.components import AgentConfig, ClientConfig, CustomWorkflowConfig, LLMConfig, WorkflowConfig
        print("✅ SUCCESS: Direct import of config models works!")
        return True
    except ImportError as e:
        print(f"❌ FAILED: Direct import still fails: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Unexpected error during import: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Import Fix for ModuleNotFoundError")
    print("=" * 60)
    
    # Test 1: Direct import
    print("\n1. Testing direct import...")
    import_success = test_import_directly()
    
    # Test 2: API endpoint
    print("\n2. Testing API endpoint...")
    api_success = test_linear_workflow_creation()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Direct Import: {'✅ PASS' if import_success else '❌ FAIL'}")
    print(f"API Endpoint:  {'✅ PASS' if api_success else '❌ FAIL'}")
    
    if import_success and api_success:
        print("\n🎉 ALL TESTS PASSED! The import fix is working correctly.")
        sys.exit(0)
    elif import_success:
        print("\n⚠️  Import works but API may have other issues. Check if server is running.")
        sys.exit(1)
    else:
        print("\n❌ Import fix did not resolve the issue. Further investigation needed.")
        sys.exit(1)
