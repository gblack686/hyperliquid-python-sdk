---
type: expert-file
parent: "[[tac/_index]]"
file-type: command
command-name: "plan"
human_reviewed: false
tac_original: true
tags: [expert-file, command, planning, hop]
---

# TAC Expert - Plan Mode

> Higher Order Prompt (HOP) that wraps `/plan` with TAC methodology expertise.

## Purpose
Create TAC-informed implementation plans that apply the 8 tactics and TAC frameworks to the user's request. This ensures plans follow agentic coding best practices.

## Usage
```
/experts:tac:plan [user_request]
```

## Allowed Tools
`Task`, `Read`, `SlashCommand`, `TodoWrite`, `Grep`, `Glob`, `Bash`

---

## CRITICAL: TAC Knowledge Retrieval

**For TAC methodology questions during planning, invoke the `tac` agent.**

The TAC knowledge base is external to this repository.

### When to Invoke tac

- To look up specific tactics (Tactic #1-8)
- To reference frameworks (PITER, R&D, Core Four, ACT-LEARN-REUSE)
- To find agent patterns (Pong, Echo, Calculator)
- To check ADW catalogs or command catalogs

### Invocation Pattern

```
Task(
  subagent_type: "tac",
  model: "haiku",
  prompt: "What is the recommended approach for [specific TAC concept]?"
)
```

---

## TAC-Informed Planning Framework

### Step 1: Problem Class Analysis (Tactic #1, #3)

**Stop Coding** - Identify if this is a coding task or an agentic task.

| Task Type | Approach |
|-----------|----------|
| One-off fix | Simple prompt, no template |
| Repeating pattern | Create/use template |
| Problem class | Build ADW |
| Complex system | Multi-agent orchestration |

**Template Your Engineering** - Does a template exist for this problem class?
- Check `index/commands/README.md` for existing templates
- Check `index/adws/README.md` for existing ADWs

---

### Step 2: Autonomy Level Analysis (Tactic #4, #7)

Determine the target autonomy level:

| Level | Human Touchpoints | When to Use |
|-------|-------------------|-------------|
| **In-Loop** | Many | Complex, novel problems requiring iteration |
| **Out-Loop** | 2 (prompt + review) | Well-defined problems with clear validation |
| **Zero-Touch** | 1 (prompt only) | Highly repeatable, proven workflows |

**PITER Framework Check**:
- [ ] **P**rompt: Is input well-defined?
- [ ] **T**rigger: Can this be automated?
- [ ] **E**nvironment: Isolated execution possible?
- [ ] **R**eview: Automated validation available?

---

### Step 3: Primitive Selection (Tactic #8)

**Prioritize Agentics** - Select the right primitives:

| Primitive | Use When |
|-----------|----------|
| Command | Reusable prompt pattern |
| Hook | Event-driven automation |
| Agent | Dedicated single-purpose execution |
| ADW | Multi-step workflow |
| Orchestrator | Multi-agent coordination |

---

### Step 4: Validation Strategy (Tactic #5)

**Always Add Feedback Loops** - Define validation approach:

```yaml
validation:
  linting: [list linters to run]
  unit_tests: [test files/commands]
  integration_tests: [integration test commands]
  e2e_tests: [e2e test commands]
  build_check: [build commands]
  custom_evals: [custom evaluation commands]
```

---

### Step 5: Context Engineering (Tactic #6, R&D Framework)

**One Agent, One Prompt, One Purpose** - Plan context:

| Question | Analysis |
|----------|----------|
| What context is required? | List files, docs, types |
| What context can be reduced? | Identify bloat |
| What context can be delegated? | Dynamic retrieval |

**R&D Analysis**:
- **Reduce**: What can be excluded from initial context?
- **Delegate**: What should agents retrieve on-demand?

---

### Step 6: Agent Pattern Selection

Based on `building-specialized-agents/loot.md`:

| Pattern | When to Use |
|---------|-------------|
| **Pong** | Simple request-response |
| **Echo** | Event-driven with custom tools |
| **Calculator** | Tool-heavy focused functionality |

---

### Step 7: Orchestration Decision

Based on complexity:

| Complexity | Approach |
|------------|----------|
| Single task | One agent |
| Multi-step workflow | ADW (plan_build, plan_build_review) |
| Multi-domain | Multi-agent orchestration |
| Fleet management | Orchestrator pattern |

---

## Workflow

1. **Load TAC Expertise Context**
   - Read `expertise.md` for mental model
   - Identify relevant tactics for the request
   - Reference specific loot.md files if needed

2. **Apply TAC Analysis**
   - Problem class analysis
   - Autonomy level determination
   - Primitive selection
   - Validation strategy
   - Context engineering
   - Agent pattern selection
   - Orchestration decision

3. **Execute Planning with Context**
   - Call `/plan` with the user request
   - Planning is now informed by TAC expertise
   - Include TAC-specific recommendations

---

## Plan Output Format

```markdown
# TAC-Informed Plan: {Title}

## TAC Analysis

### Problem Classification
- **Type**: {one-off | pattern | problem-class | complex-system}
- **Existing Templates**: {list or "none"}
- **Tactic Focus**: {primary tactics to apply}

### Autonomy Target
- **Level**: {In-Loop | Out-Loop | Zero-Touch}
- **PITER Status**: {assessment}

### Primitives Required
- {primitive 1}: {purpose}
- {primitive 2}: {purpose}

### Agent Pattern
- **Pattern**: {Pong | Echo | Calculator | Multi-Agent}
- **Reason**: {why this pattern}

## Implementation Plan

### Context Requirements
| Required | Source | Load Method |
|----------|--------|-------------|
| {context 1} | {path} | {static | dynamic} |

### Validation Strategy
- [ ] {validation step 1}
- [ ] {validation step 2}

### Steps
1. {Step 1}
2. {Step 2}
3. {Step 3}

### Success Criteria
- {criterion 1}
- {criterion 2}

## Recommended Workflow
{plan_build | plan_build_review | plan_build_review_fix | custom}
```

---

## Examples

### Example 1: Simple Feature
```
/experts:tac:plan "Add a logout button to the header"
```

**TAC Analysis**:
- Type: One-off (unless similar patterns exist)
- Autonomy: In-Loop (need design decisions)
- Primitive: Command
- Pattern: Pong
- Validation: Unit test + visual check

### Example 2: Repeating Pattern
```
/experts:tac:plan "Add CRUD endpoints for the new Product entity"
```

**TAC Analysis**:
- Type: Pattern (CRUD is repeatable)
- Autonomy: Out-Loop (well-defined)
- Primitive: Template + ADW
- Pattern: Calculator (tool-heavy)
- Validation: API tests + type checks

### Example 3: Complex System
```
/experts:tac:plan "Implement real-time notifications with WebSocket"
```

**TAC Analysis**:
- Type: Complex system
- Autonomy: In-Loop → Out-Loop (iterative)
- Primitive: Agent + ADW
- Pattern: Multi-Agent (backend + frontend agents)
- Validation: Integration tests + e2e tests

---

## Key Insight
> The expertise file is your **mental model** - validate claims against the source loot.md files before planning. Use TAC principles to create plans that maximize agent success.
