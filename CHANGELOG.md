# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (though we are pre-1.0.0).

## [Unreleased]


### Added
- Fixed tests and added new ones to fit guide ([@jwilcox17](https://github.com/jwilcox17)) [#commit-47f59dc](https://github.com/Aurite-ai/aurite-agents/commit/47f59dcd25bebeada9b105e10528ac62272f41fc)
### Fixed
- Fixed Framework test commands ([@jwilcox17](https://github.com/jwilcox17)) [#commit-632796a](https://github.com/Aurite-ai/aurite-agents/commit/632796ac358a90150c9847ae49e389dfea3cd9b4)
### Changed
- Revert framework-tests to simple tests ([@jwilcox17](https://github.com/jwilcox17)) [#commit-3542ce7](https://github.com/Aurite-ai/aurite-agents/commit/3542ce7ce3a19c04e7aeb7f60c09151bcae9d99d)
- Testing run on push again ([@jwilcox17](https://github.com/jwilcox17)) [#commit-32102ba](https://github.com/Aurite-ai/aurite-agents/commit/32102ba764976d72e8ae1509e42c78c2da8114b9)
## [0.2.17]

### Changed
- Logging improved: Removed unnecessary logging and colored the most important log statements (different color for each framework layer).
- Agent final response improved: Now handled through a Pydantic model, replacing a simple Python dict. This simplifies retrieving the agent's response (e.g., `response_text = agent_result.primary_text`) and includes built-in error handling.
