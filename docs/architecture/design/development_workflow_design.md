# Development Workflow Design

**Version:** 1.0
**Date:** 2025-01-06
**Authors:** Ryan, Claude

## 1. Problem Statement

The Aurite Framework development lacks standardization in how developers work with AI copilots to plan and execute tasks. This leads to:
- Inconsistent documentation and planning across different developers
- Difficulty in tracking project progress and changes
- Copilots lacking context about project-specific workflows
- No clear guidance on when to create design documents vs. implementation plans
- Fragmented approach to different types of development tasks

## 2. Proposed Solution

Implement a structured 7-document rule system in `.clinerules/` that provides:
- Clear workflows for different types of development tasks
- Embedded implementation plan templates within task-specific rules
- Consistent plan organization and versioning approach
- Integrated guidance for design documents where needed

### Document Structure

```
.clinerules/
├── MUST_READ_FIRST.md          # General rules + task router
├── documentation_guide.md       # How to navigate/update docs
├── feature_development_rules.md # Feature workflow + template
├── refactoring_rules.md        # Refactoring workflow + template
├── debugging_rules.md          # Bug fix workflow + template
├── testing_rules.md            # Testing workflow + template
└── documentation_rules.md      # Doc writing workflow + template
```

## 3. Architecture & Workflow

### 3.1 Document Relationships

```
MUST_READ_FIRST.md (Entry Point)
    ├─→ Determines task type
    ├─→ Routes to specific rule document
    └─→ References documentation_guide.md for context

Task-Specific Rules (5 documents)
    ├─→ Define workflow phases (PLAN MODE → ACT MODE)
    ├─→ Embed implementation plan template
    ├─→ Include design document guidance (when needed)
    └─→ Link to example plans

Documentation Guide
    └─→ Maps all documentation for reference
```

### 3.2 Implementation Plan Organization

All implementation plans follow this structure:
```
docs/plans/[project_name]/MM-DD_[descriptive_name].md
```

Example:
```
docs/plans/overhaul/01-06_refactor_host_manager.md
docs/plans/auth/02-15_oauth_integration.md
```

### 3.3 Plan Evolution Strategy

Plans use a **changelog approach** with in-place updates:
- Version number increments for significant changes
- Change log section tracks all modifications
- Completed steps marked with checkmarks
- Original content preserved with strikethrough for removed items

## 4. Key Design Decisions

### 4.1 Why Five Task-Specific Rules?

Instead of one generic template, we chose five specialized rules because:
- **Contextual Guidance**: Each task type has unique considerations
- **Reduced Cognitive Load**: Copilots get only relevant sections
- **Better Quality**: Templates guide toward task-appropriate detail levels
- **Clear Selection**: Simple decision tree for choosing the right workflow

### 4.2 Why Embed Templates in Rules?

Rather than separate template files:
- **Single Source**: Everything needed is in one document
- **Context Preservation**: Workflow and template are connected
- **Easier Maintenance**: Updates to workflow can adjust template simultaneously
- **Better Copilot Experience**: No context switching between files

### 4.3 Project-Based Plan Organization

The `[project_name]/MM-DD_[name].md` structure provides:
- **Project Context**: Plans grouped by related work
- **Chronological Ordering**: Date prefix enables easy sorting
- **Integration**: Aligns with Notion project tracking
- **Scalability**: Works for both small and large projects

### 4.4 Changelog Over Versioned Files

We chose in-place updates with changelogs because:
- **Single Source of Truth**: No confusion about current version
- **Historical Context**: Evolution of thinking is preserved
- **Git Integration**: Detailed history already tracked in version control
- **Copilot Friendly**: Full context available in one file

## 5. Implementation Details

### 5.1 Task-Specific Rule Structure

Each of the 5 task-specific rule documents contains:

1. **Purpose & When to Use**
   - Clear criteria for selecting this workflow
   - Examples of applicable scenarios

2. **Workflow Phases**
   - Discovery (PLAN MODE): Context gathering
   - Design (PLAN MODE, if needed): Architecture decisions
   - Planning (PLAN MODE): Create implementation plan
   - Implementation (ACT MODE): Execute the plan

3. **Best Practices**
   - Task-specific guidelines and considerations
   - Common pitfalls to avoid

4. **Implementation Plan Template**
   - Embedded template with appropriate sections
   - Level of detail guidance

5. **Example References**
   - Links to real plans using this template

### 5.2 Design Document Integration

For feature and refactoring rules, design document guidance is embedded:
- Criteria for when a design document is needed
- Brief structure (not a full template)
- Storage location: `docs/architecture/design/`
- Linkage with implementation plans

### 5.3 MUST_READ_FIRST.md Updates

Will be refactored to:
- Serve as the entry point and router
- Include the decision tree for task type selection
- Contain general rules that apply to all tasks
- Reference the documentation guide for finding relevant files

## 6. Benefits

1. **Consistency**: All developers follow the same workflows
2. **Efficiency**: Copilots have clear guidance and templates
3. **Traceability**: Project-based organization aids tracking
4. **Flexibility**: Templates can be adapted while maintaining structure
5. **Learning**: New developers have clear patterns to follow

## 7. Future Considerations

- Monitor which templates are most/least used
- Gather feedback on template effectiveness
- Consider additional templates if new patterns emerge
- Potentially automate some plan creation/updating tasks
