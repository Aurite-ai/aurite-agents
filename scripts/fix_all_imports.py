#!/usr/bin/env python3
"""
Script to fix all incorrect config_models imports throughout the codebase.
"""

import os
import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix config_models imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern 1: from aurite.lib.config.config_models import ...
        content = re.sub(
            r'from aurite\.lib\.config\.config_models import',
            'from aurite.lib.models.config.components import',
            content
        )
        
        # Pattern 2: from src.aurite.lib.config.config_models import ...
        content = re.sub(
            r'from src\.aurite\.lib\.config\.config_models import',
            'from src.aurite.lib.models.config.components import',
            content
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed imports in: {file_path}")
            return True
        else:
            print(f"⏭️  No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Fix all config_models imports in the codebase."""
    print("🔧 Fixing all config_models imports...")
    
    # Files that need fixing based on the search results
    files_to_fix = [
        "tests/fixtures/fixture_custom_workflow.py",
        "tests/fixtures/workflow_fixtures.py", 
        "tests/fixtures/fixture_agents.py",
        "tests/fixtures/workspace/project_alpha/run_example_project.py",
        "tests/fixtures/workspace/project_bravo/run_example_project.py",
        "tests/integration/mcp_servers/test_local.py",
        "tests/integration/agent/test_agent_integration.py",
        "tests/integration/mcp_servers/test_error.py",
        "tests/integration/agent/test_agent_turn_processor.py",
        "tests/integration/mcp_servers/test_http.py",
        "tests/integration/mcp_servers/test_stdio.py",
        "tests/integration/host/test_mcp_host.py",
        "tests/integration/llm/test_litellm_client_integration.py",
        "tests/unit/llm/test_litellm_client.py",
        "tests/unit/host/test_root_manager.py"
    ]
    
    fixed_count = 0
    total_count = len(files_to_fix)
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_imports_in_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\n📊 Summary: Fixed {fixed_count} out of {total_count} files")
    
    if fixed_count > 0:
        print("🎉 Import fixes completed successfully!")
    else:
        print("ℹ️  No files needed fixing.")

if __name__ == "__main__":
    main()
