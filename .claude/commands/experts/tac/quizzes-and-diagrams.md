---
type: expert-file
parent: "[[tac/_index]]"
file-type: reference
human_reviewed: false
tac_original: true
tags: [expert-file, quizzes, diagrams, assessment]
---

# TAC Quizzes and Diagrams Reference

> **Source**: `TAC-Learning-System/quizzes-and-diagrams/`

This file provides references to all TAC assessment materials and visual diagrams. Use this for study, validation, and visual understanding of TAC concepts.

---

## Quizzes (15 Assessment Files)

### Core Tactics (8 Quizzes)

| Lesson | Quiz Location | Topics |
|--------|--------------|--------|
| TAC-1 | `quizzes-and-diagrams/tac-1/quiz.md` | Stop Coding, Core Four, Phase 2 Engineering |
| TAC-2 | `quizzes-and-diagrams/tac-2/quiz.md` | 12 Leverage Points, Agent Perspective |
| TAC-3 | `quizzes-and-diagrams/tac-3/quiz.md` | Templates, Meta-Prompts, HOPs |
| TAC-4 | `quizzes-and-diagrams/tac-4/quiz.md` | AFK Agents, PITER Framework |
| TAC-5 | `quizzes-and-diagrams/tac-5/quiz.md` | Feedback Loops, Closed-Loop Systems |
| TAC-6 | `quizzes-and-diagrams/tac-6/quiz.md` | Specialized Agents, Context Focus |
| TAC-7 | `quizzes-and-diagrams/tac-7/quiz.md` | ZTE, Composable Primitives |
| TAC-8 | `quizzes-and-diagrams/tac-8/quiz.md` | Agentic Layer, Prioritization |

### Advanced Lessons (7 Quizzes)

| Lesson | Quiz Location | Topics |
|--------|--------------|--------|
| Elite Context Engineering | `quizzes-and-diagrams/elite-context-engineering/quiz.md` | R&D Framework, Context Sweet Spot |
| Agentic Prompt Engineering | `quizzes-and-diagrams/agentic-prompt-engineering/quiz.md` | 7 Prompt Levels |
| Building Specialized Agents | `quizzes-and-diagrams/building-specialized-agents/quiz.md` | Pong/Echo/Calculator Patterns |
| Multi-Agent Orchestration | `quizzes-and-diagrams/multi-agent-orchestration/quiz.md` | Three Pillars, PETER |
| Orchestrator with ADWs | `quizzes-and-diagrams/orchestrator-agent-with-adws/quiz.md` | ADW Integration |
| Agent Experts | `quizzes-and-diagrams/agent-experts/quiz.md` | ACT-LEARN-REUSE |
| Software Delivery ADW | `quizzes-and-diagrams/software-delivery-adw/quiz.md` | 9 Phases |

---

## Master Answer Key

**Location**: `tac-learning-system/ANSWER_KEY.md`

**Total Questions**: 253 across all quizzes

| Category | Question Count |
|----------|---------------|
| Core Tactics (1-8) | ~160 questions |
| Advanced Lessons (9-15) | ~93 questions |

---

## Visual Diagrams (12 Excalidraw Files)

**Location**: `quizzes-and-diagrams/diagrams/`

### Framework Diagrams

| Diagram | File | Visualizes |
|---------|------|------------|
| Core Four | `core-four.excalidraw` | Context, Model, Prompt, Tools |
| 12 Leverage Points | `12-leverage-points.excalidraw` | In-Agent + Through-Agent levers |
| PITER Framework | `piter-framework.excalidraw` | Prompt, Input, Trigger, Environment, Review |

### Workflow Diagrams

| Diagram | File | Visualizes |
|---------|------|------------|
| ZTE Workflow | `zte-workflow.excalidraw` | Zero-Touch Engineering flow |
| ADW Architecture | `adw-architecture.excalidraw` | ADW component structure |
| Agent Evolution | `agent-evolution.excalidraw` | Prompt → Command → Hook → Agent → ADW |

### Concept Diagrams

| Diagram | File | Visualizes |
|---------|------|------------|
| TAC Master Part 1 | `tac-master-part1.excalidraw` | Tactics 1-4 overview |
| TAC Master Part 2 | `tac-master-part2.excalidraw` | Tactics 5-8 overview |
| TAC Paradigm Shift | `tac-paradigm-shift.excalidraw` | Phase 1 → Phase 2 transition |
| Agentic Layer | `agentic-layer.excalidraw` | Application vs Agentic layer |
| 7 Prompt Levels | `7-prompt-levels.excalidraw` | Prompt hierarchy visualization |

---

## Index Catalogs

**Location**: `quizzes-and-diagrams/index/`

| Catalog | File | Contents |
|---------|------|----------|
| ADWs | `index/adws/README.md` | 80+ AI Developer Workflow patterns |
| Agents | `index/agents/README.md` | Agent definitions and configurations |
| Commands | `index/commands/README.md` | 100+ battle-tested commands |
| Hooks | `index/hooks/README.md` | Hook patterns and examples |
| Skills | `index/skills/README.md` | Skill definitions |

---

## Transcript Reference

**Location**: `quizzes-and-diagrams/transcripts/TRANSCRIPT_INDEX.md`

Full video transcripts for all 15 lessons, useful for:
- Deep-dive understanding
- Quote extraction
- Content verification

---

## Assessment Difficulty Levels

| Level | Lessons | Focus |
|-------|---------|-------|
| Beginner | TAC-1, TAC-2 | Foundations, Core Four |
| Intermediate | TAC-3, TAC-4, TAC-5, Elite Context, Agentic Prompts | Templates, AFK, Feedback |
| Advanced | TAC-6, TAC-7, TAC-8, Building Agents, Multi-Agent, Orchestrator, Experts, SDLC ADW | ZTE, Orchestration, Learning |

---

## Usage

### For Self-Assessment
1. Read the loot.md for a lesson
2. Take the corresponding quiz.md
3. Check answers against ANSWER_KEY.md

### For Visual Learning
1. Open diagrams in Excalidraw
2. Reference while reading loot.md files
3. Use for presentations and team training

### For Agent Queries
```
/experts:tac:question "Explain the 7 prompt levels diagram"
```
→ Reads `7-prompt-levels.excalidraw` context and explains

```
/experts:tac:question "What are the quiz topics for TAC-5?"
```
→ Returns: Feedback Loops, Closed-Loop Systems, Agentic KPIs
