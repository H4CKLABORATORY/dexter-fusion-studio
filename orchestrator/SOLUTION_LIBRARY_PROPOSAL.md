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
