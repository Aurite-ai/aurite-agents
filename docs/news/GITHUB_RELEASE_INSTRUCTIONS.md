# GitHub Release Instructions for v0.4.2

## Steps to Create the Release

1. **Go to GitHub Releases Page**

   - Navigate to: https://github.com/Aurite-ai/aurite-agents/releases
   - Click "Draft a new release"

2. **Configure Release Details**

   - **Choose a tag**: Create new tag `v0.4.2`
   - **Target**: main branch
   - **Release title**: `v0.4.2 - Developer Experience Update`
   - **Set as latest release**: ✅ Check this box

3. **Copy the Release Content**

   - Copy the content below (everything between the "--- START ---" and "--- END ---" markers)
   - Paste it into the release description field

4. **Upload Screenshots**

   - Drag and drop the following images from `docs/images/release-notes/`:
     1. `schema-validation-error.png`
     2. `hover-documentation.png`
     3. `field-autocomplete.png`
     4. `value-autocomplete.png`
     5. `test-cli-output.png`
   - GitHub will automatically generate URLs and update the markdown references

5. **Publish**
   - Review the preview
   - Click "Publish release"

---

## Release Content (Copy Everything Below)

--- START ---

# 🎉 Developer Experience Update for Aurite Agents

We're excited to announce powerful new developer tools to enhance your workflow with Aurite Agents!

## ✨ What's New

### 🧪 Testing CLI Support

Run comprehensive tests directly from your terminal with beautiful output displays and powerful filtering options.

**New Command:** `aurite test {eval_name}`

- Run quality assurance tests with detailed reporting
- Use feature flags like `--test_cases` to specify specific test cases
- Control output verbosity and detail levels
- Get clear, actionable test results in your terminal

![Testing CLI Output](https://github.com/Aurite-ai/aurite-agents/releases/download/v0.4.2/test-cli-output.png)
_Testing CLI with detailed output display_

### 🔧 IDE Intelligence for Configuration Files

Full IDE support for all Aurite configuration files (YAML/JSON), including QA test configurations.

#### Setup

Run the linter setup command to enable IDE support:

```bash
aurite-linter
```

This automatically configures VS Code to use JSON schemas for intelligent assistance.

### Features

#### ✅ Schema Validation

- **Real-time type safety** for all configuration files
- **Instant error detection** with inline error messages and warnings
- Validates structure, required fields, and data types
- Works with agents, workflows, LLMs, MCP servers, and evaluation configs

![Schema Validation Error](https://github.com/Aurite-ai/aurite-agents/releases/download/v0.4.2/schema-validation-error.png)
_Inline linter errors for invalid configurations_

#### 📖 Intelligent Documentation

- **Hover for details**: See comprehensive field descriptions by hovering over any configuration property
- Documentation pulled directly from the framework's type definitions
- Understand each field's purpose without leaving your editor

![Hover Documentation](https://github.com/Aurite-ai/aurite-agents/releases/download/v0.4.2/hover-documentation.png)
_Detailed descriptions on hover_

#### 🚀 Smart Auto-Complete

- **Field suggestions**: As you type, get suggestions for available configuration properties
- **Value completion**: Get intelligent suggestions for field values based on the schema
  - Enum values (like "type" fields) are suggested automatically
  - Press Tab to accept suggestions
- **Context-aware**: Suggestions adapt based on the component type you're configuring

![Field Auto-Complete](https://github.com/Aurite-ai/aurite-agents/releases/download/v0.4.2/field-autocomplete.png)
_Unused fields suggested in popup with descriptions_

![Value Auto-Complete](https://github.com/Aurite-ai/aurite-agents/releases/download/v0.4.2/value-autocomplete.png)
_Smart type field completion based on schema_

#### 🤖 AI Copilot Integration

Since the schema validation appears as standard linter errors in your IDE, AI coding assistants can:

- See and understand configuration errors
- Provide better suggestions for fixes
- Help you write valid configurations from the start

### Supported Formats

- ✅ YAML files (requires [YAML extension by Red Hat](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml))
- ✅ JSON files (native VS Code support)
- ✅ All Aurite component types: agents, workflows, LLMs, MCP servers, evaluations, and more

## 🚀 Getting Started

1. **Update to v0.4.2**:

   ```bash
   pip install --upgrade aurite
   ```

2. **Enable IDE support**:

   ```bash
   aurite-linter
   ```

3. **Install VS Code YAML extension** (for YAML support):

   - Open VS Code
   - Search for "YAML" in extensions
   - Install the extension by Red Hat

4. **Start using the new features**:
   - Run tests: `aurite test my_evaluation`
   - Create configurations with full IDE support

## 📚 How It Works

The `aurite-linter` command generates JSON schemas from Aurite's Pydantic models, providing:

- Type definitions for every configuration field
- Validation rules and constraints
- Field descriptions and documentation
- Auto-complete suggestions for both field names and values

This means your IDE understands the exact structure of Aurite configurations and can guide you while you write them!

## 🔄 What's Changed

- Added `aurite-linter` CLI command for IDE configuration setup
- Introduced `aurite test` command for running evaluations from the terminal
- Generated comprehensive JSON schemas for all component types
- Enhanced VS Code integration with automatic schema association
- Improved developer experience with intelligent code completion

## 📝 Full Changelog

See the [Full Changelog](https://github.com/Aurite-ai/aurite-agents/blob/main/CHANGELOG.md) for complete details on all changes in this release.

## 🙏 Acknowledgments

Thanks to all contributors and users who provided feedback on improving the developer experience!

---

**Installation**: `pip install aurite==0.4.2`
**Documentation**: [docs.aurite.ai](https://aurite-ai.github.io/aurite-agents)
**Repository**: [github.com/Aurite-ai/aurite-agents](https://github.com/Aurite-ai/aurite-agents)

--- END ---

## Notes

- After uploading images, GitHub will provide URLs like: `https://github.com/Aurite-ai/aurite-agents/releases/download/v0.4.2/[filename]`
- The markdown references in the content above assume these standard GitHub release asset URLs
- You may need to update the image URLs after uploading if GitHub generates different URLs
