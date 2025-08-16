#!/usr/bin/env python3
"""
Test script to simulate pip wheel installation and test static asset detection.
"""

import subprocess
import sys
import tempfile
import os
from pathlib import Path

def test_wheel_installation():
    """Test installing the wheel and checking static asset detection."""
    
    wheel_path = Path("dist/aurite-0.3.26-py3-none-any.whl").absolute()
    
    if not wheel_path.exists():
        print(f"❌ Wheel file not found: {wheel_path}")
        return False
    
    print(f"🔍 Testing wheel installation: {wheel_path}")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Test directory: {temp_dir}")
        
        # Create a virtual environment
        venv_path = Path(temp_dir) / "test_venv"
        print("🐍 Creating virtual environment...")
        result = subprocess.run([
            sys.executable, "-m", "venv", str(venv_path)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to create venv: {result.stderr}")
            return False
        
        # Determine the python executable path
        if os.name == 'nt':  # Windows
            python_exe = venv_path / "Scripts" / "python.exe"
            pip_exe = venv_path / "Scripts" / "pip.exe"
        else:  # Unix-like
            python_exe = venv_path / "bin" / "python"
            pip_exe = venv_path / "bin" / "pip"
        
        # Install the wheel
        print("📦 Installing wheel package...")
        result = subprocess.run([
            str(pip_exe), "install", str(wheel_path)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to install wheel: {result.stderr}")
            return False
        
        print("✅ Wheel installed successfully!")
        
        # Test static asset detection in the installed package
        print("\n🔍 Testing static asset detection in installed package...")
        
        test_script = '''
import sys
from pathlib import Path

try:
    from aurite.bin.studio.static_server import (
        get_static_assets_path,
        is_static_assets_available,
        get_static_assets_info
    )
    
    print("📦 Static asset detection results:")
    
    # Test path detection
    static_path = get_static_assets_path()
    print(f"Static assets path: {static_path}")
    
    if static_path:
        print(f"Path exists: {static_path.exists()}")
        print(f"Is directory: {static_path.is_dir()}")
        
        # List contents if exists
        if static_path.exists():
            files = list(static_path.iterdir())
            print(f"Files in static directory: {len(files)}")
            for file in sorted(files)[:5]:  # Show first 5 files
                print(f"  - {file.name}")
    
    # Test availability
    available = is_static_assets_available()
    print(f"Static assets available: {available}")
    
    # Get detailed info
    info = get_static_assets_info()
    print(f"Static assets info: {info}")
    
    # Test the specific file that should exist
    if static_path:
        index_file = static_path / "index.html"
        print(f"index.html exists: {index_file.exists()}")
        if index_file.exists():
            print(f"index.html size: {index_file.stat().st_size} bytes")
    
    sys.exit(0 if available else 1)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        
        # Run the test in the virtual environment
        result = subprocess.run([
            str(python_exe), "-c", test_script
        ], capture_output=True, text=True, env={**os.environ, "API_KEY": "dummy"})
        
        print("📋 Test output:")
        print(result.stdout)
        if result.stderr:
            print("⚠️ Errors:")
            print(result.stderr)
        
        success = result.returncode == 0
        
        if success:
            print("\n✅ Static assets detected successfully in wheel package!")
        else:
            print("\n❌ Static assets NOT detected in wheel package!")
            
            # Additional debugging - check what's actually in the installed package
            print("\n🔍 Debugging: Checking installed package structure...")
            debug_script = '''
import aurite.bin.studio.static_server
from pathlib import Path
import os

module_file = aurite.bin.studio.static_server.__file__
print(f"Module file: {module_file}")

module_dir = Path(module_file).parent
print(f"Module directory: {module_dir}")
print(f"Module directory exists: {module_dir.exists()}")

static_dir = module_dir / "static"
print(f"Expected static directory: {static_dir}")
print(f"Static directory exists: {static_dir.exists()}")

if module_dir.exists():
    print("Contents of module directory:")
    for item in sorted(module_dir.iterdir()):
        print(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")

# Check if static directory exists anywhere in the package
package_root = module_dir.parent.parent  # Go up to aurite package root
print(f"Package root: {package_root}")
for root, dirs, files in os.walk(package_root):
    if "static" in dirs:
        static_path = Path(root) / "static"
        print(f"Found static directory at: {static_path}")
        static_files = list(static_path.iterdir())
        print(f"  Contains {len(static_files)} files")
'''
            
            debug_result = subprocess.run([
                str(python_exe), "-c", debug_script
            ], capture_output=True, text=True, env={**os.environ, "API_KEY": "dummy"})
            
            print("🔍 Debug output:")
            print(debug_result.stdout)
            if debug_result.stderr:
                print("Debug errors:")
                print(debug_result.stderr)
        
        return success

if __name__ == "__main__":
    success = test_wheel_installation()
    sys.exit(0 if success else 1)
