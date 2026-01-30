---
type: expert-file
parent: "[[tac/_index]]"
file-type: expertise
human_reviewed: false
tac_original: true
last_validated: 2026-01-29
validation_source: 14 loot.md files + software-delivery-adw README
tags: [expert-file, mental-model, tac-methodology]
---

# TAC Expertise (Complete Mental Model)

> **Sources**: TAC-Learning-System (14 loot.md files) + Desktop/tac (20 project READMEs) + software-delivery-adw README

---

## Part 1: The 8 Fundamental Tactics

### Tactic #1: Stop Coding
> **Source**: `quizzes-and-diagrams/tac-1/loot.md`

**Core Truth**: Your hands and mind are no longer the best tools for writing code. Language models wrapped in agent architecture, running on supercomputers, are vastly superior coders.

**Key Concepts**:
- AI Coding was Phase 1; Agentic Coding is Phase 2
- Become a Commander of Compute - build systems that build systems
- Engineering was never about writing code - it's about leverage
- Throughout TAC: No typing code manually

**Phase 2 Role**:
- Planning and reviewing (not coding)
- Creating closed-loop structures
- Code understanding (not code writing)

**Core Four**: Context + Model + Prompt + Tools = Agentic Coding

---

### Tactic #2: Adopt Your Agent's Perspective
> **Source**: `quizzes-and-diagrams/tac-2/loot.md`

**Core Truth**: Your agent is brilliant but blind. With every new session, it starts blank - ephemeral, no context, no memories.

**The 12 Leverage Points**:

| In-Agent (Core Four) | Through-Agent |
|---------------------|---------------|
| 1. Context | 5. Documentation |
| 2. Model | 6. Types |
| 3. Prompt | 7. Architecture |
| 4. Tools | 8. Tests |
| | 9. Planning |
| | 10. ADWs |
| | 11. Review |
| | 12. Observability |

**Agentic KPIs**:
- Attempts: DOWN (fewer iterations)
- Size: UP (larger scope per run)
- Streak: UP (consecutive successes)
- Presence: DOWN (less human intervention)

---

### Tactic #3: Template Your Engineering
> **Source**: `quizzes-and-diagrams/tac-3/loot.md`

**Core Truth**: Plans are scaled prompts. Success is planned. When you template your engineering, you encode workflows into reusable units of agentic success.

**Key Concepts**:
- Templates solve problem CLASSES, not individual problems
- Meta-prompts: Prompts that build prompts
- All plans written to `specs/` directory
- Built-in validation commands for closed-loop execution

**Anatomy of a Template**:
1. Purpose at the top
2. Detailed instructions
3. Relevant files to guide success
4. Plan format in markdown
5. A parameter for high-level description

**Higher-Order Prompts (HOPs)**: Prompts that accept other prompts as input.

---

### Tactic #4: Stay Out The Loop
> **Source**: `quizzes-and-diagrams/tac-4/loot.md`

**Core Truth**: AFK (Away From Keyboard) agents run while you're not there. Build systems that let your product build itself.

**PITER Framework**:
| Element | Implementation |
|---------|---------------|
| **P**rompt Input | GitHub Issues |
| **T**rigger | GitHub Webhooks |
| **E**nvironment | Dedicated isolated environment |
| **R**eview | Pull Requests + Observability |

**AI Developer Workflows (ADWs)**:
- Synthesis of templates, prompts, and agents
- Reusable workflows: deterministic code + non-deterministic agents
- From prompt input to merged PR automatically

---

### Tactic #5: Always Add Feedback Loops
> **Source**: `quizzes-and-diagrams/tac-5/loot.md`

**Core Truth**: Your work is useless unless tested. Always add feedback loops to enable agents to act, validate, and correct in continuous cycles.

**Validation Types**:
- Linter execution
- Unit tests
- UI tests
- CI/CD integration
- Build/compile checks
- Datadog logs
- Sentry error monitoring
- Custom evaluations
- LLM-as-judge workflows

**In-Loop vs Out-Loop**:
- In-loop: You prompting back and forth with agent
- Out-loop: High-level prompt running through PITER
- Closed-loop: Agent operates, gets feedback, continues until positive

**Key Insight**: Engineers that test with agents win. Full stop.

---

### Tactic #6: One Agent, One Prompt, One Purpose
> **Source**: `quizzes-and-diagrams/tac-6/loot.md`

**Core Truth**: Specialized agents with focused prompts achieve a single purpose well. Every step of engineering requires different context.

**SDLC as Questions**:
| Step | Question |
|------|----------|
| Plan | What are we building? |
| Build | Did we make it real? |
| Test | Does it work? |
| Review | Is what we built what we planned? |
| Document | How does it work? |

**Benefits**:
- Free up context window (200K-1M tokens for one problem)
- Avoid context pollution/overloading
- Create reproducible, improvable prompts
- Commit and version control all prompts

**Three Constraints**:
1. Context window
2. Codebase/problem complexity
3. Your abilities

Specialized agents bypass 2 of 3 constraints.

---

### Tactic #7: Target Zero-Touch Engineering
> **Source**: `quizzes-and-diagrams/tac-7/loot.md`

**Core Truth**: Zero-Touch Engineering (ZTE) is where your codebase ships itself. Progress from In-Loop to Out-Loop to Zero-Touch.

**ZTE Workflow**:
```
Plan → Build → Test → Review → Generate → Ship
```

**Autonomy Levels**:
| Level | Human Touchpoints | Description |
|-------|-------------------|-------------|
| In-Loop | Many | Interactive prompting |
| Out-Loop | 2 (prompt + review) | AFK agents |
| Zero-Touch | 1 (prompt only) | Self-shipping codebase |

**The Secret**: Composable Agentic Primitives
- Not about traditional SDLC
- Different compositions for different project types
- Git worktrees for agent parallelization
- Containerization for agent isolation

---

### Tactic #8: Prioritize Agentics
> **Source**: `quizzes-and-diagrams/tac-8/loot.md`

**Core Truth**: More than half your engineering time should be on the agentic layer, not the application layer.

**Minimum Viable Agentic Layer**:
- AI developer workflow directory
- Prompts (stored in `.claude/commands`)
- Plans

**Layers**:
| Layer | Contents |
|-------|----------|
| Agentic Layer | ADWs, prompts, agents, hooks |
| Application Layer | DevOps, infra, database, app code |

**The Guiding Question**: Is this work growing my agentic layer or my application layer?

---

## Part 2: Advanced Lessons

### Lesson 9: Elite Context Engineering
> **Source**: `quizzes-and-diagrams/elite-context-engineering/loot.md`

**Core Truth**: A focused agent is a performant agent. Context is your agent's most precious resource.

**R&D Framework**:
- **R**educe: Minimize unnecessary context (50%+ reduction)
- **D**elegate: Let agents retrieve context dynamically

**Context Levels**:
| Level | Skill |
|-------|-------|
| 1 | Context Curator |
| 2 | Context Engineer |
| 3 | Context Architect |
| 4 | (Bleeding edge) |

**Practical Tips**:
- Install token counter in IDE
- Delete default `.mcp.json` files (10-12% context waste)
- Use context priming over always-on memory files
- Hit the context sweet spot for max performance

**Commands**: `/measure-context`, `/load-mcp`, `/prime`

---

### Lesson 10: Agentic Prompt Engineering
> **Source**: `quizzes-and-diagrams/agentic-prompt-engineering/loot.md`

**Core Truth**: The prompt is the fundamental unit of engineering. One prompt = tens to hundreds of hours of productive work.

**7 Levels of Agentic Prompts**:

| Level | Name | Description |
|-------|------|-------------|
| 1 | High Level Prompt | Reusable ad hoc static prompt |
| 2 | Workflow Prompt | Sequential workflow with task list |
| 3 | Control Flow | Flow control for domain-specific agents |
| 4 | Delegation Prompt | Kicks off other workflows |
| 5 | Higher Order Prompt | Prompts passing prompts |
| 6 | Template Meta Prompt | Prompts that create prompts |
| 7 | Self-Improving Prompt | Agents updating agents |

**Stakeholder Trifecta**: You, Your Team, Your Agents

**Key Insight**: Level 3-4 is the 80/20 for most applications.

---

### Lesson 11: Building Specialized Agents
> **Source**: `quizzes-and-diagrams/building-specialized-agents/loot.md`

**Core Truth**: Better agents → More agents → Custom agents. Move from generic to domain-specific powerhouses.

**Agent Evolution**:
```
Prompt → Command → Hook → Agent → ADW
```

**Three Agent Execution Patterns**:

| Pattern | Type | Use Case |
|---------|------|----------|
| **Pong** | Request-Response | Simple custom agents |
| **Echo** | Event-Driven | Custom tool-enabled agents |
| **Calculator** | Tool-Heavy | Focused functionality agents |

**8 Progressive Custom Agent Examples** (from `building-domain-specific-agents`):

| Agent | Interface | Pattern | Key Learning |
|-------|-----------|---------|--------------|
| 1. Pong | CLI | Request-Response | SDK fundamentals, system prompt override |
| 2. Echo | CLI | Tool-Enabled | Custom tools with @tool decorator |
| 3. Calculator | REPL | Multi-Tool | Session continuity with `resume` |
| 4. Social Hype | CLI | Real-Time | WebSocket firehose monitoring |
| 5. QA | REPL | Parallel Search | Task deployment, controlled tool access |
| 6. Tri-Copy-Writer | Web App | Structured | JSON responses, file context |
| 7. Micro SDLC | Kanban | Orchestrated | Plan→Build→Review workflow |
| 8. Ultra Stream | Dual-Panel | Streaming | Log processing, Inspector agent |

**Agent File Template (4 Sections)**:

All agent configuration files (`.claude/agents/*.md`) must follow this structure:

```markdown
---
name: kebab-case-name
description: Action-oriented description stating WHEN to use this agent
tools: Tool1, Tool2, Tool3
model: haiku|sonnet|opus
---

# Purpose
{What this agent does and its role - one paragraph}

## Instructions
- {Guiding principle 1}
- {Guiding principle 2}

## Workflow
1. {First step}
2. {Second step}
3. {Third step}

## Report
{Output format for reporting results}
```

**Key Rules**:
- Frontmatter is REAL YAML (not a code block)
- Tools are comma-separated (not YAML list)
- Exactly 4 sections after frontmatter
- No extra sections (no "Example", "Execution", etc.)

**System Prompt Strategies**:
- **Append**: Extend Claude Code capabilities
- **Override**: Build true custom agents (WARNING: no longer Claude Code!)

**Model Selection**:
| Model | Use Case |
|-------|----------|
| Haiku | Simple, fast tasks |
| Sonnet | Balanced performance |
| Opus | Complex reasoning |

---

### Lesson 12: Multi-Agent Orchestration
> **Source**: `quizzes-and-diagrams/multi-agent-orchestration/loot.md`

**Core Truth**: Command your fleet of agents through a single interface. The rate at which you create and command agents becomes your constraint.

**Agent Evolution Path**:
```
Base agents → Better agents → More agents → Custom agents → Orchestrated agents
```

**Three Pillars**:
1. **Orchestrator Agent**: Unified interface to command all agents
2. **CRUD for Agents**: Create, Read, Update, Delete at scale
3. **Observability**: Real-time monitoring of performance, costs, results

**PETER Framework** (for Out-Loop Multi-Agent):
- **P**rompt input
- (E is implicit - Execution)
- **T**rigger (HTTP)
- **E**nvironment
- **R**eview (observability)

> **Note**: PETER is a variant of PITER for multi-agent context, emphasizing HTTP triggers and observability-based review.

---

### Lesson 13: Agent Experts
> **Source**: `quizzes-and-diagrams/agent-experts/loot.md`

**Core Truth**: The massive problem with agents is they forget. Agent Experts solve this with ACT → LEARN → REUSE.

**Two Types of Agent Experts**:

| Type | Use Case | Example |
|------|----------|---------|
| **Codebase Experts** | High-risk or complex code areas | Database, WebSocket, Billing, Security |
| **Product Experts** | Adaptive user experiences | Personalized recommendations, learning user patterns |

**Codebase Expert Domains**:
| Domain | Use Case |
|--------|----------|
| Database | Schema changes, migrations, query patterns |
| WebSocket | Real-time events, streaming architecture |
| Billing | Payment flows, subscription logic |
| Security | Auth patterns, permission systems |

**Product Expert Example** (Nile Adaptive Shopping):
```
ACT    →  User views product, adds to cart, or checks out
LEARN  →  System updates user's Expertise JSONB in database
REUSE  →  Agent generates personalized home page sections
```

**The Pattern**:
```
ACT    →  Agent takes useful action
LEARN  →  Agent stores new information in expertise file
REUSE  →  Agent uses expertise on next execution
```

**Self-Improving Template Meta Prompts**:
- Prompts that build other prompts
- Update themselves with new information
- No human in the loop required

**Expert Types**:
| Type | Use Case |
|------|----------|
| Codebase Expert | Database, WebSocket, Billing, Security |
| Domain Expert | Business rules, industry knowledge |
| Product Expert | User preferences, adaptive UX |

**Expert File Structure**:
```
.claude/commands/experts/{domain}/
├── expertise.yaml      # Mental model
├── question.md         # Query without coding
├── plan.md             # Domain-aware planning
├── self-improve.md     # Sync expertise with code
└── plan_build_improve.md  # Full workflow
```

---

### Lesson 14: The Codebase Singularity
> **Source**: `quizzes-and-diagrams/orchestrator-agent-with-adws/loot.md`

**Core Truth**: The Codebase Singularity is the moment when you realize your agents can run your codebase better than you or your team. Build Agentic Layers that accelerate you toward this singular moment.

**Agentic Layer Classification System**:

> The agentic layer wraps around your application layer. Build it progressively toward the **Codebase Singularity** - the moment your agents run your codebase better than you.

**Class 1: Foundation Agentic Layers** (In-Loop to Out-Loop)

| Grade | Name | Description |
|-------|------|-------------|
| 1.1 | Prime Prompts & Memory Files | Thinnest layer: `/prime` commands and CLAUDE.md. The foundation. |
| 1.2 | Sub-Agents, Plans & AI Docs | Specialized prompts for planning, sub-agents, and ai_docs directories. |
| 1.3 | Skills, MCPs & Custom Tools | Custom tools that enhance the Core Four. Skills bypass MCPs. |
| 1.4 | Closed-Loop Prompts | Request → Validate → Resolve. Agents review and self-correct. |
| 1.5 | Bug/Feature/Chore Templates | Type-specific output formats. Teach agents to build like YOU do. |
| 1.6 | Prompt Chains & Workflows | One prompt references many prompts/sub-agents. Plan then build. |
| 1.7 | Agent Experts | Mental models for specific codebase areas. Zero-touch emerges. |

**Class 2: Out-Loop Systems** (Minimal Human Touchpoints)

| Grade | Name | Description |
|-------|------|-------------|
| 2.1 | Webhooks & External Triggers | PITER framework. HTTP endpoints fire prompts from Slack/Jira/GitHub. |
| 2.2 | AI Developer Workflows (ADW) | Deterministic code + non-deterministic agents. Highest leverage. |

**Class 3: Orchestration Layer** (Fleet Management)

| Grade | Name | Description |
|-------|------|-------------|
| 3.1 | Orchestrator Agent | One agent to rule them all. CRUD and command other agents. |
| 3.2 | Orchestrator Dev Workflows | Multi-level conversations across multiple teams of agents. |
| 3.3 | ADWs with Orchestrator | Final level. Orchestrator runs ADWs deterministically. |

**Key Insight**: More compute = more trust. If adding agents decreases trust, you're doing something wrong.

**ADW Architecture**:
- `adw_agent_sdk.py`: Typed Pydantic wrapper
- `adw_logging.py`: Step logging, event broadcasting
- `adw_websockets.py`: Real-time updates
- `adw_summarizer.py`: AI-powered summaries

**ADW Workflow Types**:
| Type | Steps | Flow |
|------|-------|------|
| plan_build | 2 | /plan → /build |
| plan_build_review | 3 | /plan → /build → /review |
| plan_build_review_fix | 4 | /plan → /build → /review → /fix |

**ADW OAuth Limitation** ⚠️:
> **See**: [[adw-oauth-limitation.md]] for full details and workaround scripts

Claude Code Pro/Max OAuth tokens (`sk-ant-oat01-...`) do NOT work with ADWs programmatically. Neither `anthropic` SDK nor `claude_agent_sdk` accepts OAuth tokens.

| Workaround | Trade-off |
|------------|-----------|
| CLI subprocess | No streaming/hooks/swimlanes |
| GitHub Actions | No real-time UI, cold start latency |
| Anthropic API key | Full features (recommended) |

---

### Software Delivery ADW (Repository Reference)
> **Source**: `Desktop/tac/software-delivery-adw/` | **Note**: Not a TAC lesson, but a practical implementation

**29 Commands** covering the full software delivery lifecycle
**12 ADWs** for automated workflows
**14 Scoping File Commands** for comprehensive planning

Key phases: Discovery → Requirements → Planning → Development → Testing → Review → Deployment

---

## Part 3: Reference Catalogs

### Index Directories
| Catalog | Location | Count | Purpose |
|---------|----------|-------|---------|
| ADWs | `index/adws/README.md` | 130+ | Agentic Development Workflows |
| Agents | `index/agents/README.md` | 16 | Agent templates |
| Commands | `index/commands/README.md` | 388+ | Slash commands |
| Hooks | `index/hooks/README.md` | 80+ | Lifecycle hooks |
| Skills | `index/skills/README.md` | 21 | Skill packages |

### Desktop/tac Projects (20 directories)

**Core Tactics (8)**:
| Directory | Lesson | Topic |
|-----------|--------|-------|
| `tac-1` | L01 | Stop Coding |
| `tac-2` | L02 | Adopt Your Agent's Perspective |
| `tac-3` | L03 | Template Your Engineering |
| `tac-4` | L04 | Stay Out The Loop (PITER) |
| `tac-5` | L05 | Always Add Feedback Loops |
| `tac-6` | L06 | One Agent, One Prompt, One Purpose |
| `tac-7` | L07 | Target Zero-Touch Engineering |
| `tac-8` | L08 | Prioritize Agentics |

**Advanced Lessons (6)**:
| Directory | Lesson | Focus |
|-----------|--------|-------|
| `rd-framework-context-window-mastery` | L09 | Elite Context Engineering (R&D) |
| `seven-levels-agentic-prompt-formats` | L10 | Agentic Prompt Engineering (7 Levels) |
| `building-domain-specific-agents` | L11 | Pong/Echo/Calculator agents |
| `multi-agent-orchestration-the-o-agent` | L12 | Fleet management |
| `agent-experts` | L13 | ACT-LEARN-REUSE patterns |
| `orchestrator-agent-with-adws` | L14 | Full-stack orchestration + Codebase Singularity |

**Additional Specialized Projects (6+)**:
| Directory | Focus |
|-----------|-------|
| `agentic-finance-review` | Self-validating finance agents |
| `claude-code-hooks-mastery` | PreToolUse/PostToolUse hooks |
| `claude-code-damage-control` | Security via path protection |
| `agent-sandboxes` | E2B SDK progressive learning |
| `agent-sandbox-skill` | Full-stack sandbox skill |
| `fork-repository-skill` | Multi-agent terminal forking |
| `claude-code-hooks-mastery` | --- | Hooks deep dive |
| `claude-code-damage-control` | --- | Defense-in-depth safety |
| `agent-sandboxes` | --- | Environment isolation |
| `agent-sandbox-skill` | --- | Sandbox skill template |
| `fork-repository-skill` | --- | Fork repository skill |

---

## Part 4: Core Frameworks Summary

### PITER Framework
**P**rompt → **I**nput → **T**rigger → **E**nvironment → **R**eview

### R&D Framework
**R**educe context + **D**elegate to agents

### ACT-LEARN-REUSE
**ACT** (take action) → **LEARN** (store knowledge) → **REUSE** (apply on next run)

### Core Four
**C**ontext + **M**odel + **P**rompt + **T**ools

### The 8 Tactics (Memory Aid)
1. **S**top Coding
2. **A**dopt Agent's Perspective
3. **T**emplate Your Engineering
4. **S**tay Out The Loop
5. **A**lways Add Feedback Loops
6. **O**ne Agent, One Prompt, One Purpose
7. **T**arget Zero-Touch Engineering
8. **P**rioritize Agentics

---

## Validation Sources

### Theory Files (14 TAC Lessons)
**Core Tactics (Lessons 1-8)**:
- `quizzes-and-diagrams/tac-1/loot.md` - Stop Coding
- `quizzes-and-diagrams/tac-2/loot.md` - Adopt Your Agent's Perspective
- `quizzes-and-diagrams/tac-3/loot.md` - Template Your Engineering
- `quizzes-and-diagrams/tac-4/loot.md` - Stay Out The Loop
- `quizzes-and-diagrams/tac-5/loot.md` - Always Add Feedback Loops
- `quizzes-and-diagrams/tac-6/loot.md` - One Agent, One Prompt, One Purpose
- `quizzes-and-diagrams/tac-7/loot.md` - Target Zero-Touch Engineering
- `quizzes-and-diagrams/tac-8/loot.md` - Prioritize Agentics

**Advanced Lessons (Lessons 9-14)**:
- `quizzes-and-diagrams/elite-context-engineering/loot.md` - L09: R&D Framework
- `quizzes-and-diagrams/agentic-prompt-engineering/loot.md` - L10: 7 Levels
- `quizzes-and-diagrams/building-specialized-agents/loot.md` - L11: Agent Patterns
- `quizzes-and-diagrams/multi-agent-orchestration/loot.md` - L12: Orchestrator
- `quizzes-and-diagrams/agent-experts/loot.md` - L13: ACT-LEARN-REUSE
- `quizzes-and-diagrams/orchestrator-agent-with-adws/loot.md` - L14: Codebase Singularity

**Repository Reference** (not a lesson):
- `quizzes-and-diagrams/software-delivery-adw/README.md` - Implementation example

### Project READMEs (25 total)
- Core: `tac-1` through `tac-8` (8 + 5 sub-apps)
- Specialized: 12 project directories

---

## Part 5: TAC-Compliant Hooks Architecture

### The Hook Organization Problem

Many projects accumulate domain-specific hooks in separate folders:
```
hooks/
├── aws/           ❌ Non-TAC domain folder
├── git/           ❌ Non-TAC domain folder
├── dev/           ❌ Non-TAC domain folder
├── pre_tool_use.py
└── post_tool_use.py
```

This violates TAC's flat hook structure principle.

### TAC Hook Pattern

**Core Rule**: Lifecycle hooks stay flat at root, only `utils/` subfolder allowed.

```
hooks/
├── pre_tool_use.py      # Lifecycle hook (root)
├── post_tool_use.py     # Lifecycle hook (root)
├── session_start.py     # Lifecycle hook (root)
├── stop.py              # Lifecycle hook (root)
└── utils/               # Only allowed subfolder
    ├── dispatcher.py    # Pattern-based routing
    ├── hook_utils.py    # Shared utilities
    ├── aws/             # Domain handlers (ISOLATED)
    │   ├── command_watcher.py
    │   └── post_command.py
    ├── git/             # Domain handlers (ISOLATED)
    │   ├── worktree_watcher.py
    │   └── commit_watcher.py
    └── dev/             # Domain handlers (ISOLATED)
        ├── dangerous_blocker.py
        └── file_logger.py
```

### The Dispatcher Pattern

The dispatcher provides pattern-based routing from lifecycle hooks to domain handlers:

```python
# utils/dispatcher.py
PRE_TOOL_HANDLERS = {
    "Bash": [
        ("aws ", "aws.command_watcher", "handle"),
        ("git worktree", "git.worktree_watcher", "handle"),
        ("rm ", "dev.dangerous_blocker", "handle"),
    ],
}

def dispatch_pre_tool(tool_name, tool_input):
    """Route to matching domain handlers."""
    handlers = PRE_TOOL_HANDLERS.get(tool_name, [])
    command = tool_input.get("command", "")

    for pattern, module, func in handlers:
        if pattern in command:
            handler = load_handler(module, func)
            result = handler(tool_name, tool_input)
            if result and result.get("block"):
                return result
    return None
```

### Domain Handler Interface

Each domain handler exports a `handle` function:

```python
# utils/aws/command_watcher.py
def handle(tool_name: str, tool_input: dict) -> Optional[dict]:
    """
    PreToolUse handler for AWS commands.

    Returns:
        None to allow, or {"block": True, "reason": "..."} to block
    """
    command = tool_input.get("command", "")
    log_hook_activity("aws_command_watcher", {"command": command})
    return None  # Allow
```

### Simplified settings.json

With the dispatcher, settings.json becomes minimal:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "",
      "hooks": [{"type": "command", "command": "uv run .claude/hooks/pre_tool_use.py"}]
    }],
    "PostToolUse": [{
      "matcher": "",
      "hooks": [{"type": "command", "command": "uv run .claude/hooks/post_tool_use.py"}]
    }]
  }
}
```

### Benefits of TAC-Compliant Hooks

| Aspect | Non-TAC | TAC-Compliant |
|--------|---------|---------------|
| Structure | Domain folders at root | Flat + utils/ |
| Entry Points | Multiple per domain | Single per event |
| settings.json | Complex (many hooks) | Simple (one per event) |
| Domain Isolation | Yes (folders) | Yes (utils subfolders) |
| TAC Validator Score | 55/100 | 100/100 |
| Adding Domains | Create folder + update settings | Add handler + update dispatcher |

### Migration Steps

1. **Create dispatcher**: `utils/dispatcher.py` with handler routing
2. **Move handlers**: `hooks/{domain}/` → `utils/{domain}/`
3. **Refactor handlers**: Export `handle(tool_name, tool_input)` function
4. **Update lifecycle hooks**: Import and call dispatcher
5. **Simplify settings.json**: Single hook per event type
6. **Remove old folders**: `git rm -r hooks/{domain}/`
7. **Validate**: Run `/tac-organizer:organize`

---

## Part 6: Advanced Hook Patterns

### Stop Hook Filtering by Reason Field

Stop hooks receive a `reason` field in their JSON payload that indicates the stop context:

| Reason Value | Description | Use Case |
|-------------|-------------|----------|
| `turn_end` | Single turn completed | Turn-by-turn memory logging |
| `session_end` | Full session ending | Session summary, cleanup |
| `user_interrupt` | User interrupted | Save partial state |

**settings.json Matcher Configuration**:
```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "turn_end",
        "hooks": [{"type": "command", "command": "uv run .claude/hooks/turn_memory_hook.py"}]
      },
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "uv run .claude/hooks/session_stop.py"}]
      }
    ]
  }
}
```

### Hook Chaining Pattern

Hooks can be chained to build on each other's output:

```
Turn Hook (runs first)
    └─> Writes to /memories/turns/YYYY-MM-DD/turn_001.md
    └─> Updates /memories/context/current_focus.md

Session Hook (runs later)
    └─> Reads turn logs from /memories/turns/
    └─> Creates session summary in /memories/sessions/
```

**Key Insight**: Turn hooks run on every `turn_end`, building incremental context. Session hooks can then aggregate this data when the full session concludes.

### Turn-by-Turn Memory Architecture

Directory structure for persistent memory across sessions:

```
/memories/
├── turns/
│   └── YYYY-MM-DD/           # Date-organized turn logs
│       ├── turn_001.md
│       ├── turn_002.md
│       └── ...
├── decisions/                # Key decisions extracted from turns
│   └── decision_TIMESTAMP.md
├── context/                  # Live context files
│   ├── current_focus.md      # What agent is working on
│   └── active_files.md       # Files being modified
└── sessions/                 # Session-level summaries
    └── session_TIMESTAMP.md
```

### Lightweight Turn Classification

Classify turns without API calls (< 5s execution requirement):

```python
def classify_turn(transcript: str) -> str:
    """Lightweight classification based on keywords."""
    patterns = {
        "code_change": ["Edit", "Write", "created", "modified"],
        "investigation": ["Read", "Grep", "Glob", "searched"],
        "decision": ["decided", "chose", "selected", "will use"],
        "error_handling": ["error", "failed", "fix", "retry"],
    }

    for category, keywords in patterns.items():
        if any(kw.lower() in transcript.lower() for kw in keywords):
            return category
    return "general"
```

### Memory Tool Path Validation

The Anthropic Memory Tool spec requires path validation to prevent traversal attacks:

```python
def validate_memory_path(path: str, base_dir: str) -> bool:
    """Prevent directory traversal attacks."""
    resolved = os.path.realpath(path)
    base = os.path.realpath(base_dir)
    return resolved.startswith(base + os.sep)
```

**Security Rules**:
- All memory writes must be within designated `/memories/` directory
- Reject paths containing `..` or absolute paths outside base
- Sanitize user-provided filenames before use

---

## Part 7: Claude Code Ecosystem Graph

> **Purpose**: Track relationships between Claude Code repositories, components, and emergent patterns.

### Core Principle: Component-Centric

The ecosystem graph centers on **components** (agents, commands, hooks, skills, ADWs) - the actual Claude Code primitives - not lessons or fixed categories.

```
REPOSITORY → contains → COMPONENTS → implements → PATTERNS → tagged → CONCEPTS
```

### Layer Architecture

| Layer | Contents | Examples |
|-------|----------|----------|
| **Repository** | Git repos with Claude Code components | agentic-finance-review, claude-code-damage-control |
| **Component** | Claude Code primitives | Agent, Command, Hook, Skill, ADW, Validator |
| **Pattern** | Emergent designs discovered across repos | PostToolUse Validation, Meta-Agent, Dispatcher |
| **Concept** | Metadata tags (not structure) | PITER, R&D, ACT-LEARN-REUSE, feedback-loops |

### Repository Index (20 directories)

> **Processing Command**: `/tac-process-directory --list` shows all directories with processing status.

**Core Tactics (tac-1 through tac-8)**:

| Repository | Tactic | Focus |
|------------|--------|-------|
| tac-1 | Stop Coding | Core Four, Commander of Compute |
| tac-2 | Adopt Agent's Perspective | 12 Leverage Points, Agentic KPIs |
| tac-3 | Template Your Engineering | Meta-prompts, plans in `specs/` |
| tac-4 | Stay Out The Loop | PITER framework, AFK agents |
| tac-5 | Always Add Feedback Loops | Validation, closed-loop execution |
| tac-6 | One Agent, One Prompt | Specialized agents, context focus |
| tac-7 | Target Zero-Touch | ZTE workflow, autonomy levels |
| tac-8 | Prioritize Agentics | Agentic layer > Application layer |

**Advanced Implementations (12 directories)**:

| Repository | Lesson | Key Components |
|------------|--------|----------------|
| rd-framework-context-window-mastery | L09 | R&D framework, context optimization |
| seven-levels-agentic-prompt-formats | L10 | 7 prompt levels, HOPs |
| building-domain-specific-agents | L11 | Pong, Echo, Calculator patterns |
| multi-agent-orchestration-the-o-agent | L12 | 6 agents, 14 commands, fleet management |
| agent-experts | L13 | Expert systems, ACT-LEARN-REUSE |
| orchestrator-agent-with-adws | L14 | Full ADW stack, Codebase Singularity |
| agentic-finance-review | --- | 6 agents, 12 commands, 8 validators |
| claude-code-hooks-mastery | --- | All hook types, meta-agents |
| claude-code-damage-control | --- | PreToolUse blocking, path protection |
| agent-sandboxes | --- | Multi-environment, git worktrees |
| agent-sandbox-skill | --- | Skill packaging, sandbox execution |
| fork-repository-skill | --- | Skill distribution pattern |

### Pattern Index

| Pattern | Type | Repos Implementing |
|---------|------|-------------------|
| **PostToolUse Validation** | hook | agentic-finance-review |
| **PreToolUse Blocking** | hook | claude-code-damage-control |
| **Dispatcher** | hook | multi-agent-orchestration |
| **Meta-Agent** | agent | multi-agent-orchestration |
| **Calculator Agent** | agent | agentic-finance-review |
| **Scout-Plan-Build** | workflow | multi-agent-orchestration |
| **Skill Distribution** | skill | agent-sandbox-skill, claude-code-damage-control |

### Edge Types

| Edge | From → To | Meaning |
|------|-----------|---------|
| **contains** | Repository → Component | Source contains this component |
| **invokes** | Command/ADW → Agent/Command | Triggers execution |
| **uses** | Agent/Command → Hook | Uses during execution |
| **validates** | Validator → Output | Validates this output type |
| **implements** | Component → Pattern | Demonstrates this pattern |
| **tagged** | Any → Concept | Associated with concept |

### tac-manifest.yaml

Repositories can include an annotation manifest for automatic graph population:

```yaml
# .claude/tac-manifest.yaml
schema_version: "1.0"

repository:
  name: "repo-name"
  url: "https://github.com/..."
  author: "IndyDevDan"
  themes: [validation, self-correction]

components:
  agents:
    - name: "csv-edit-agent"
      pattern: "Calculator"
      hooks: [PostToolUse]

  hooks:
    - name: "csv-validator"
      event: "PostToolUse"
      validates: [csv]

patterns:
  - name: "Self-Validating Agents"
    type: "architecture"

relationships:
  - from: "csv-edit"
    to: "csv-edit-agent"
    type: "invokes"
```

### Knowledge Graph Location

The full ecosystem graph schema is documented in:
- **Obsidian**: `AI-Agent-KB/_SCHEMA.md` → Claude Code Ecosystem Graph section
- **Taxonomy**: `AI-Agent-KB/_TAXONOMY.md` → Repository Categories section
- **Repository Notes**: `AI-Agent-KB/12-Repositories/`

### Update Workflow

1. **Trigger**: New repo released or existing repo updated
2. **Scan**: Auto-detect components in `.claude/` directory
3. **Generate**: Create/update `tac-manifest.yaml` skeleton
4. **Pattern Discovery**: If pattern in 2+ repos → add to registry
5. **Sync**: Update Obsidian notes and backlinks
6. **Validate**: Check edge targets exist, no duplicates

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Component-centric | Components as nodes, not lessons | Ecosystem evolves beyond original 8 tactics |
| Patterns emergent | Discovered from repos | New patterns will emerge |
| Repository as entity | Track source of components | Know where things come from |
| Schema extensible | Document extension process | Anthropic will release new features |

### Context Files for Session Continuity

Context files enable agents to resume work across sessions:

**current_focus.md**:
```markdown
# Current Focus
Last Updated: 2025-01-22T15:30:00Z

## Active Task
Implementing turn-by-turn memory hooks

## Key Context
- Working in claude-code-hooks-mastery project
- Building memory integration with Anthropic spec
- Files modified: hooks/turn_memory_hook.py, settings.json

## Next Steps
1. Test turn classification accuracy
2. Add session summary generation
```

**active_files.md**:
```markdown
# Active Files
Last Updated: 2025-01-22T15:30:00Z

| File | Status | Last Modified |
|------|--------|---------------|
| hooks/turn_memory_hook.py | Modified | 15:25 |
| settings.json | Modified | 15:20 |
| memories/context/current_focus.md | Updated | 15:30 |
```

### Hook Execution Environment

| Property | Value | Notes |
|----------|-------|-------|
| Timeout | 60 seconds | Per hook execution |
| Parallelization | All matching hooks | Run simultaneously |
| Working Directory | Project root | Access to codebase |
| Input | JSON via stdin | Session + tool data |
| Output | stdout/stderr + exit code | Control flow |

### Best Practices for Memory Hooks

1. **Keep turns lightweight**: < 5s execution, no API calls for classification
2. **Use atomic writes**: Write to temp file, then rename to prevent corruption
3. **Limit file growth**: Rotate or archive old turn logs periodically
4. **Index for retrieval**: Maintain index files for quick lookups
5. **Validate all paths**: Prevent security issues with path traversal
6. **Handle failures gracefully**: Memory hooks should never block agent operation
