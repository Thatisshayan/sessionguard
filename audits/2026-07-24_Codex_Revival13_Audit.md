# 2026-07-24 Codex Revival 1.3 Audit

## Scope

Verified the prior A1/A5 claims and continued the active 1.3 sprint in the
canonical working clone at `_repo_clone`.

## Findings and changes

- A1 is partially implemented: `.github/workflows/bundled-backend-smoke.yml`
  stages the backend and probes `/health`; GitHub CI validation remains open.
- A5 is implemented: `intelligence.py` routes use relative paths under the
  `/api/v1/intelligence` mount, while the separately mounted AI-analysis route
  serves `/api/v1/ai/status`; the frontend calls `/ai/status`.
- A4 scan found no remaining `C:\\Projects`, `C:\\Users`, `/Users/`, `/home/`,
  or `D:\\` literals in `_repo_clone` source. A reusable drift-safe scanner is
  now available at `_repo_clone/scripts/check_repo_drift.py`.
- B5 is complete: `backend/version.py` reads `config/app_config.json`, and
  `backend.main` plus both health responses use `APP_VERSION`.

## Verification evidence

- `python -m pytest tests/test_version.py` from `_repo_clone`: **2 passed**.
- Codebase-memory index status: ready, 3,665 nodes / 8,004 edges.
- The local bundled-backend probe was attempted twice but did not return within
  the bounded runner window; no local smoke success is claimed. A1 remains
  partial pending CI validation.

## Residual work

- A2, A3, B1-B4, C1-C5, and D1-D2 remain open in the sprint board.
- No commit or push was performed in this pass.
