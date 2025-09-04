# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (though we are pre-1.0.0).

## [Unreleased]

### Added
- Add automated changelog management workflow ([@jwilcox17](https://github.com/jwilcox17)) [#139](https://github.com/Aurite-ai/aurite-agents/pull/139)
- added storage optional dep ([@wilcoxr](https://github.com/wilcoxr)) [#142](https://github.com/Aurite-ai/aurite-agents/pull/142)
- Added PyPI release automation workflow for quicker release ([@jwilcox17](https://github.com/jwilcox17)) [#145](https://github.com/Aurite-ai/aurite-agents/pull/145)
- Add messages parameter to agent endpoints ([@blakerandle](https://github.com/blakerandle)) [#146](https://github.com/Aurite-ai/aurite-agents/pull/146)
- feat: added security module ([@jitenoswal](https://github.com/jitenoswal)) [#147](https://github.com/Aurite-ai/aurite-agents/pull/147)
- Feat-sqlite-support ([@wilcoxr](https://github.com/wilcoxr)) [#149](https://github.com/Aurite-ai/aurite-agents/pull/149)

### Changed
- Graph workflow ([@blakerandle](https://github.com/blakerandle)) [#120](https://github.com/Aurite-ai/aurite-agents/pull/120)
- docs: add second test comment to validate changelog workflow ([@jitenoswal](https://github.com/jitenoswal)) [#141](https://github.com/Aurite-ai/aurite-agents/pull/141)
- Eval schema ([@blakerandle](https://github.com/blakerandle)) [#143](https://github.com/Aurite-ai/aurite-agents/pull/143)
- database guide ([@wilcoxr](https://github.com/wilcoxr)) [#148](https://github.com/Aurite-ai/aurite-agents/pull/148)
- Container-updates-clean ([@wilcoxr](https://github.com/wilcoxr)) [#150](https://github.com/Aurite-ai/aurite-agents/pull/150)
- Example project fix ([@blakerandle](https://github.com/blakerandle)) [#151](https://github.com/Aurite-ai/aurite-agents/pull/151)
- test: add test file for release workflow validation ([@jitenoswal](https://github.com/jitenoswal)) [#153](https://github.com/Aurite-ai/aurite-agents/pull/153)
- fix: add git synchronization to release workflow ([@jitenoswal](https://github.com/jitenoswal)) [#154](https://github.com/Aurite-ai/aurite-agents/pull/154)
- test: add test file for release workflow validation ([@jitenoswal](https://github.com/jitenoswal)) [#155](https://github.com/Aurite-ai/aurite-agents/pull/155)
- test: add test file for release workflow validation ([@jitenoswal](https://github.com/jitenoswal)) [#158](https://github.com/Aurite-ai/aurite-agents/pull/158)
- test: Merge changelog and release automation workflows ([@jwilcox17](https://github.com/jwilcox17)) [#159](https://github.com/Aurite-ai/aurite-agents/pull/159)
- test: add workflow validation test file for release automation ([@jitenoswal](https://github.com/jitenoswal)) [#161](https://github.com/Aurite-ai/aurite-agents/pull/161)
- test: add fixed version validation test for release workflow ([@jitenoswal](https://github.com/jitenoswal)) [#162](https://github.com/Aurite-ai/aurite-agents/pull/162)
- fix: test releases now trigger timestamp ([@jwilcox17](https://github.com/jwilcox17)) [#163](https://github.com/Aurite-ai/aurite-agents/pull/163)
- fix: test/prod release triggers ([@jwilcox17](https://github.com/jwilcox17)) [#164](https://github.com/Aurite-ai/aurite-agents/pull/164)
- Changelog automation ([@jwilcox17](https://github.com/jwilcox17)) [#167](https://github.com/Aurite-ai/aurite-agents/pull/167)

### Documentation
- docs: test for release pypi workflow ([@jitenoswal](https://github.com/jitenoswal)) [#165](https://github.com/Aurite-ai/aurite-agents/pull/165)

### Fixed
- fix: changelog now has proper formatting to work with cicd automation ([@jwilcox17](https://github.com/jwilcox17)) [#168](https://github.com/Aurite-ai/aurite-agents/pull/168)
- fix: github handling in git automation workflows ([@jwilcox17](https://github.com/jwilcox17)) [#156](https://github.com/Aurite-ai/aurite-agents/pull/156)
- fix: improve release workflow PR info extraction from commit messages ([@jitenoswal](https://github.com/jitenoswal)) [#160](https://github.com/Aurite-ai/aurite-agents/pull/160)

## [0.3.28] - 2025-08-20

### 🚀 Major Release: Framework Enhancements & Aurite Studio Launch!

This release marks a significant milestone with the launch of **Aurite Studio** - a comprehensive React-based web GUI for the Aurite framework, along with major enhancements across the entire platform.

### Added
- **🎨 Aurite Studio**: Complete React web application providing visual management of agents, workflows, and configurations (MCP & LLM)
  - Interactive agent & workflow configuration and testing interface
  - LLM provider setup and testing tools
  - MCP server integration management
  - Modern, responsive UI with comprehensive error handling
- **🔧 Enhanced CLI**: New `aurite studio` & improved `aurite api` command with automatic dependency management
- **🌐 Comprehensive REST API**: Expanded API endpoints for complete framework control

### Changed
- **⚡ Framework Performance**: Significantly improved agent execution speed and reliability
- **🏗️ Architecture Enhancements**: Better separation of concerns and modular design
- **📝 Configuration System**: More intuitive and powerful component configuration
- **🔍 Logging & Debugging**: Enhanced logging with better error tracking and debugging tools
- **📚 Documentation**: Comprehensive updates with new guides and examples
- **🔄 Workflow Engine**: Improved linear and custom workflow execution
- **🛠️ MCP Integration**: Enhanced Model Context Protocol support with better tool management
- **💾 Storage Layer**: Optimized session management and data persistence
- **📦 Package Distribution**: Added frontend asset bundling and static file serving

### Fixed
- **🐛 Agent Stability**: Resolved critical issues in agent execution and response handling
- **🔗 API Reliability**: Improved error handling and response consistency across all endpoints
- **⚙️ Configuration Loading**: Fixed edge cases in workspace and project configuration parsing
- **🌐 Cross-platform Support**: Better compatibility across different operating systems
- **🔧 CLI Robustness**: Enhanced command-line interface stability and error reporting

### Technical Improvements
- **Dependencies**: Updated to latest stable versions for better compatibility and security
- **Testing**: Expanded test coverage with comprehensive integration and end-to-end tests
- **Build System**: Improved build processes for both Python package and frontend assets
- **Performance**: Optimized memory usage and response times across the framework
- **Error Handling**: Comprehensive error handling with detailed user feedback

This release represents over a month of intensive development, transforming Aurite from a CLI-focused framework into a comprehensive platform with both programmatic and visual interfaces for AI agent development and deployment.

## [0.2.17]

### Changed
- Logging improved: Removed unnecessary logging and colored the most important log statements (different color for each framework layer).
- Agent final response improved: Now handled through a Pydantic model, replacing a simple Python dict. This simplifies retrieving the agent's response (e.g., `response_text = agent_result.primary_text`) and includes built-in error handling.

[Unreleased]: https://github.com/Aurite-ai/aurite-agents/compare/v0.3.28...HEAD
[0.3.28]: https://github.com/aurite-agents/aurite-agents/compare/v0.2.17...v0.3.28
