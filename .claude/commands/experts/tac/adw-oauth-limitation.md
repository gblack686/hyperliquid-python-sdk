# ADW OAuth Token Limitation

> **Issue**: Claude Code Max OAuth tokens (`sk-ant-oat01-...`) cannot be used with ADWs programmatically.

## The Problem

OAuth tokens from Claude Code Pro/Max plans only work for **interactive Claude Code sessions**, not programmatic API access.

### Test Results

| SDK | OAuth Works? | Error |
|-----|-------------|-------|
| `anthropic` SDK | ❌ No | `AuthenticationError: invalid x-api-key` |
| `claude_agent_sdk` | ❌ No | `Invalid API key · Fix external API key` |
| `claude` CLI | ✅ Yes | Interactive sessions work |

### Root Cause

The OAuth token (`sk-ant-oat01-...`) is specifically scoped for Claude Code's interactive authentication flow, not direct API calls through any SDK.

---

## Workaround: CLI Subprocess Approach

Since the `claude` CLI works with OAuth, spawn it as a subprocess instead of using the SDK directly.

### Basic Implementation

```python
# adw_cli_executor.py
import subprocess
import json
import os
from pathlib import Path

def execute_claude_cli(
    prompt: str,
    working_dir: str | None = None,
    max_turns: int = 50,
    allowed_tools: list[str] | None = None,
    output_format: str = "json"
) -> dict:
    """
    Execute Claude via CLI subprocess (works with OAuth token).

    Args:
        prompt: The prompt to send to Claude
        working_dir: Working directory for the agent
        max_turns: Maximum turns before stopping
        allowed_tools: List of allowed tools (e.g., ["Read", "Write", "Bash"])
        output_format: Output format ("json" or "text")

    Returns:
        dict with 'success', 'output', 'error' keys
    """
    cmd = ["claude", "-p", prompt]

    if output_format == "json":
        cmd.extend(["--output-format", "json"])

    if max_turns:
        cmd.extend(["--max-turns", str(max_turns)])

    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=working_dir or os.getcwd(),
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            return {
                "success": True,
                "output": result.stdout,
                "error": None
            }
        else:
            return {
                "success": False,
                "output": result.stdout,
                "error": result.stderr
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": None,
            "error": "Execution timed out after 600 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "error": str(e)
        }
```

### ADW Step Executor (CLI-based)

```python
# adw_cli_step.py
import asyncio
from pathlib import Path

async def run_step_via_cli(
    step_name: str,
    prompt: str,
    working_dir: str,
    adw_id: str
) -> dict:
    """
    Run an ADW step using CLI subprocess.

    Works with OAuth token since it uses claude CLI internally.
    """
    from adw_cli_executor import execute_claude_cli

    # Log step start
    print(f"[ADW {adw_id}] Starting step: {step_name}")

    # Execute via CLI
    result = execute_claude_cli(
        prompt=prompt,
        working_dir=working_dir,
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
    )

    # Log step end
    status = "completed" if result["success"] else "failed"
    print(f"[ADW {adw_id}] Step {step_name}: {status}")

    return {
        "step": step_name,
        "success": result["success"],
        "output": result["output"],
        "error": result["error"]
    }


async def run_plan_build_via_cli(
    prompt: str,
    working_dir: str,
    adw_id: str
) -> dict:
    """
    Run plan_build workflow using CLI subprocess.
    """
    # Step 1: Plan
    plan_result = await run_step_via_cli(
        step_name="plan",
        prompt=f"/plan {prompt}",
        working_dir=working_dir,
        adw_id=adw_id
    )

    if not plan_result["success"]:
        return {"success": False, "error": f"Plan step failed: {plan_result['error']}"}

    # Find the spec file from plan output
    # (Parse output to find spec path)
    spec_path = extract_spec_path(plan_result["output"])

    # Step 2: Build
    build_result = await run_step_via_cli(
        step_name="build",
        prompt=f"/build {spec_path}",
        working_dir=working_dir,
        adw_id=adw_id
    )

    return {
        "success": build_result["success"],
        "plan_output": plan_result["output"],
        "build_output": build_result["output"],
        "error": build_result["error"]
    }


def extract_spec_path(plan_output: str) -> str:
    """Extract spec file path from plan command output."""
    # Look for specs/ path in output
    import re
    match = re.search(r'specs/[\w\-]+\.md', plan_output)
    if match:
        return match.group(0)
    return "specs/latest.md"  # Fallback
```

### Worktree + CLI Integration

```python
# worktree_cli_adw.py
import subprocess
import os

def init_worktree(worktree_name: str, target_dir: str) -> str:
    """Initialize a git worktree for isolated execution."""
    worktree_path = f"trees/{worktree_name}"

    # Create worktree with sparse checkout
    subprocess.run([
        "git", "worktree", "add", "--no-checkout",
        worktree_path, "-b", worktree_name
    ], check=True)

    # Configure sparse checkout
    subprocess.run([
        "git", "-C", worktree_path,
        "sparse-checkout", "init", "--cone"
    ], check=True)

    subprocess.run([
        "git", "-C", worktree_path,
        "sparse-checkout", "set", target_dir
    ], check=True)

    subprocess.run([
        "git", "-C", worktree_path, "checkout"
    ], check=True)

    return os.path.abspath(worktree_path)


def run_adw_in_worktree(
    worktree_name: str,
    target_dir: str,
    prompt: str
) -> dict:
    """
    Run ADW in isolated worktree using CLI subprocess.

    Combines TAC worktree pattern with OAuth CLI workaround.
    """
    from adw_cli_step import run_plan_build_via_cli
    import asyncio
    import uuid

    # Initialize worktree
    worktree_path = init_worktree(worktree_name, target_dir)
    adw_id = str(uuid.uuid4())[:8]

    try:
        # Run ADW workflow
        result = asyncio.run(run_plan_build_via_cli(
            prompt=prompt,
            working_dir=worktree_path,
            adw_id=adw_id
        ))
        return result
    finally:
        # Cleanup worktree
        subprocess.run([
            "git", "worktree", "remove", "--force", worktree_path
        ], check=False)
        subprocess.run([
            "git", "branch", "-D", worktree_name
        ], check=False)
```

---

## Limitations of CLI Approach

| Feature | SDK | CLI Subprocess |
|---------|-----|----------------|
| Real-time streaming | ✅ Yes | ❌ No |
| Hook callbacks | ✅ Yes | ❌ No |
| Message interception | ✅ Yes | ❌ No |
| Token usage tracking | ✅ Yes | ⚠️ Limited |
| WebSocket broadcasts | ✅ Yes | ❌ Manual |
| Session resumption | ✅ Yes | ⚠️ Via --resume |
| Swimlane UI | ✅ Yes | ❌ No |

---

## Alternative: GitHub Actions

If you need full ADW functionality, GitHub Actions can use `CLAUDE_CODE_OAUTH_TOKEN`:

```yaml
# .github/workflows/adw.yml
name: Run ADW
on:
  workflow_dispatch:
    inputs:
      prompt:
        description: 'ADW prompt'
        required: true

jobs:
  run-adw:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Claude
        env:
          CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
        run: |
          npx claude -p "${{ inputs.prompt }}"
```

**GitHub Actions Disadvantages**:
- No real-time WebSocket updates
- No local database integration
- Cold start latency (~30-60s)
- Rate limits apply
- Debugging is harder

---

## Recommendation

| Scenario | Approach |
|----------|----------|
| Quick experimentation | CLI subprocess |
| Full ADW features | Get Anthropic API key |
| CI/CD integration | GitHub Actions |
| Parallel worktrees | CLI + worktree scripts |

**Long-term**: An Anthropic API key (even minimal prepaid) unlocks the full ADW stack with swimlanes, hooks, and real-time UI.
