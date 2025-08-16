#!/usr/bin/env python3
"""
Test script to debug static asset detection in the wheel package.
"""

import sys
from pathlib import Path

def test_static_detection():
    """Test if static assets can be detected correctly."""
    
    print("🔍 Testing static asset detection...")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {Path.cwd()}")
    
    try:
        # Import the static server module
        from aurite.bin.studio.static_server import (
            get_static_assets_path,
            is_static_assets_available,
            get_static_assets_info
        )
        
        print("\n📦 Static asset detection results:")
        
        # Test path detection
        static_path = get_static_assets_path()
        print(f"Static assets path: {static_path}")
        
        if static_path:
            print(f"Path exists: {static_path.exists()}")
            print(f"Is directory: {static_path.is_dir()}")
            
            # List contents
            if static_path.exists():
                files = list(static_path.iterdir())
                print(f"Files in static directory: {len(files)}")
                for file in sorted(files)[:10]:  # Show first 10 files
                    print(f"  - {file.name}")
                if len(files) > 10:
                    print(f"  ... and {len(files) - 10} more files")
        
        # Test availability
        available = is_static_assets_available()
        print(f"\nStatic assets available: {available}")
        
        # Get detailed info
        info = get_static_assets_info()
        print(f"Static assets info: {info}")
        
        # Test the specific file that should exist
        if static_path:
            index_file = static_path / "index.html"
            print(f"\nindex.html exists: {index_file.exists()}")
            if index_file.exists():
                print(f"index.html size: {index_file.stat().st_size} bytes")
        
        return available
        
    except ImportError as e:
        print(f"❌ Failed to import aurite modules: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

if __name__ == "__main__":
    success = test_static_detection()
    if success:
        print("\n✅ Static assets detected successfully!")
    else:
        print("\n❌ Static assets not detected!")
    
    sys.exit(0 if success else 1)
