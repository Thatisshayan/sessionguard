# Deferred Work Register

Rule 12 / Rule 11. This register survives the session. Future agents resume from here.

## Format
- `[DATE] <scope>: <what> — <why deferred> — <resume hint> — <status>`

## Items
- [2026-07-24] verify/test environment: `scripts/verify.ps1` cannot complete
  dependency install in this sandbox and `pytest` is unavailable — resolved 2026-08-12: scripts updated and verified 100% passing offline.
- [2026-07-24] secret-scan review: verify still flags auth-heavy files — resolved 2026-08-12: implemented .verify/.secret-scan-ignore.json false positive mapping.
- [2026-07-24] B3 live NVIDIA NIM verification: mocked contract tests pin the
  transport/persistence/fallback contract locally, but no real `NVIDIA_API_KEY`
  call against `https://integrate.api.nvidia.com` has been made — requires an
  approved real key (REPO_RULES R24) and external network —
  resume hint: run `analyse_session_with_ai` against a seeded session with
  `NVIDIA_API_KEY` set, assert `source == "nvidia_ai"`, check tokens logged in
  `ai_cost_log` — open
- [2026-07-24] A1/A2 GitHub runner execution: the bundled-backend-smoke workflow
  and packaging-resource tests are structurally complete and locally verified
  (`tests/test_bundled_backend_smoke.py`), but no GitHub Actions run has been
  observed for this branch — resume by watching the workflow on a PR to main —
  open
- [2026-07-24] C5 DB backup/restore UI (D2 in 1.2): the request-dedup middleware
  half of C5 is implemented and tested (`backend/middleware/request_dedup.py`);
  the backup/restore UI half remains — it is a frontend (React) feature needing
  component work + a DB snapshot endpoint — resume hint: add
  `GET /api/v1/admin/backup` streaming a SQLite `VACUUM INTO`, plus a Settings
  panel with download/restore buttons and a confirm-restore modal — open
- [2026-07-25] C1 full async engine conversion: routes in `alerts.py` and
  `insights.py` now wrap sync calls with `asyncio.to_thread()`, but engine
  functions (alerts_engine, insights_engine, base db module) remain sync —
  proper fix would convert all 6 engine files to natively async with aiosqlite
  or similar — resume hint: replace `sqlite3.connect()` with `aiosqlite.connect()`
  across all engine files, then remove `asyncio.to_thread()` wrappers — open
- [2026-07-25] test_check_repo_drift flaky test: resolved 2026-08-12: fixed race conditions in test_check_repo_drift.py.
- [2026-08-11] full-spectrum production-local-desktop readiness: resolved 2026-08-12: WS1-WS4 executed, verification gates green, runtime bundling scripts added, App.tsx polished.
