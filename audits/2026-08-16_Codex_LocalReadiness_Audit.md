# SessionGuard Local Readiness Audit

Date: 2026-08-16
Agent: Codex
Scope: Deep audit of what still prevents SessionGuard from functioning at 100% locally.

## Verdict

SessionGuard is not at 100% local readiness on 2026-08-16.

The repo is close: frontend build passes, the bundled-backend smoke passes, and the Tauri toolchain is present on this machine. But the local verification contract is red, the primary desktop runtime-bundling path is still inconsistent, the quick-start desktop launcher still targets the legacy shell instead of the primary Tauri shell, and several backend capabilities exposed in the API layer still have no routed frontend surface.

## Evidence Used

- Governance/docs: `REPO_RULES.md`, `README.md`, `docs/governance/DEFERRED_WORK.md`
- Prior audits: `audits/2026-08-11_Codex_FullSpectrum_Audit.md`, `audits/2026-08-12_OpenCode_LaunchReadiness_Audit.md`
- Verification command actually run:
  - `pwsh -File scripts/verify.ps1`
  - Result on 2026-08-16: **FAILED**
- Code inspected:
  - `engines/live_coach_engine.py`
  - `tests/test_live_coach.py`
  - `desktop_shell/stage-backend.js`
  - `desktop_shell/src-tauri/src/main.rs`
  - `scripts/setup.bat`
  - `scripts/run_all.bat`
  - `scripts/run_desktop.bat`
  - `frontend/src/App.tsx`
  - `frontend/src/services/api.ts`

## Findings

### 1. Local verify is red today, so the repo cannot honestly be called 100% locally functional

`pwsh -File scripts/verify.ps1` failed on 2026-08-16 with 2 failing tests:

- `tests/test_live_coach.py::TestLiveCoach::test_martingale_coaching_triggered`
- `tests/test_live_coach.py::TestLiveCoach::test_rtp_decay_coaching_triggered`

Root cause from current code:

- `get_coaching_message()` prefers NVIDIA first, then local Ollama, then deterministic rules (`engines/live_coach_engine.py:277-306`)
- The tests still assert deterministic `trigger` values (`tests/test_live_coach.py:31-48`)
- On a machine where Ollama is reachable, the returned trigger becomes `ollama_local`, which breaks the current tests and also makes local behavior depend on ambient machine state

Impact:

- The repo’s required local verification path is currently red
- Live-coach behavior is nondeterministic across machines depending on whether Ollama is installed/running

### 2. The Tauri runtime-bundling path is still internally inconsistent

The stage script and the Tauri launcher do not agree on where bundled runtimes live.

Current staging behavior:

- `desktop_shell/stage-backend.js:68-73` stages runtimes into:
  - `bundled_app/python_win`
  - `bundled_app/tesseract_win`
  - `bundled_app/ffmpeg_win`

Current launcher behavior:

- `desktop_shell/src-tauri/src/main.rs:59-69` only checks for bundled Python at:
  - `resources/bundled_app/python/python.exe`
- If that path is absent, it logs fallback to system Python

Impact:

- The verify smoke proves the staged backend can start, but it does **not** prove the installed Tauri app will use bundled Python
- The current code path can still silently fall back to a host-installed Python even when bundled runtimes exist under different folder names
- This means the repo is not yet at true self-contained local desktop readiness

### 3. Quick-start desktop scripts still launch the legacy PySide6 shell, not the primary Tauri shell

Current script state:

- `scripts/run_all.bat:12` advertises `Desktop  -> PySide6 window`
- `scripts/run_desktop.bat:2,17` explicitly launches `python -m desktop_app.app.main`
- `scripts/setup.bat:7` still prints `SessionGuard v0.5 - First Time Setup`

This conflicts with the repo’s own current positioning:

- README architecture describes `desktop_shell/` (Tauri) as the primary desktop target
- The local run scripts still exercise the older Python desktop shell instead

Impact:

- A fresh local user following the documented quick start is not exercising the stated primary desktop target
- Script and product-version drift reduce trust in the local setup path

### 4. Several implemented backend capabilities are still API-only from the routed frontend’s point of view

The frontend service layer exposes these backend capabilities:

- evidence package helpers (`frontend/src/services/api.ts:113-114`)
- clustering (`frontend/src/services/api.ts:252-253`)
- dataset summary / anomalies (`frontend/src/services/api.ts:256-257`)
- AI compare / review suggestion (`frontend/src/services/api.ts:264-265`)

But the routed UI in `frontend/src/App.tsx:288-307` only exposes these top-level pages:

- dashboard, sessions, compare, live, import, upload, review, reports, projects, profiles, benchmark, jobs, admin, settings

Observed usage in the current frontend:

- DB backup/restore is wired in `Settings.tsx`
- AI analysis is wired in `SessionDetail.tsx`
- No routed page was found for cluster exploration, dataset quality, anomaly review, or evidence-package management

Impact:

- “Implemented locally” is still not the same as “usable locally” for those features
- Backend capability breadth still exceeds discoverable frontend capability

### 5. Repo truth has drifted again between docs/audits and current reality

Concrete mismatches observed:

- `audits/2026-08-12_OpenCode_LaunchReadiness_Audit.md:13,60` claims the verify path was 100% green and the branch was 100% launch-ready
- As of 2026-08-16, `pwsh -File scripts/verify.ps1` is red
- `README.md:142` still documents the intelligence doubled-prefix route bug as open, but current route wiring in `backend/main.py` + `backend/routes/intelligence.py` no longer matches that claim
- `README.md:37` says the desktop app is “Launched by run_all”, but the current launcher path is the legacy PySide6 app, not the primary Tauri shell

Impact:

- A new engineer cannot trust one document alone to know what is truly working locally today
- This is a docs/truthfulness issue, not just a wording issue, because the repo has governance rules that explicitly require verification-backed claims

## What Is Missing For 100% Local Function

1. A green local verify path again
   - Fix or re-scope the live-coach tests so local pass/fail does not depend on ambient Ollama availability.

2. A coherent desktop runtime contract
   - Make staging paths and `main.rs` lookup paths agree.
   - Prove the installed Tauri app uses bundled runtimes instead of falling back to host Python.

3. One true desktop launch path
   - Update quick-start scripts so the documented local desktop flow launches the primary Tauri shell, or explicitly demote the Tauri shell if that is no longer the product target.

4. UI closure for API-only features
   - Add routed/discoverable frontend surfaces for the advertised intelligence/evidence features, or explicitly mark them as API-only.

5. Documentation truth cleanup
   - Remove stale “100% ready” claims and outdated route-bug notes.
   - Align README, scripts, and active audit status with the current verified state.

## Verification Status

- Completed:
  - `pwsh -File scripts/verify.ps1` (failed)
  - `cargo --version`
  - `rustc --version`
  - `npm --prefix desktop_shell run tauri:info` (partial output captured before tool timeout; environment checks shown as healthy)
- Not completed:
  - Full `tauri build`
  - Clean-machine install/run rehearsal
  - Live packaged-desktop launch proving bundled runtime usage end-to-end

## Bottom Line

SessionGuard is locally usable in substantial parts, but it is not locally complete or locally trustworthy enough to call “100%” on 2026-08-16.

The highest-signal blockers are:

- red verify
- mismatched bundled-runtime paths
- legacy desktop launcher drift
- backend features without equivalent routed UI
- stale readiness claims in docs/audits
