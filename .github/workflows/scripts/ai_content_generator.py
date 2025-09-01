#!/usr/bin/env python3
"""
AI Content Generator for Aurite Agents Framework
Generates changelog summaries and GitHub release bodies using Anthropic's Claude API.
"""

import os
import json
import sys
import argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def generate_changelog_summary(changes: str, files: str, api_key: str) -> str:
    """Generate a changelog summary using Claude API."""
    
    prompt = f"""You are analyzing changes for a major release of Aurite Agents Framework, a Python framework for building AI agents with MCP (Model Context Protocol) integration, multi-LLM support, CLI/TUI interfaces, REST API, and web UI.

Based on these recent changes and files:

Recent commits:
{changes}

Modified files:
{files}

Write a 2-3 sentence summary highlighting the most significant improvements in this major release. Focus on user-facing features, architectural improvements, or major capabilities added. Be concise and technical but accessible."""

    return call_claude_api(prompt, api_key, 300, "Major release bringing significant improvements and new capabilities to the Aurite Agents Framework.")


def generate_release_body(version: str, version_type: str, environment: str, changes: str, changelog_section: str, api_key: str) -> str:
    """Generate a GitHub release body using Claude API."""
    
    prompt = f"""You are creating a GitHub release body for Aurite Agents Framework v{version}, a Python framework for building AI agents with MCP (Model Context Protocol) integration, multi-LLM support, CLI/TUI interfaces, REST API, and web UI.

Release Details:
- Version: {version}
- Type: {version_type} release
- Environment: {environment}

Recent commits since last release:
{changes}

Changelog section for this release:
{changelog_section}

Create a compelling GitHub release body that includes:

1. **Brief summary** (1-2 sentences) highlighting the key improvements
2. **What's New** section with 3-5 key features/improvements as bullet points
3. **Installation** section with pip install command
4. **Documentation** section mentioning key docs links
5. **Thanks** section acknowledging contributors (keep generic)

Use markdown formatting. Be professional but engaging. Focus on user benefits and practical improvements."""

    return call_claude_api(prompt, api_key, 600, generate_fallback_release_body(version, version_type, environment))


def call_claude_api(prompt: str, api_key: str, max_tokens: int, fallback: str) -> str:
    """Make API call to Claude and return response or fallback."""
    
    data = {
        'model': 'claude-3-haiku-20240307',
        'max_tokens': max_tokens,
        'messages': [
            {
                'role': 'user', 
                'content': prompt
            }
        ]
    }
    
    try:
        req = Request('https://api.anthropic.com/v1/messages')
        req.add_header('Content-Type', 'application/json')
        req.add_header('x-api-key', api_key)
        req.add_header('anthropic-version', '2023-06-01')
        
        response = urlopen(req, json.dumps(data).encode())
        result = json.loads(response.read().decode())
        
        if 'content' in result and len(result['content']) > 0:
            return result['content'][0]['text'].strip()
        else:
            return fallback
            
    except Exception as e:
        print(f'Error generating AI content: {e}', file=sys.stderr)
        return fallback


def generate_fallback_release_body(version: str, version_type: str, environment: str) -> str:
    """Generate a fallback release body if AI generation fails."""
    
    env_text = "production PyPI" if environment == "prod" else "TestPyPI"
    
    return f"""## Aurite Agents Framework v{version}

We're excited to announce the release of Aurite Agents Framework v{version}, bringing new capabilities and improvements to AI agent development.

### What's New
- Enhanced agent orchestration capabilities
- Improved MCP server integration
- Performance optimizations and bug fixes
- Updated documentation and examples

### Installation
```bash
pip install aurite=={version}
```

### Documentation
- [Getting Started Guide](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/getting-started/package_installation_guide.md)
- [API Reference](https://github.com/Aurite-ai/aurite-agents/blob/main/docs/usage/api_reference.md)
- [Configuration Guides](https://github.com/Aurite-ai/aurite-agents/tree/main/docs/config)

Released to {env_text}
Environment: {environment}
Version Type: {version_type}
Package: aurite-agents=={version}

Thanks to all contributors who made this release possible! 🚀"""


def main():
    parser = argparse.ArgumentParser(description='Generate AI content for releases')
    parser.add_argument('--mode', required=True, choices=['summary', 'release'], 
                       help='Content type to generate (summary for changelog, release for GitHub release)')
    
    # Common arguments
    parser.add_argument('--api-key', help='Anthropic API key (or use ANTHROPIC_API_KEY env var)')
    
    # Summary mode arguments
    parser.add_argument('--changes', help='Recent commit messages (for summary mode)')
    parser.add_argument('--files', help='Modified files (for summary mode)')
    
    # Release mode arguments
    parser.add_argument('--version', help='Release version (for release mode)')
    parser.add_argument('--version-type', help='Version type (major/minor/patch) (for release mode)')
    parser.add_argument('--environment', help='Environment (prod/test) (for release mode)')
    parser.add_argument('--changelog-section', default='', help='Relevant changelog section (for release mode)')
    
    args = parser.parse_args()
    
    # Get API key from argument or environment
    api_key = args.api_key or os.getenv('ANTHROPIC_API_KEY')
    
    if args.mode == 'summary':
        if not args.changes or not args.files:
            print("--changes and --files are required for summary mode", file=sys.stderr)
            sys.exit(1)
        
        if not api_key:
            print('Major release bringing significant improvements and new capabilities to the Aurite Agents Framework.')
            return
        
        summary = generate_changelog_summary(args.changes, args.files, api_key)
        print(summary)
        
    elif args.mode == 'release':
        if not all([args.version, args.version_type, args.environment, args.changes is not None]):
            print("--version, --version-type, --environment, and --changes are required for release mode", file=sys.stderr)
            sys.exit(1)
        
        if not api_key:
            print(generate_fallback_release_body(args.version, args.version_type, args.environment))
            return
        
        release_body = generate_release_body(
            args.version, 
            args.version_type, 
            args.environment, 
            args.changes, 
            args.changelog_section,
            api_key
        )
        print(release_body)


if __name__ == '__main__':
    main()