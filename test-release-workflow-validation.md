# Test Release Workflow Validation

**Date:** September 2, 2025  
**Purpose:** Validate the automated release pipeline for TestPyPI

## Test Details

This file is created to test the GitHub Actions release workflow:

1. **Changelog Workflow** - Should update CHANGELOG.md when this PR is merged
2. **Release Workflow** - Should trigger after changelog workflow and publish to TestPyPI
3. **Version Format** - Should use timestamp suffix for test releases (e.g., 0.3.28rc20250902130700)

## Expected Behavior

- PR labeled with `patch` + `test` should trigger TestPyPI release
- No git tags should be created for test releases
- Package should appear on https://test.pypi.org/project/aurite-agents/

## Validation Steps

1. Create PR with proper labels
2. Merge PR to main
3. Monitor GitHub Actions workflows
4. Verify TestPyPI publication
5. Test installation from TestPyPI

---

**Note:** This is a safe test that only publishes to TestPyPI, not production PyPI.
