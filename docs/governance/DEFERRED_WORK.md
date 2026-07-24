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
