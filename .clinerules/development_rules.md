# Aurite Framework: Development Rules

**Document Type:** Core Development Rules
**When to Use:** For all development tasks (Level 3+) in the framework

## 1. Overview

This document provides the standard workflow and templates for all development tasks in the Aurite Framework. It covers features, refactoring, bug fixes, and any other code changes.

## 2. Workflow Phases

### Phase 1: Discovery
- Review `.clinerules/documentation_guide.md` to identify relevant documentation
- Read the identified documents from `docs/` to understand the feature area
- Examine source files referenced in the documentation to understand current implementation

### Phase 2: Design (if complexity warrants)
- For significant features, create a design document in `docs/architecture/design/`
- Include: Architecture decisions, component interactions, API design
- Get design approval before proceeding to planning

### Phase 3: Planning
- Create implementation plan using template below
- Store in `docs/internal/plans/[project]/MM-DD_[descriptive_name].md`
- Include testing as integral part of each implementation phase
- Plan for documentation updates as final step

### Phase 4: Implementation
- Execute plan step-by-step
- When reaching testing steps, consult `tests/README.md` to locate relevant test files
- Run tests after each implementation phase
- Update plan changelog as work progresses

## 3. Implementation Plan Templates

Choose the appropriate template based on your task type:

### 3.1 Feature Development Template

```markdown
# Implementation Plan: [Feature Name]

**Type:** Feature Development
**Date:** YYYY-MM-DD
**Author:** [User's Name or blank]
**Design Doc:** [Link if applicable]

## Goal
[What new capability will this add to the framework?]

## Context
[Why is this feature needed? What problem does it solve?]

## Architecture Impact
- **Affected Layers:** [e.g., Orchestration, Host]
- **New Components:** [List any new classes/modules]
- **Modified Components:** [List existing components to change]

## Implementation Steps

[Organize your implementation into logical phases. Each phase should represent a cohesive set of changes that can be tested together. Within each phase, list specific steps with file paths and clear actions.]

### Phase 1: [Descriptive Phase Name]
1. [Specific action with file path]
2. [Another specific action]
3. [Testing step referencing specific test files]

### Phase 2: [Descriptive Phase Name]
4. [Continue numbering across phases]
5. [More specific actions]
6. [Testing step]

[Continue with additional phases as needed]

## Testing Strategy
See `tests/README.md` for testing guidelines and structure.

## Documentation Updates
See `.clinerules/documentation_guide.md` for documentation update requirements.

## Changelog
- v1.0 (YYYY-MM-DD): Initial plan
```