#!/usr/bin/env python3
"""
Test script to verify template injection functionality.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aurite.bin.dependencies import get_server_config
from aurite.bin.studio.static_server import serve_injected_html


def test_template_injection():
    """Test that template injection works correctly."""
    print("🧪 Testing template injection functionality...")

    # Get the static HTML file
    static_dir = Path(__file__).parent / "src" / "aurite" / "bin" / "studio" / "static"
    html_file = static_dir / "index.html"

    if not html_file.exists():
        print(f"❌ Static HTML file not found: {html_file}")
        return False

    print(f"✅ Found static HTML file: {html_file}")

    # Test template injection
    try:
        # Set up a test environment variable
        os.environ["PORT"] = "8003"
        os.environ["API_KEY"] = "test_api_key_12345"

        # Get server config
        server_config = get_server_config()
        print(f"📋 Server config: PORT={server_config.PORT}, API_KEY={server_config.API_KEY}")

        # Test the injection
        response = serve_injected_html(html_file)
        html_content = response.body.decode("utf-8")

        # Check that placeholders were replaced
        if "{{API_KEY}}" in html_content:
            print("❌ API_KEY placeholder was not replaced")
            return False

        if "{{API_BASE_URL}}" in html_content:
            print("❌ API_BASE_URL placeholder was not replaced")
            return False

        if "{{SERVER_PORT}}" in html_content:
            print("❌ SERVER_PORT placeholder was not replaced")
            return False

        # Show a snippet of the injected config for debugging
        start = html_content.find("window.AURITE_CONFIG=")
        end = html_content.find("</script>", start)
        if start != -1 and end != -1:
            config_snippet = html_content[start:end]
            print(f"📄 Injected config: {config_snippet}")

        # Check that values were injected correctly
        if "test_api_key_12345" not in html_content:
            print("❌ API key was not injected correctly")
            return False

        if "http://localhost:8003" not in html_content:
            print("❌ API base URL was not injected correctly")
            return False

        # Check for server port in the config (it might be formatted differently)
        if "8003" not in html_content:
            print("❌ Server port was not injected correctly")
            return False

        print("✅ All template placeholders were replaced correctly!")
        print("✅ API key injection working")
        print("✅ API base URL injection working")
        print("✅ Server port injection working")

        # Show a snippet of the injected config
        start = html_content.find("window.AURITE_CONFIG=")
        end = html_content.find("</script>", start)
        if start != -1 and end != -1:
            config_snippet = html_content[start:end]
            print(f"📄 Injected config: {config_snippet}")

        return True

    except Exception as e:
        print(f"❌ Template injection test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_template_injection()
    sys.exit(0 if success else 1)
