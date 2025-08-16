#!/usr/bin/env python3
"""
Build frontend packages for distribution with the Python package.

This script builds the React frontend and copies the static assets
to the appropriate location in the Python package structure.

Enhanced for CI/CD environments with better error reporting and validation.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def check_node_dependencies():
    """Check if Node.js and npm are available."""
    try:
        subprocess.run(["node", "--version"], check=True, capture_output=True)
        subprocess.run(["npm", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_frontend_dependencies(frontend_dir: Path):
    """Install frontend dependencies if needed."""
    print("📦 Installing frontend dependencies...")
    
    try:
        # Install root dependencies
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
        print("✅ Frontend dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install frontend dependencies: {e}")
        return False


def build_react_app(frontend_dir: Path):
    """Build the React app for production."""
    print("🏗️  Building React app for production...")
    
    try:
        # Build all packages (this includes the api-client and aurite-studio)
        subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
        print("✅ React app built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build React app: {e}")
        return False


def copy_built_assets(build_dir: Path, target_dir: Path):
    """Copy built assets to the Python package directory."""
    print(f"📁 Copying built assets from {build_dir} to {target_dir}...")
    
    if not build_dir.exists():
        print(f"❌ Build directory does not exist: {build_dir}")
        return False
    
    try:
        # Remove existing static directory if it exists
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        # Copy built assets
        shutil.copytree(build_dir, target_dir)
        print(f"✅ Built assets copied to {target_dir}")
        
        # Verify key files exist
        index_file = target_dir / "index.html"
        if not index_file.exists():
            print("⚠️  Warning: index.html not found in built assets")
            return False
        
        static_dir = target_dir / "static"
        if not static_dir.exists():
            print("⚠️  Warning: static directory not found in built assets")
            return False
        
        print("✅ Built assets verification passed")
        return True
        
    except Exception as e:
        print(f"❌ Failed to copy built assets: {e}")
        return False


def verify_build_output(target_dir: Path):
    """Verify the build output contains expected files."""
    print("🔍 Verifying build output...")
    
    required_files = [
        "index.html",
        "static/js",
        "static/css"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = target_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    # Check file sizes
    index_size = (target_dir / "index.html").stat().st_size
    if index_size < 100:  # Very small index.html might indicate a problem
        print(f"⚠️  Warning: index.html is very small ({index_size} bytes)")
    
    print("✅ Build output verification passed")
    return True


def build_frontend_for_package():
    """Main function to build frontend for package distribution."""
    print("🚀 Starting frontend build for package distribution...")
    
    # Define paths
    project_root = Path(__file__).parent.parent
    frontend_dir = project_root / "frontend"
    build_dir = frontend_dir / "packages" / "aurite-studio" / "build"
    target_dir = project_root / "src" / "aurite" / "bin" / "studio" / "static"
    
    print(f"Project root: {project_root}")
    print(f"Frontend directory: {frontend_dir}")
    print(f"Build directory: {build_dir}")
    print(f"Target directory: {target_dir}")
    
    # Check prerequisites
    if not check_node_dependencies():
        print("❌ Node.js and npm are required but not found")
        print("Please install Node.js (>= 18.0.0) from https://nodejs.org/")
        return False
    
    if not frontend_dir.exists():
        print(f"❌ Frontend directory not found: {frontend_dir}")
        return False
    
    # Install dependencies
    if not install_frontend_dependencies(frontend_dir):
        return False
    
    # Build React app
    if not build_react_app(frontend_dir):
        return False
    
    # Copy built assets
    if not copy_built_assets(build_dir, target_dir):
        return False
    
    # Verify build output
    if not verify_build_output(target_dir):
        return False
    
    print("🎉 Frontend build for package distribution completed successfully!")
    print(f"📦 Static assets are ready at: {target_dir}")
    
    # Print summary
    total_size = sum(f.stat().st_size for f in target_dir.rglob('*') if f.is_file())
    file_count = len(list(target_dir.rglob('*')))
    print(f"📊 Build summary: {file_count} files, {total_size / 1024 / 1024:.2f} MB total")
    
    return True


if __name__ == "__main__":
    success = build_frontend_for_package()
    sys.exit(0 if success else 1)
