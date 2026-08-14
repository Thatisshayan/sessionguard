# SessionGuard Audit — C5 Database Restore UI (W4.8)

**Date:** 2026-08-14
**Agent:** opencode
**Scope:** Complete the deferred C5 DB backup/restore UI (second half) — restore path
**Branch:** `feat/db-restore-UI`

---

## Executive Summary

The final deferred piece of the 50-task roadmap — the **DB restore half of C5/W4.8** — has been implemented, tested, and verified. PR #17 (frontend API-consistency + backup download UI) was merged first at `e17903e` per user approval, and this restore feature builds directly on it. The backup **download** half was already shipped in PR #17; this change adds the matching **restore** half (validated upload, atomic swap, safety backup, confirm modal).

All verification gates are **GREEN**: backend suite 260 passed / 6 skipped (was 253 — +7 new restore tests), frontend type-check and vite build pass, bundled-backend smoke passes. PR #18 merged to `main` as `dd8fc61` (2026-08-14).

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
- Creates a **safety backup** of the current database via the sqlite3 `Connection.backup()` API (no raw SQL — chosen over `VACUUM INTO` to keep Codacy's SQL-injection static analysis clean) at `<db>.pre-restore-<ts>.db` before replacing.
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

## Codacy gate

The `feat/db-restore-UI` branch went through a multi-round Codacy remediation (PR #18 CI). Codacy flags on *new* diff lines and enforces a 0-new-issues gate:

1. **HIGH — memory bloat**: `read_bytes()`/`write_bytes()` on the full DB → replaced with `shutil.copyfile` for staging + `Path.replace` for atomic swap.
2. **HIGH — `restore_database` too complex** → extracted `_validate_backup_snapshot()` and `_create_safety_backup()` helpers.
3. **MEDIUM — `tempfile.mkdtemp` never removed** → `tempfile.TemporaryDirectory` context manager.
4. **HIGH — formatted SQL `VACUUM INTO`** → `# noqa: B608` did **not** suppress Codacy's own SQL-concat/format pattern check; the endpoint now uses the sqlite3 `Connection.backup()` API in `_create_safety_backup` and `tests/test_admin_restore.py`'s `_make_valid_backup` helper, eliminating the raw SQL entirely.
5. **B101 assert warnings** in the new test file → `# nosec B101` comments (Codacy/bandit treats asserts as security-relevant).
6. **MEDIUM — restore replaces whole DB → stale frontend state** → `window.setTimeout(() => window.location.reload(), 800)` after successful restore.
7. **LOW/MEDIUM — void-returning arrow shorthands** in `Settings.tsx` → braces added to `onClick`/`onChange`/`setTimeout` callbacks.
8. **MEDIUM — "Method (anonymous) has 14 parameters"** on the restore `<button>`: Lizard counts the inline style object's keys + JSX attributes as function parameters. Hoisting the style to a module const (`RESTORE_BTN_STYLE`) and then a component-level `restoreBtnStyle` did **not** reduce the count — Lizard resolves the referenced const. Fix: moved the button styling into a reusable `.btn-danger` CSS class in `frontend/src/styles/global.css` and removed the inline style object entirely (button now has 3 attributes).
9. **MEDIUM — "Method (anonymous) has 14 parameters"** (2nd report, `Settings.tsx` line ~223): the first fix dropped the button to 3 attributes but the *confirm-restore modal* block (`{confirmOpen && (...)}`) still carried multiple multi-key inline `style={{...}}` objects, which Lizard again counted as parameters — this time reproducing locally via `python -m lizard frontend/src/pages/Settings.tsx -l typescript` (the anonymous `@223-231` had PARAM 14). Local bisection (isolating the modal in `$env:TEMP` repro files) proved the trigger was the inline style objects inside the `{confirmOpen && (...)}` wrapper, not the button. Fix (`270b521`): extracted **all** modal styling into `global.css` classes (`modal-overlay`, `modal-card`, `modal-header`, `modal-title`, `modal-close`, `modal-body`, `modal-actions`) plus a `.btn-secondary` button class, and rewrote the modal JSX to use `className` only. Local lizard then showed no anonymous function with PARAM > 8.

**Final Codacy result: PASS — 0 new issues** on head `270b521` (PR #18 CI). The 0-new-issues gate is satisfied and the merge was approved and completed as squash commit `dd8fc61` ("feat(admin): DB restore endpoint + Settings restore UI (C5) (#18)"). The Linux (AppImage + deb) build, which had failed once on a transient GitHub Actions infrastructure error ("No server is currently available to service your request"), also passed on the re-run and on `270b521`.

## Verification

| Gate | Result |
|---|---|
| `python -m pytest tests/test_admin_restore.py` | 7 passed |
| Full backend suite | **260 passed, 6 skipped** |
| `tsc --noEmit` (frontend) | pass |
| `vite build` | pass |
| Bundled-backend smoke (port 8012) | pass (`/health` → 200, version 1.5.2) |
| `scripts/verify.ps1` | backend + bundle + deploy-dry + directive-lint green (one cold-start smoke timing flake re-run green) |
| PR #18 CI (head `270b521`) | **all green** — Codacy 0 new issues, CodeFactor, CodeRabbit, qlty, backend tests, frontend type check, E2E smoke, OCR benchmarks, Linux (AppImage + deb), Windows (MSI + NSIS), macOS (DMG), bundled-backend smoke, governance gate (x2), repo-drift check |

---

## Notes / follow-ups

- Restore requires admin role — matches the W4.8 acceptance bar ("destructive restore requires explicit confirmation").
- Safety backup is written beside the live DB and reported back to the client; a future enhancement could surface it in the UI.
- Remaining deferred items (unchanged by this work): C1 async engine migration (WS5.1), B3 live NVIDIA NIM verification (needs R24-approved key), WS3 clean-VM runtime rehearsal (WS7).
