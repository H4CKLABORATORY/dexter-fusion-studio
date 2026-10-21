# DEXTER local accelerator — fast Windows handoff

This folder reuses existing programs rather than vendoring their source code. No upstream program is bundled or installed by merely merging this PR.

## Reused components

| Component | Official upstream | Use |
| --- | --- | --- |
| LM Studio | https://lmstudio.ai/ | Local Qwen OpenAI-compatible endpoint |
| Aider | https://github.com/Aider-AI/aider | Local AI code editing |
| GitHub CLI | https://cli.github.com/ | Auth and repository workflow |
| Git | https://git-scm.com/ | Local branches and diffs |
| Node.js | https://nodejs.org/ | Existing 1UP metadata scraper |

Review licenses and security before adding any other third-party code. Do not copy entire upstream repositories into this one.

## One-time Windows setup

Open PowerShell in this folder. The commands below are **not yet validated on the owner's Windows PC**.

```powershell
.\START-DEXTER.ps1 -Install
```

After tools are installed, reopen PowerShell and ensure LM Studio has loaded Qwen and enabled its local API server at `http://127.0.0.1:1234`. Authenticate GitHub CLI if needed:

```powershell
gh auth login
```

Run the **existing scraper first**, even if the model is not ready:

```powershell
.\RUN-1UP-SCRAPING.ps1
```

This expects a clone at `%USERPROFILE%\DEXTER-LOCAL\1UP-ANIME`. Override with `-Project 'C:\path\to\1UP-ANIME'` if needed. It runs `node --check`, invokes the repository's existing `scripts/refresh-catalog.mjs` with a 240-second timeout, validates the generated `data/catalog.json`, and writes `%USERPROFILE%\DEXTER-LOCAL\reports\last-scraping-run.json`. It does not push, merge or deploy. AniList connectivity is required.

Next, run the **one-task Qwen coding trial**:

```powershell
.\START-DEXTER.ps1 -StartTask
```

Read `QWEN_FIRST_SCRAPING_MISSION.md` as the next agent assignment. Note: `START-DEXTER.ps1 -StartTask` currently uses its original single UX/test improvement prompt; it does **not yet** automatically consume the mission file or run a 24/7 queue. This gap is explicit so we don't mistake documentation for automation.

## Verification checklist

- `last-scraping-run.json` reports `status: completed`, with valid counts.
- `git diff` shows only expected changes to the catalog or intentionally edited files.
- Existing site tests pass after changes.
- Playback sources are not inferred from metadata.
- No Windows service, auto-restart, auto-push, remote approval or WhatsApp integration is claimed functional until actually tested.

If the first run fails, preserve the JSON report and command output. Fix that exact failure before adding more components.
