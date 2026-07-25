# Deferred Work Register

Rule 12 / Rule 11. This register survives the session. Future agents resume from here.

## Format
- `[DATE] <scope>: <what> — <why deferred> — <resume hint> — <status>`

## Items
- [2026-07-24] verify/test environment: `scripts/verify.ps1` cannot complete
  dependency install in this sandbox and `pytest` is unavailable — keep the
  repo-provided env/bootstrap path or vendor the test runtime so verification
  runs offline — open
- [2026-07-24] secret-scan review: verify still flags auth-heavy files
  (`backend/auth/service.py`, `backend/routes/alerts.py`,
  `backend/routes/auth.py`, `backend/routes/openapi_export.py`,
  `database/db.py`, `engines/ai_insights_engine.py`,
  `frontend/src/services/api.ts`, `tests/test_auth.py`) — review scan rules and
  decide whether these are true positives or exclusions — open
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
