# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (though we are pre-1.0.0).

## [Unreleased]


### Changed
- Testing run on push again ([@jwilcox17](https://github.com/jwilcox17)) [#commit-32102ba](https://github.com/Aurite-ai/aurite-agents/commit/32102ba764976d72e8ae1509e42c78c2da8114b9)
## [0.2.17]

### Changed
- Logging improved: Removed unnecessary logging and colored the most important log statements (different color for each framework layer).
- Agent final response improved: Now handled through a Pydantic model, replacing a simple Python dict. This simplifies retrieving the agent's response (e.g., `response_text = agent_result.primary_text`) and includes built-in error handling.
