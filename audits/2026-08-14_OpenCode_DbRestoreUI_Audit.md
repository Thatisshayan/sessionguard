# SessionGuard Audit — C5 Database Restore UI (W4.8)

**Date:** 2026-08-14
**Agent:** opencode
**Scope:** Complete the deferred C5 DB backup/restore UI (second half) — restore path
**Branch:** `feat/db-restore-UI`

---

## Executive Summary

The final deferred piece of the 50-task roadmap — the **DB restore half of C5/W4.8** — has been implemented, tested, and verified. PR #17 (frontend API-consistency + backup download UI) was merged first at `e17903e` per user approval, and this restore feature builds directly on it. The backup **download** half was already shipped in PR #17; this change adds the matching **restore** half (validated upload, atomic swap, safety backup, confirm modal).

All verification gates are **GREEN**: backend suite 260 passed / 6 skipped (was 253 — +7 new restore tests), frontend type-check and vite build pass, bundled-backend smoke passes.

---

## What was implemented

### Backend — `POST /api/v1/admin/restore`
`backend/routes/admin.py`
- Requires admin role (rejects anonymous 401 / non-admin 403).
- Streams the uploaded `.db` file to a temp location first (client fully consumed before touching the live DB).
- Validates before any swap:
  1. filename must end in `.db`,
  2. file must be non-empty,
  3. must open as a valid SQLite database (`PRAGMA integrity_check == ok`),
  4. must contain the expected core SessionGuard tables (`sessions`, `events`, `users`, `projects`, `jobs`, `live_runs`, `ocr_results`, `insights`, `alerts`, `audit_log`).
- Creates a **safety backup** of the current database via `VACUUM INTO` at `<db>.pre-restore-<ts>.db` before replacing.
- Atomically swaps the staging copy into place (`Path.replace` on same filesystem) and cleans stale `-wal`/`-shm` sidecars so the previous DB's WAL is not replayed against the restored snapshot.
- Returns `{ restored: true, safety_backup: <path|null> }`.

### Backend tests — `tests/test_admin_restore.py` (7 tests)
- `test_restore_requires_admin` — non-admin → 403
- `test_restore_requires_auth` — anonymous → 401
- `test_restore_rejects_non_db_extension` — `.txt` → 400
- `test_restore_rejects_empty_file` — empty body → 400
- `test_restore_rejects_not_sqlite` — non-SQLite bytes → 400
- `test_restore_rejects_wrong_schema` — valid SQLite missing SessionGuard tables → 400
- `test_restore_happy_path` — genuine `VACUUM INTO` snapshot restores; DB intact after; safety backup present

### Test infrastructure fix — `tests/conftest.py`
The `admin_headers` fixture was **stale**: it inserted a `salt` column that no longer exists in the `users` schema (had never been exercised — no existing test used it). Fixed to use the current schema + `hash_password()` from the auth service. Line endings preserved (LF).

### Frontend
- `frontend/src/services/api.ts` — added `restoreDb(file: File)` (multipart POST via the shared versioned axios client, which already injects the JWT and `/api/v1` prefix).
- `frontend/src/pages/Settings.tsx` — added a **Database Restore** card:
  - file picker (accept `.db`),
  - admin-gated (non-admin sees "Admin access required"),
  - "Restore Database…" button opens a **confirm-restore modal** (destructive-action confirmation),
  - success/failure toasts surfacing backend `detail` on failure,
  - file input cleared on success.
- `frontend/openapi.json` regenerated via `scripts/generate_client.py` (requires `SECRET_KEY` set — the app now fails fast without it, per WS2.2).

### Docs
- `docs/governance/DEFERRED_WORK.md` — C5 item marked **resolved** (2026-08-14) with implementation summary.

---

## Verification

| Gate | Result |
|---|---|
| `python -m pytest tests/test_admin_restore.py` | 7 passed |
| Full backend suite | **260 passed, 6 skipped** |
| `tsc --noEmit` (frontend) | pass |
| `vite build` | pass |
| Bundled-backend smoke (port 8012) | pass (`/health` → 200, version 1.5.2) |
| `scripts/verify.ps1` | backend + bundle + deploy-dry + directive-lint green (one cold-start smoke timing flake re-run green) |

---

## Notes / follow-ups

- Restore requires admin role — matches the W4.8 acceptance bar ("destructive restore requires explicit confirmation").
- Safety backup is written beside the live DB and reported back to the client; a future enhancement could surface it in the UI.
- Remaining deferred items (unchanged by this work): C1 async engine migration (WS5.1), B3 live NVIDIA NIM verification (needs R24-approved key), WS3 clean-VM runtime rehearsal (WS7).
