---
type: expert-file
parent: "[[tac/_index]]"
file-type: command
command-name: "question"
human_reviewed: false
tac_original: true
tags: [expert-file, command, read-only]
---

# TAC Expert - Question Mode

> Read-only command to query TAC methodology without making any changes.

## Purpose
Answer questions about Tactical Agentic Coding (TAC) methodology, tactics, frameworks, and patterns **without making any code changes**.

## Usage
```
/experts:tac:question [question]
```

## Allowed Tools
`Task` (REQUIRED), `TodoWrite`

---

## MANDATORY: Always Invoke TAC Agent First

**EVERY question through this command MUST be routed to the `tac` agent. No exceptions.**

DO NOT:
- Search the local `.claude/` directory
- Read local files to answer questions
- Use Glob, Grep, or Read tools directly
- Attempt to answer without invoking the agent

DO:
- Immediately invoke the `tac` agent with the user's question
- Wait for the agent's response
- Return the agent's response to the user

### Required First Action

Your FIRST tool call MUST be:

```
Task(
  subagent_type: "tac",
  prompt: "[FULL USER QUESTION]"
)
```

### Workflow

1. **Receive question** from user
2. **IMMEDIATELY invoke tac agent** - this is your first and primary action
3. **Return the agent's response** to the user with source references
4. If the agent says "not found", relay that to the user

### Example

User asks: "What is Tactic #5?"

Your FIRST action:
```
Task(
  subagent_type: "tac",
  prompt: "What is Tactic #5? Provide the full explanation with source reference."
)
```

User asks: "How do I create an excalidraw agent?"

Your FIRST action (even for practical questions):
```
Task(
  subagent_type: "tac",
  prompt: "How do I create an excalidraw agent? Check TAC knowledge base for agent creation patterns and best practices."
)
```

The agent retrieves the answer from the TAC knowledge base. If not found, it will say so.

---

## Question Categories

### Category 1: Tactic Questions
Questions about the 8 fundamental tactics.

**Examples**:
- "What is Tactic #5?"
- "Explain Stay Out The Loop"
- "What are the Agentic KPIs?"

**Resolution**:
1. Read `expertise.md` for quick summary
2. Read corresponding `quizzes-and-diagrams/tac-{n}/loot.md` for details
3. Provide answer with source reference

---

### Category 2: Framework Questions
Questions about PITER, R&D, Core Four, ACT-LEARN-REUSE.

**Examples**:
- "What is the PITER framework?"
- "Explain R&D context engineering"
- "What are the 12 leverage points?"

**Resolution**:
1. Read `expertise.md` for framework summary
2. Read relevant `loot.md` file for deep details
3. Reference diagrams if visual explanation needed

---

### Category 3: Pattern Questions
Questions about agent patterns and prompt levels.

**Examples**:
- "What is the Pong agent pattern?"
- "Explain the 7 prompt levels"
- "What's the difference between Echo and Calculator patterns?"

**Resolution**:
1. Read `quizzes-and-diagrams/building-specialized-agents/loot.md`
2. Read `quizzes-and-diagrams/agentic-prompt-engineering/loot.md`
3. Provide comparison tables if multiple patterns

---

### Category 4: ADW Questions
Questions about AI Developer Workflows.

**Examples**:
- "How do ADWs work?"
- "What's the plan_build_review workflow?"
- "How do I create a custom ADW?"

**Resolution**:
1. Read `expertise.md` ADW section
2. Read `quizzes-and-diagrams/orchestrator-agent-with-adws/loot.md`
3. Read `index/adws/README.md` for catalog

---

### Category 5: Catalog Questions
Questions about available commands, agents, hooks, skills.

**Examples**:
- "List all TAC commands"
- "What agents are available?"
- "Show me hook patterns"

**Resolution**:
1. Read corresponding `index/{type}/README.md`
2. Provide formatted catalog list
3. Include usage examples

---

### Category 6: Project Questions
Questions about Desktop/tac implementations.

**Examples**:
- "What does agentic-finance-review do?"
- "Explain the tac-8 sub-apps"
- "How is orchestrator-agent-with-adws structured?"

**Resolution**:
1. Read `Desktop/tac/{project}/README.md`
2. Summarize key concepts and structure
3. Reference related loot.md if exists

---

## Workflow

```mermaid
flowchart TD
    A[Receive Question] --> B{Classify Question}
    B -->|Tactic| C[Read tac-n/loot.md]
    B -->|Framework| D[Read expertise.md + relevant loot.md]
    B -->|Pattern| E[Read building-specialized-agents/loot.md]
    B -->|ADW| F[Read orchestrator-agent-with-adws/loot.md]
    B -->|Catalog| G[Read index/{type}/README.md]
    B -->|Project| H[Read Desktop/tac/{project}/README.md]
    C --> I[Generate Answer]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
    I --> J[Include Source Reference]
```

---

## Source Locations

### Theory (TAC-Learning-System)
```
C:\Users\gblac\OneDrive\Desktop\obsidian\Gbautomation\TAC-Learning-System
├── quizzes-and-diagrams/
│   ├── tac-1/ through tac-8/loot.md
│   ├── elite-context-engineering/loot.md
│   ├── agentic-prompt-engineering/loot.md
│   ├── building-specialized-agents/loot.md
│   ├── multi-agent-orchestration/loot.md
│   ├── orchestrator-agent-with-adws/loot.md
│   ├── agent-experts/loot.md
│   └── index/{adws,agents,commands,hooks,skills}/README.md
```

### Projects (Desktop/tac)
```
C:\Users\gblac\OneDrive\Desktop\tac
├── tac-1/ through tac-8/README.md
├── agentic-finance-review/README.md
├── agent-experts/README.md
├── orchestrator-agent-with-adws/README.md
└── ... (12 more project directories)
```

---

## Report Format

```markdown
## Answer

{Direct answer to the question}

## Key Points

- {Point 1}
- {Point 2}
- {Point 3}

## Source Reference

- Primary: `{path/to/primary/source}`
- Secondary: `{path/to/secondary/source}` (if applicable)

## Related Topics

- [[{related-concept-1}]]
- [[{related-concept-2}]]
```

---

## Examples

### Example 1: Tactic Question
```
/experts:tac:question "What is Tactic #5?"
```

**Response**:
> **Tactic #5: Always Add Feedback Loops**
>
> Your work is useless unless tested. Enable agents to act, validate, and correct in continuous cycles. Create closed-loop systems where agents self-validate through linters, unit tests, UI tests, and end-to-end validation.
>
> **Source**: `quizzes-and-diagrams/tac-5/loot.md`

### Example 2: Framework Question
```
/experts:tac:question "Explain the Core Four"
```

**Response**:
> **The Core Four (In-Agent Leverage Points)**
>
> | Lever | Question |
> |-------|----------|
> | Context | What can your agent see? |
> | Model | Which Claude model for the task? |
> | Prompt | What are you asking? |
> | Tools | What can your agent do? |
>
> **Source**: `quizzes-and-diagrams/tac-2/loot.md`

### Example 3: Project Question
```
/experts:tac:question "What is orchestrator-agent-with-adws?"
```

**Response**:
> **orchestrator-agent-with-adws** (34 KB README)
>
> Full-stack orchestration pattern combining:
> - Orchestrator agent with CRUD operations
> - ADW integration with real-time WebSocket updates
> - Swimlane UI for workflow visualization
> - Database persistence for state management
>
> **Source**: `Desktop/tac/orchestrator-agent-with-adws/README.md`
