# Qwen first mission: 1UP Anime metadata sync

Goal: TODAY, run the existing permitted metadata ingestion and fix one reproducible defect. Do not build a new scraper if an existing one works.

## Repository evidence (2026-10-21)
- 1UP Anime already contains `scripts/refresh-catalog.mjs` fetching AniList GraphQL metadata into `data/catalog.json`.
- `.github/workflows/refresh-catalog.yml` schedules it daily and includes Spanish synopsis translation.
- `data/dexter/status.json` last observed 125 anime, 275 episode records, **zero playback sources**; the latest sync found zero new episodes. These are snapshots, not live runtime proof.

## Autonomous bounded job
1. Read `AGENTS.md`, `docs/PROJECT_CONTINUITY.md`, `docs/OMEGA_NEXT_ACTIONS.md` and current git status. Preserve existing design and code.
2. On a fresh `agent/qwen-scraping-<timestamp>` branch, run `node --check scripts/refresh-catalog.mjs`; then `node scripts/refresh-catalog.mjs` with a 3-minute external timeout. Do not suppress API failures.
3. Validate `data/catalog.json`: updated ISO date, nonempty groups, no duplicate IDs within each group, https streaming links only, no invented episode video URLs.
4. If a reproducible defect is found, make the smallest repair and rerun tests. Otherwise report successful sync with measured counts and no invented code changes.
5. Run relevant existing tests. Save a concise checkpoint: command, exit code, before/after counts, changed files, blockers, next task.
6. Do not touch auth/secrets, bypass access controls, download or redistribute copyrighted video, claim playback from metadata, auto-merge, or deploy.

## Completion criteria
Report verified success only when the actual fetch, validation and relevant tests have run. If AniList is unreachable or rate-limited, report a blocked run and preserve the last valid snapshot. A functioning scraper does not imply licensed playback.
