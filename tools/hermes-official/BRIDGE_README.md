# DEXTER HERMES -> OpenCode -> Qwen

This is the official Hermes Agent cron scheduler combined with OpenCode CLI's documented noninteractive run command. It does NOT install a new coding model or rebuild an agent.

## Setup in Windows

Requirements: Git, Python 3.12+, OpenCode CLI, official Hermes Agent, and an existing Qwen model endpoint already configured inside OpenCode.

In PowerShell from this branch's checkout:

    .\tools\hermes-official\INSTALL-OPENCODE-BRIDGE.ps1 -ProjectPath "C:\PATH\MY-REPOSITORY" -EnableHourly

This installs the local dispatcher Python script under %LOCALAPPDATA%\hermes\scripts\, creates one small safe pilot task, and registers one Hermes job that executes the dispatcher every hour using Hermes's documented --no-agent --script mode. The installer does not run the pilot immediately unless -RunPilot is passed.

Before enabling recurrence, test that OpenCode can complete a prompt using local Qwen. Select model in OpenCode before starting the job. To specify a particular Qwen model for a task use --model PROVIDER/MODEL with the identifier from opencode models.

## Sending tasks to OpenCode

Create a text file with exactly one concrete and reversible coding task. From PowerShell:

    $worker = Join-Path $env:LOCALAPPDATA 'hermes\scripts\dexter_opencode_tick.py'
    python $worker add --project 'C:\PATH\MY-REPOSITORY' --prompt-file 'C:\PATH\instructions.txt' --name task-001 --timeout 1800
    python $worker status

A queue item can include checks in a JSON file, using --checks-json checks.json, for example:

    [["python", "-m", "unittest", "discover", "-s", "tests", "-v"]]

Only add checks that actually exist for the repository. Jobs without substantive host checks are labeled needs_review instead of completed.

## Behavior

- The dispatcher starts OpenCode noninteractively: opencode run --agent build --format json (with optional --model).
- Hermes is the hourly scheduler and does not need to invoke its own AI model for each tick.
- Each job gets a separate Git worktree and branch, preserving the original working directory.
- Private task state and logs live under %LOCALAPPDATA%\DEXTER-AUTO, not in GitHub.
- A lock prevents two copies of this dispatcher overlapping.
- Error/timeout/uncertain execution is blocked for review rather than repeated blindly.
- No automatic pushing, merging, deployment, payment operations or deletion of repositories.
- Tasks run in separate worktrees and do not automatically incorporate the results of earlier tasks. Review/merge a task result before enqueuing a dependent task.

## Status and limitations

    python $worker doctor
    python $worker status
    hermes gateway status
    hermes cron status
    hermes cron list

Windows + Linux GitHub Actions use **real Git worktrees** and a **simulated OpenCode process**. That is not end-to-end confirmation of local Qwen and Hermes on the user's PC. Continuous operation requires the PC, model API, OpenCode CLI and Hermes gateway running. Hermes gateway can start at Windows user logon; the Qwen server may require separate startup configuration.

Textual instructions restricting the agent are not an OS security sandbox. Run as non-administrator with least privileges and only trusted repositories. Never store Stripe or API secrets in project files.

References:
- https://opencode.ai/v2/docs/cli/commands
- https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/
- https://github.com/NousResearch/hermes-agent
