# Codebase Audit — 2026-07-23

## Scope and result

Read-only code-first audit of the full working tree, including repository state,
security boundaries, runtime architecture, complexity, tests, and delivery gates.
No product code was changed.

## Critical findings

1. The Git repository does not contain the application. `HEAD` is the four-commit
   `agent/hermes-governance-bootstrap` branch, while the application trees,
   archives, virtual environment, database, and generated artifacts are all
   untracked. No remote or upstream is configured, so push state cannot be
   established.
2. Three overlapping implementations exist: `_repo_clone`,
   `Claude/sessionguard_base Calude/sessionguard Session 1`, and
   `Claude/sessionguard_v05_phase3_complete/sessionguard`. Only `_repo_clone`
   has CI/workflows and the newer auth, jobs, Tauri, and test surface. The
   repository gives no single source-of-truth or release target.
3. `_repo_clone/backend/main.py` exposes many data routes without global auth,
   seeds and prints the fixed demo credential `demo@sessionguard.local / demo123`
   at every startup, and makes session/export/evidence download routes publicly
   callable. Authentication is implemented only for selected routers.

## High findings

- Upload classification accepts client MIME type and then filename extension; it
  does not verify file signatures. ClamAV absence degrades to acceptance by
  design. The API returns the server-side stored path.
- Evidence/export functions return files based on database IDs without a caller
  identity or ownership check. Evidence packaging uses broad exception handling
  that hides frame-export failures.
- Core units are unusually dense and combine orchestration, persistence,
  processing, and error policy: OCR frame processing (cyclomatic 26/cognitive
  94), Excel export (29/71), CSV import (23/60), evidence packaging (20/46),
  and upload handling (12/23). These are change-risk hotspots.
- A SQLite database, a Python virtual environment, PDFs, and ZIP exports are in
  the untracked working tree. They make secret scanning noisy and materially
  raise the risk of accidental artifact/data commits.

## Verification and repository state

- `git status`: branch `agent/hermes-governance-bootstrap`; numerous untracked
  files including all application source. No tracked modifications were shown.
- `git log`: four governance-only commits; no remote/upstream config exists.
- `pwsh scripts/verify.ps1`: failed. Secret scan traverses `_repo_clone/.venv`
  and reports dependency certificates/source; doc freshness fails because root
  `README.md` is missing. Build/test were skipped as no root build system was
  detected.
- Graph scan found no obvious live credential matching common API-token formats,
  but this is not a substitute for a clean secret scan.

## Assessment

The `_repo_clone` implementation shows real product work: parameterized SQL,
JWT verification/rotation, rate limits, upload size caps, tests, and a richer
desktop stack. However, the repository is currently an import/staging folder,
not a releasable software repository. Establish a single tracked product root,
remove generated/runtime material from version control scope, then enforce
authentication and per-user ownership on every non-public API before adding
features.

## Deep-dive addendum

- Git state is diverged, not merely dirty: `agent/hermes-governance-bootstrap`
  is ahead of `origin/agent/hermes-governance-bootstrap` by 70 commits and
  behind by 5. That means there are local-only changes that have not reached
  origin, and origin has changes this checkout has not incorporated.
- Ownership is extremely concentrated. `git shortlog` shows 68 commits from
  `thatisshayan` and 3 from `Thatisshayan`, so most of the codebase lacks
  shared ownership depth.
- Historical hotspot files are the control plane: `SessionGuardRevival.md`,
  `requirements.txt`, `backend/main.py`, `scripts/verify.ps1`,
  `engines/ai_insights_engine.py`, `database/db.py`, `frontend/src/services/api.ts`,
  and the desktop config/runtime files. Those are exactly the areas where a
  mistake cascades across the whole product.
- The auth boundary is inconsistent. `projects`, `admin`, `system_config`,
  `notes`, `tags`, `jobs`, and `data_export` do enforce token checks, but
  `sessions`, `events`, `alerts`, `insights`, `review_queue`, `uploads`,
  `exports`, `evidence`, `ai_analysis`, `openapi_export`, `search`, `trends`,
  and several live/utility routes do not show a global auth gate.
- `backend/routes/uploads.py` is stronger than a typical prototype but still
  not production-tight: it trusts client MIME/extension hints, skips virus
  enforcement when ClamAV is missing, and returns the internal server path in
  the API response.
- `backend/routes/exports.py` and `backend/routes/evidence.py` expose file
  downloads by database ID/session lookup only. Without ownership checks, those
  become ID-guessing endpoints.
- `backend/services/evidence_package.py` still suppresses some frame-write
  failures with bare `except Exception: pass`, so the package can be incomplete
  while the caller sees success.
- The frontend persists refresh tokens in `sessionStorage` in
  `frontend/src/context/AuthContext.tsx`, which is workable for a local-first
  prototype but not a strong browser security posture.

## Post-audit execution note

The following audit findings were materially reduced during the follow-up
hardening pass:

- Global auth was added or tightened across sessions, events, alerts,
  insights, review queue, behavior, trends, health, search, AI analysis,
  exports, evidence downloads, openapi export, metrics, dashboard, compare,
  prompt management, recorder, OCR calibration, parser benchmark, coach, live
  monitoring, and video job/status routes.
- Evidence package generation now records partial frame export failures instead
  of silently swallowing them.
- The demo bootstrap password was removed from `database/db.py`; demo-user
  seeding now requires `SESSIONGUARD_DEMO_PASSWORD`.
- Root-level archival artifacts and nested runtime logs were moved into
  ignored `hygiene/` folders instead of being left in the repo root.

Remaining follow-up items were recorded in `docs/governance/DEFERRED_WORK.md`.
