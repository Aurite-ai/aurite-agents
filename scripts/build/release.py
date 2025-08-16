#!/usr/bin/env python3
"""
Streamlined release script for Aurite framework.

This script automates the local preparation steps for a new release:
1. Updates version in pyproject.toml
2. Builds frontend assets
3. Runs tests
4. Builds Python package
5. Tests wheel installation
6. Commits changes and creates git tag

Usage:
    python scripts/release.py 0.3.27
    python scripts/release.py patch  # Auto-increment patch version
    python scripts/release.py minor  # Auto-increment minor version
    python scripts/release.py major  # Auto-increment major version
"""

import subprocess
import sys
import re
from pathlib import Path

def run_command(cmd, check=True, capture_output=True):
    """Run command and return result."""
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(
        cmd, 
        shell=True, 
        capture_output=capture_output, 
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    if check and result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        sys.exit(1)
    
    if capture_output and result.stdout.strip():
        print(f"   Output: {result.stdout.strip()}")
    
    return result

def get_current_version():
    """Get current version from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    match = re.search(r'version = "([^"]+)"', content)
    if match:
        return match.group(1)
    else:
        print("❌ Could not find version in pyproject.toml")
        sys.exit(1)

def increment_version(current_version, increment_type):
    """Increment version based on type (patch, minor, major)."""
    parts = current_version.split('.')
    if len(parts) != 3:
        print(f"❌ Invalid version format: {current_version}")
        sys.exit(1)
    
    major, minor, patch = map(int, parts)
    
    if increment_type == "patch":
        patch += 1
    elif increment_type == "minor":
        minor += 1
        patch = 0
    elif increment_type == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        print(f"❌ Invalid increment type: {increment_type}")
        sys.exit(1)
    
    return f"{major}.{minor}.{patch}"

def validate_version(version):
    """Validate version format."""
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        print(f"❌ Invalid version format: {version}")
        print("   Expected format: X.Y.Z (e.g., 0.3.27)")
        sys.exit(1)

def check_git_status():
    """Check if git working directory is clean."""
    result = run_command("git status --porcelain", check=False)
    if result.stdout.strip():
        print("⚠️  Warning: Git working directory is not clean")
        print("   Uncommitted changes:")
        for line in result.stdout.strip().split('\n'):
            print(f"   {line}")
        
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            print("❌ Aborted")
            sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/release.py <version|patch|minor|major>")
        print("Examples:")
        print("  python scripts/release.py 0.3.27")
        print("  python scripts/release.py patch")
        print("  python scripts/release.py minor")
        print("  python scripts/release.py major")
        sys.exit(1)
    
    version_input = sys.argv[1]
    
    print("🚀 Aurite Framework Release Script")
    print("=" * 40)
    
    # Determine target version
    current_version = get_current_version()
    print(f"📋 Current version: {current_version}")
    
    if version_input in ["patch", "minor", "major"]:
        target_version = increment_version(current_version, version_input)
        print(f"📈 Auto-incrementing {version_input}: {current_version} → {target_version}")
    else:
        target_version = version_input
        validate_version(target_version)
        print(f"🎯 Target version: {target_version}")
    
    # Check git status
    print("\n📋 Checking git status...")
    check_git_status()
    
    # Update version
    print(f"\n📝 Updating version to {target_version}...")
    run_command(f"poetry version {target_version}")
    
    # Build frontend
    print("\n🏗️  Building frontend assets...")
    run_command("python scripts/build_frontend_for_package.py")
    
    # Run tests
    print("\n🧪 Running tests...")
    run_command("poetry run pytest tests/unit/ -v --tb=short")
    
    # Build package
    print("\n📦 Building Python package...")
    run_command("poetry build")
    
    # Test wheel installation
    print("\n🔍 Testing wheel installation...")
    run_command("python scripts/test_wheel_install.py")
    
    # Test static asset detection
    print("\n🔍 Testing static asset detection...")
    run_command("python scripts/test_static_detection.py")
    
    # Commit and tag
    print(f"\n📝 Committing changes and creating tag v{target_version}...")
    run_command("git add .")
    run_command(f'git commit -m "Release v{target_version}"')
    run_command(f"git tag v{target_version}")
    
    print("\n" + "=" * 50)
    print(f"✅ Release v{target_version} prepared successfully!")
    print("=" * 50)
    print("\n🚀 To publish to PyPI, run:")
    print(f"   git push origin v{target_version}")
    print("\n📋 This will trigger GitHub Actions to:")
    print("   • Build and test the package")
    print("   • Publish to PyPI")
    print("   • Create GitHub release")
    print("\n🔍 Monitor the release at:")
    print("   https://github.com/Aurite-ai/aurite-agents/actions")
    print("\n📦 Check PyPI after publishing:")
    print("   https://pypi.org/project/aurite/")

if __name__ == "__main__":
    main()
