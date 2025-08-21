#!/usr/bin/env python3
"""
Changelog management script for GitHub Actions workflow.
Handles updating and releasing changelog entries.
"""

import os
import re
import sys
from typing import Optional, Dict, Any
import argparse
import logging

class ChangelogError(Exception):
    """Custom exception for changelog operations."""
    pass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class ChangelogManager:
    def __init__(self, changelog_path: str = "CHANGELOG.md"):
        self.changelog_path = changelog_path
        self.changelog_template = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

"""

    def _sanitize_input(self, text: str) -> str:
        """Sanitize input text to prevent injection attacks."""
        if not isinstance(text, str):
            return ""
        # Only remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f]', '', text)
        return sanitized[:500]

    def _validate_section(self, section: str) -> bool:
        """Validate that section is one of the allowed types."""
        allowed_sections = {
            "Added", "Changed", "Deprecated", "Removed", 
            "Fixed", "Security", "Performance", "Documentation",
            "Breaking Changes"
        }
        return section in allowed_sections

    def create_changelog_if_missing(self) -> None:
        """Create changelog file if it doesn't exist."""
        if not os.path.exists(self.changelog_path):
            logger.info(f"Creating {self.changelog_path}")
            with open(self.changelog_path, 'w', encoding='utf-8') as f:
                f.write(self.changelog_template)

    def read_changelog(self) -> str:
        """Read the changelog file."""
        try:
            with open(self.changelog_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Changelog file {self.changelog_path} not found")
            raise ChangelogError("Changelog file missing")
        except PermissionError:
            logger.error("Permission denied reading changelog")
            raise ChangelogError("Permission denied")
        except Exception as e:
            logger.error(f"Error reading changelog: {e}")
            raise ChangelogError(f"Failed to read changelog: {e}")

    def write_changelog(self, content: str) -> None:
        """Write content to changelog file."""
        try:
            with open(self.changelog_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except PermissionError:
            logger.error("Permission denied writing changelog")
            raise ChangelogError("Permission denied")
        except Exception as e:
            logger.error(f"Error writing changelog: {e}")
            raise ChangelogError(f"Failed to write changelog: {e}")

    def add_entry(self, section: str, pr_title: str, pr_author: str, 
                  pr_num: str, pr_url: str) -> bool:
        """Add a new entry to the changelog."""
        # Sanitize all inputs
        section = self._sanitize_input(section)
        pr_title = self._sanitize_input(pr_title)
        pr_author = self._sanitize_input(pr_author)
        pr_num = self._sanitize_input(pr_num)
        pr_url = self._sanitize_input(pr_url)

        # Validate section
        if not self._validate_section(section):
            logger.error(f"Invalid section: {section}")
            return False

        # Validate required fields
        if not all([pr_title, pr_author, pr_num, pr_url]):
            logger.error("Missing required fields for changelog entry")
            return False

        try:
            content = self.read_changelog()
            
            # Format the new entry
            if pr_url.startswith('https://github.com/'):
                new_entry = f"- {pr_title} ([@{pr_author}](https://github.com/{pr_author})) [#{pr_num}]({pr_url})"
            else:
                new_entry = f"- {pr_title} by {pr_author} [#{pr_num}]({pr_url})"
            
            # Find the Unreleased section
            unreleased_pattern = r'(## \[Unreleased\].*?)(?=## \[|\Z)'
            unreleased_match = re.search(unreleased_pattern, content, re.MULTILINE | re.DOTALL)
            
            if not unreleased_match:
                logger.error("Could not find [Unreleased] section")
                return False

            unreleased_content = unreleased_match.group(1)
            
            # Check if the section already exists
            section_pattern = rf'### {re.escape(section)}\n'
            section_match = re.search(section_pattern, unreleased_content)
            
            if section_match:
                # Add to existing section
                lines = unreleased_content.split('\n')
                section_header = f'### {section}'
                for i, line in enumerate(lines):
                    if line == section_header:
                        lines.insert(i + 1, new_entry)
                        break
                # Ensure there's a blank line at the end of unreleased section
                if lines and lines[-1].strip():
                    lines.append('')
                updated_unreleased = '\n'.join(lines)
            else:
                # Create new section
                lines = unreleased_content.split('\n')
                # Find insertion point after [Unreleased] header
                insert_pos = 1
                while insert_pos < len(lines) and not lines[insert_pos].strip():
                    insert_pos += 1
                
                lines.insert(insert_pos, f"### {section}")
                lines.insert(insert_pos + 1, new_entry)
                # Ensure there's a blank line at the end of unreleased section
                if lines and lines[-1].strip():
                    lines.append('')
                updated_unreleased = '\n'.join(lines)

            # Update the content
            content = content.replace(unreleased_content, updated_unreleased)
            self.write_changelog(content)
            
            logger.info(f"Successfully added entry to {section} section")
            return True
            
        except ChangelogError:
            return False
        except Exception as e:
            logger.error(f"Unexpected error adding changelog entry: {e}")
            return False

    def release_version(self, new_version: str, current_version: str, 
                       date: str, repo: str) -> bool:
        """Release a new version by converting Unreleased to versioned release."""
        # Sanitize inputs
        new_version = self._sanitize_input(new_version)
        current_version = self._sanitize_input(current_version)
        date = self._sanitize_input(date)
        repo = self._sanitize_input(repo)

        # Validate version format
        if not re.match(r'^\d+\.\d+\.\d+$', new_version):
            logger.error(f"Invalid version format: {new_version}")
            return False

        # Validate date format
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
            logger.error(f"Invalid date format: {date}")
            return False

        try:
            content = self.read_changelog()
            
            # Find the Unreleased section
            unreleased_pattern = r'## \[Unreleased\](.*?)(?=## \[|\Z)'
            unreleased_match = re.search(unreleased_pattern, content, re.DOTALL)

            if not unreleased_match:
                logger.warning("No [Unreleased] section found")
                return False

            unreleased_content = unreleased_match.group(1).strip()
            
            if not unreleased_content:
                logger.warning("No changes in [Unreleased] section")
                return False

            # Create new version section
            new_version_section = f"## [{new_version}] - {date}\n{unreleased_content}\n\n"
            
            # Replace unreleased with new version and add empty unreleased
            replacement = f"## [Unreleased]\n\n\n{new_version_section}"
            content = content.replace(unreleased_match.group(0), replacement)

            # Update or add comparison links
            if "[Unreleased]:" in content:
                # Update existing links
                content = re.sub(
                    r'\[Unreleased\]:.*',
                    f'[Unreleased]: https://github.com/{repo}/compare/v{new_version}...HEAD',
                    content
                )
                # Add new version link if not exists
                if f"[{new_version}]:" not in content:
                    content = content.rstrip() + f"\n[{new_version}]: https://github.com/{repo}/compare/v{current_version}...v{new_version}\n"
            else:
                # Add links section
                content = content.rstrip() + f"\n\n[Unreleased]: https://github.com/{repo}/compare/v{new_version}...HEAD\n"
                content += f"[{new_version}]: https://github.com/{repo}/compare/v{current_version}...v{new_version}\n"

            self.write_changelog(content)
            logger.info(f"Successfully released version {new_version}")
            return True
            
        except ChangelogError:
            return False
        except Exception as e:
            logger.error(f"Unexpected error releasing version: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Manage changelog entries")
    parser.add_argument("--action", choices=["add", "release"], required=True,
                       help="Action to perform")
    parser.add_argument("--changelog", default="CHANGELOG.md",
                       help="Path to changelog file")
    
    # Arguments for add action
    parser.add_argument("--section", help="Changelog section")
    parser.add_argument("--pr-title", help="Pull request title")
    parser.add_argument("--pr-author", help="Pull request author")
    parser.add_argument("--pr-num", help="Pull request number")
    parser.add_argument("--pr-url", help="Pull request URL")
    
    # Arguments for release action
    parser.add_argument("--new-version", help="New version number")
    parser.add_argument("--current-version", help="Current version number")
    parser.add_argument("--date", help="Release date")
    parser.add_argument("--repo", help="Repository name")
    
    args = parser.parse_args()
    
    manager = ChangelogManager(args.changelog)
    manager.create_changelog_if_missing()
    
    if args.action == "add":
        if not all([args.section, args.pr_title, args.pr_author, args.pr_num, args.pr_url]):
            logger.error("Missing required arguments for add action")
            sys.exit(1)
        
        success = manager.add_entry(
            args.section, args.pr_title, args.pr_author, 
            args.pr_num, args.pr_url
        )
        sys.exit(0 if success else 1)
        
    elif args.action == "release":
        if not all([args.new_version, args.current_version, args.date, args.repo]):
            logger.error("Missing required arguments for release action")
            sys.exit(1)
        
        success = manager.release_version(
            args.new_version, args.current_version, args.date, args.repo
        )
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()