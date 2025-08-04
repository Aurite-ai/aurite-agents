# 🚨 START HERE - Aurite Framework Development Guide

You are working in the **Aurite Agents** framework repository, a collaborative project maintained by multiple developers using AI copilots. Following these rules is **CRITICAL** for maintaining code quality, consistency, and effective collaboration across the team.

## Your First Steps

1. **Assess the task complexity** (see Section 1 below)
2. **Select the appropriate rule document** (see Section 2 - Task Router)
3. **Follow general development principles** (see Section 3)
4. **Use documentation guide for context** (see `.clinerules/02_DOCUMENTATION_GUIDE.md`)

---

## 1. Task Complexity Levels

Not every task requires a formal plan. Use this guide to determine the appropriate approach:

### Level 1: Simple Question/Command

**Examples:** "What does this function do?", "Show me the test files", "Run the tests"

- **Plan Required:** No
- **Approach:** Answer directly or execute the command
- **Documentation:** None needed

### Level 2: Basic Task

**Examples:** Fix a typo, update a comment, add a simple logging statement

- **Plan Required:** No
- **Approach:** Make the change directly if the solution is obvious
- **Documentation:** Rarely needed

### Level 3: Standard Task

**Examples:** Add a new method, fix a straightforward bug, update documentation

- **Plan Required:** Recommended but not required
- **Approach:** May benefit from a simple plan outlining steps
- **Documentation:** Update relevant docs if needed

### Level 4: Complex Task

**Examples:** Implement a new feature, refactor a module, fix a complex bug

- **Plan Required:** Yes - Implementation Plan
- **Approach:** Follow full workflow: Discovery → Planning → Implementation
- **Documentation:** Implementation plan in `docs/internal/plans/[project]/`

### Level 5: Complex Task with Design

**Examples:** New architecture component, significant refactoring, API redesign

- **Plan Required:** Yes - Design Document + Implementation Plan
- **Approach:** Design first, then plan, then implement
- **Documentation:** Design doc in `docs/architecture/design/` + plan

### Level 6: Multiple Related Tasks

**Examples:** Project overhaul, multi-feature implementation, system-wide changes

- **Plan Required:** Yes - Overarching plan + individual task plans
- **Approach:** Break into sub-tasks, each with its own plan
- **Documentation:** Project plan + first implementation plan

---

## 2. Task Router - Which Rules to Follow?

For development tasks (Level 3+), follow this guidance:

```
ALL development tasks:
├─ Start with → `01_DEVELOPMENT_RULES.md`
│
└─ Then, based on task type, ALSO read:
   ├─ Improving existing code? → Add `REFACTORING_RULES.md`
   └─ Fixing bugs/errors? → Add `DEBUGGING_RULES.md`
```

### Quick Reference:

- **All development tasks** → Start with `01_DEVELOPMENT_RULES.md`
- **Code improvements** → Also read `REFACTORING_RULES.md`
- **Bug fixes** → Also read `DEBUGGING_RULES.md`

Note: Testing and documentation updates are integral parts of all development tasks and are covered in `01_DEVELOPMENT_RULES.md`.

---

## 3. General Development Principles

These rules apply to ALL development tasks, regardless of type:

### 3.1 Context is King

- **Always** check existing code/docs before making assumptions
- Use project artifacts as your primary source of truth:
  - `docs/` for plans and design documents
  - `tests/` for understanding expected behavior
  - Source code as the ultimate specification

### 3.2 Communication Standards

- Be clear and technical in responses (avoid conversational fluff)
- Confirm understanding before executing complex tasks
- Report completion of each major step
- Ask clarifying questions when requirements are ambiguous

### 3.3 Code Quality

- Write clean, readable, maintainable code
- Follow the **Aurite Framework Coding Standard** (see `.clinerules/CODING_STANDARD.md`)
- Include appropriate comments for complex logic
- Ensure all relevant tests pass before considering a task complete

### 3.4 File Modification Strategy

- Use `replace_in_file` for small, targeted changes
- Use `write_to_file` for new files or major rewrites
- Always read the current file content before attempting modifications
- Be aware of auto-formatting that may change file structure

### 3.5 Testing Approach

- Write tests for new functionality (TDD when possible)
- Run relevant tests after each implementation step
- Fix failing tests before proceeding to next steps
- Consider edge cases and error conditions

### 3.6 Documentation Updates

- Update relevant documentation when changing functionality
- Keep implementation plans current with changelog entries
- Ensure code comments reflect any logic changes
- Update README files if user-facing changes are made

### 3.7 Collaboration Practices

- Follow the established plan/act workflow phases
- Create implementation plans for complex tasks (Level 4+)
- Store plans in `docs/internal/plans/[project]/MM-DD_[name].md`
- Use changelogs within plans to track modifications

---

## 4. Quick Reference Links

### Essential Documents

- **Documentation Navigation:** `.clinerules/02_DOCUMENTATION_GUIDE.md`
- **Architecture Overview:** `docs/architecture/overview.md`
- **Testing Guide:** `tests/README.md`

### Code Organization

- **Aurite Framework Coding Standard:** `.clinerules/CODING_STANDARD.md`

### Task-Specific Rules (Level 3+ tasks)

- **All Development:** `.clinerules/01_DEVELOPMENT_RULES.md`
- **Refactoring:** `.clinerules/REFACTORING_RULES.md`
- **Debugging:** `.clinerules/DEBUGGING_RULES.md`

### Implementation Plans

- **Location:** `docs/plans/[project_name]/`
- **Format:** `MM-DD_[descriptive_name].md`
- **Examples:** Browse existing plans for reference

---

## Remember

**Flexibility is key!** Not every conversation needs a formal plan. Use your judgment based on the task complexity levels above. When in doubt, ask the user for guidance on the appropriate level of formality needed.

The goal is effective collaboration and quality code, not bureaucratic process. These rules exist to help achieve that goal, not hinder it.
