# Mission Control — verified solution library (proposal)

This is a documentation-only, opt-in design. It does not install HomeShed or execute commands.

## Entry contract
Each reusable solution records: stable id, repository, problem fingerprint, source commit, related PR, affected paths, test command, test result, environment, last verified commit, risk, rollback, and next action. No credentials, private user data, or unverified success claims.

## Reuse gate
1. Consult AGENTS.md, queue and checkpoints before searching.
2. Match repository + affected paths + problem fingerprint; check current main SHA and open PRs.
3. Only reuse a patch when its base and test evidence remain applicable; otherwise label stale and revalidate.
4. Never auto-run scripts or merge PRs. Request review and record blockers.
5. Report savings only from measured duplicate steps or actual token telemetry.

## HomeShed assessment
External MCP integration is **not approved or installed**. Review source, license, dependencies, permission scope and command allowlist before a separate integration PR. Local Windows bridge remains unverified.

## Acceptance for follow-up implementation
A deterministic offline test should prove duplicate detection, stale SHA rejection, secret-field rejection and non-execution of stored commands. Keep the existing queue priorities unchanged.

## Decision model (baseline required)
For a matched task, define total expected minutes:
- baseline = repeated_search_minutes + repeated_reproduction_minutes + repeated_test_minutes
- reuse = lookup_minutes + revalidation_minutes + integration_minutes
- net_saved_minutes = baseline - reuse
- success_rate = verified_completed_tasks / attempted_tasks
- token_delta = baseline_input_output_tokens - reuse_input_output_tokens (only when instrumented)

Reject a feature when measured net_saved_minutes <= 0, success rate decreases, or a security invariant fails. Do not extrapolate percentage savings from one example. Track sample size and median as well as outliers.

## Capability assessment (2026-10-21; external claims not independently audited)
| Component | Incremental value | Decision |
| --- | --- | --- |
| Existing GitHub checkpoints and AGENTS.md | Already present; no extra service | Keep as source of truth |
| Solution fingerprint and stale-SHA gate | Addresses observed repeat investigations | Pilot offline |
| HomeShed memory/SQLite | Potential cross-agent lookup; duplicates existing checkpoint layer | Defer pending benchmark |
| HomeShed Git/Docker/command tools | High permissions, overlap with GitHub connector | Do not enable |
| Z3/logic solver | Only for reproducible constraint problems | Evaluate per task |
| Live dashboard | Visibility, no proven task-completion gain | Defer until event data exists |
| Token savings display | Needs instrumented counts | Do not estimate |
| Local model bridge | Not authenticated or verified | Disabled |

## Controlled A/B pilot
Use 10 previously encountered non-sensitive bug tasks, with 5 baseline and 5 reuse trials, then swap assignments if practical. Freeze task definitions and success criteria before measurement. Record actual minutes, GitHub reads, repeated steps, test results and any available token counts. Require no regressions, no leaked secrets and positive median net time saved before expanding. Avoid untrusted code execution and production deployment.
