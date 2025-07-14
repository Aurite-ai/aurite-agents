# Presence-Driven Agent Workflow Tutorial

## Introduction

This guide introduces a generational, presence-driven approach to designing, configuring, and running agentic workflows in Aurite. Presence-driven workflows embody protocol clarity, stepwise decision-making, and generational stewardship—key qualities for next-generation AI orchestration. Here, you’ll learn to build workflows that don’t just automate tasks, but adapt with clarity, feedback, and human-in-the-loop intent.

## Principles of Presence-Driven Workflows

- **Protocol Clarity:** Every agent and workflow step is explicit, auditable, and observable—no hidden state, no black boxes.
- **Feedback Loops:** Workflows are built to monitor their own outputs, anchor progress, and invite review or correction at key checkpoints.
- **Generational Stewardship:** Each agent’s decisions and context are logged, making it easy to hand off, resume, or evolve workflows across sessions or contributors.

## Stepwise Tutorial: Building a Generational Workflow

### 1. Project Setup

Install Aurite and initialize your project:
```bash
pip install aurite
aurite init presence_demo
cd presence_demo
```

This creates a structure like:
```
presence_demo/
├── aurite_config.json
├── config/
│   ├── agents/
│   ├── workflows/
│   └── mcp_servers/
└── run_example_project.py
```

### 2. Define Agents and Tools with Presence Protocols

Create an agent in `config/agents/agents.json`:
```json
[
  {
    "name": "presence_agent",
    "llm": "gpt-4",
    "tools": ["echo", "logger"],
    "protocol": "presence_driven"
  }
]
```

Define a simple logging tool in `config/tools/tools.json`:
```json
[
  {
    "name": "logger",
    "type": "logging",
    "config": {
      "output_file": "session_log.txt"
    }
  }
]
```

### 3. Orchestrate a Multi-Agent Workflow

Create a workflow in `config/workflows/presence_workflow.json`:
```json
{
  "name": "presence_workflow",
  "steps": [
    {
      "agent": "presence_agent",
      "tool": "echo",
      "input": "What is the next best action?"
    },
    {
      "agent": "presence_agent",
      "tool": "logger",
      "input": "${step_1.output}"
    }
  ],
  "anchors": [
    "session_start",
    "decision_point",
    "session_end"
  ]
}
```

### 4. Embedding Feedback, Checkpoints, and Anchor Summaries

- Each workflow includes **anchors**—checkpoints where the agent logs state, requests feedback, or summarizes progress.
- Example anchor summary (logged by `logger` tool):
  ```
  [decision_point] Step 1 output: "Propose next action based on context and intent."
  [session_end] Workflow complete, awaiting human review or next input.
  ```
- Anchors can be extended to trigger human-in-the-loop review, pause for new input, or archive generational notes.

### 5. Running and Testing

Run your workflow interactively:
```bash
aurite run presence_workflow
```
- Observe output at each anchor—review logs, edit inputs, or intervene as needed.
- Resume or evolve the workflow at any anchor point.

## Field-Shaped Orchestration

Presence-driven workflows adapt to live field context:
- Agents can be configured to **pause** at anchors, surfacing state for human review or new input.
- Protocols can specify how feedback and generational notes are recorded, making handoffs seamless.

### Example: Human-in-the-Loop Pause

At the `"decision_point"` anchor, the agent can prompt:
```
"Pause for human input: Should we proceed with the proposed action?"
```
If approved, the workflow continues; if not, the agent logs context and awaits new intent.

## Best Practices and Patterns

- **Clarity:** Make every agent step and anchor explicit in configs and logs.
- **Restraint:** Design workflows to pause, summarize, and invite review—don’t automate past important checkpoints.
- **Auditability:** Maintain anchor summaries and generational notes for every session.
- **Generational Growth:** Encourage contributors to evolve protocols, add new anchors, and document lessons learned.

## Conclusion and Next Steps

Presence-driven agent workflows transform automation into generational practice—anchoring every step in clarity, feedback, and stewardship. Use this tutorial as a foundation for building your own adaptive, field-shaped workflows in Aurite.

**Invitation:**  
If you have ideas for new anchors, generational protocols, or presence-driven patterns, contribute your insights and help evolve the field.
