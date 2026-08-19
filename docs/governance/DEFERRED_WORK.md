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
  `ai_cost_log` — resolved 2026-08-14: `scripts/verify_nvidia_live.py` passed
  against the real API (source == nvidia_ai, 3 [AI] insights persisted, cost
  logged in=537/out=244 $0.000151). Fixes surfaced: default model 404'd for the
  account — `NVIDIA_MODELS` reordered to verified `nvidia/llama-3.3-nemotron-super-49b-v1`
  (+pricing); `_log_ai_cost` only read `input_tokens`/`output_tokens` but NVIDIA
  returns OpenAI-style `prompt_tokens`/`completion_tokens` — normalization added.
- [2026-07-24] A1/A2 GitHub runner execution: the bundled-backend-smoke workflow
  and packaging-resource tests are structurally complete and locally verified
  (`tests/test_bundled_backend_smoke.py`), but no GitHub Actions run has been
  observed for this branch — resume by watching the workflow on a PR to main —
  resolved 2026-08-14: observed on PR #19 CI (run 31785241801) —
  `test_staged_backend_health_responds`, `test_staged_backend_reports_canonical_version`
  (test_bundled_backend_smoke.py) and all 4 `test_packaging_resources.py` cases
  PASSED on GitHub Actions; bundled-backend-smoke workflow run 31785241767 passed.
- [2026-07-24] C5 DB backup/restore UI (D2 in 1.2): the request-dedup middleware
  half of C5 is implemented and tested (`backend/middleware/request_dedup.py`);
  the backup/restore UI half remains — it is a frontend (React) feature needing
  component work + a DB snapshot endpoint — resume hint: add
  `GET /api/v1/admin/backup` streaming a SQLite `VACUUM INTO`, plus a Settings
  panel with download/restore buttons and a confirm-restore modal — resolved
  2026-08-14: `GET /api/v1/admin/backup` + `POST /api/v1/admin/restore`
  (validated, atomic swap with safety backup) implemented; Settings panel has
  download + restore buttons and a confirm-restore modal; 7 tests in
  `tests/test_admin_restore.py`.
- [2026-07-25] C1 full async engine conversion: routes in `alerts.py` and
  `insights.py` now wrap sync calls with `asyncio.to_thread()`, but engine
  functions (alerts_engine, insights_engine, base db module) remain sync —
  proper fix would convert all 6 engine files to natively async with aiosqlite
  or similar — resume hint: replace `sqlite3.connect()` with `aiosqlite.connect()`
  across all engine files, then remove `asyncio.to_thread()` wrappers — open
- [2026-07-25] test_check_repo_drift flaky test: resolved 2026-08-12: fixed race conditions in test_check_repo_drift.py.
- [2026-08-11] full-spectrum production-local-desktop readiness: resolved 2026-08-12: WS1-WS4 executed, verification gates green, runtime bundling scripts added, App.tsx polished.
- [2026-08-16] local verify truth: `pwsh -File scripts/verify.ps1` is red again
  on 2026-08-16 because `tests/test_live_coach.py` expects deterministic rule
  triggers (`martingale`, `rtp_decay`) while `engines/live_coach_engine.py`
  prefers NVIDIA/Ollama coaching before rule fallback when AI is available —
  resume hint: either make the tests explicitly disable AI/Ollama or make the
  coach expose a deterministic test mode so local pass/fail does not depend on
  ambient Ollama availability — resolved 2026-08-16: added `RULE_FIRST_TRIGGERS`
  set (`martingale`, `rtp_decay`, `rage_spiral`, `critical_streak`,
  `tilt_betting`) in `engines/live_coach_engine.py` so those triggers always
  return the deterministic rule message before the AI tiers run, plus a
  `SESSIONGUARD_DISABLE_COACH_AI` env-var escape hatch; `tests/test_live_coach.py`
  now passes 3/3 regardless of ambient Ollama state; full `pwsh -File
  scripts/verify.ps1` confirmed green (264 passed, 2 skipped).
- [2026-08-16] Tauri bundled-runtime path mismatch: `desktop_shell/stage-backend.js`
  stages runtimes into `bundled_app/python_win`, `tesseract_win`, and
  `ffmpeg_win`, but `desktop_shell/src-tauri/src/main.rs` only checks for
  bundled Python under `resources/bundled_app/python/python.exe` before
  falling back to system PATH — resume hint: normalize the runtime folder
  contract across staging + launcher + docs, then verify packaged-desktop
  startup uses bundled binaries end-to-end — resolved 2026-08-16: verified
  `main.rs::find_python()` already checks both `resources/bundled_app/python/`
  and `resources/bundled_app/python_win/` folder names, matching
  `stage-backend.js`'s `python_win` staging target; `pwsh -File
  scripts/verify.ps1`'s desktop-bundle smoke step confirms all three runtimes
  (`python_win`, `tesseract_win`, `ffmpeg_win`) stage correctly into
  `desktop_shell/src-tauri/bundled_app/` and the bundled backend smoke passes.
- [2026-08-16] local launch/docs drift: quick-start desktop scripts still launch
  the legacy PySide6 shell (`scripts/run_desktop.bat`) and `scripts/setup.bat`
  still prints `v0.5`, while the repo positions Tauri as the primary desktop
  target; README and the 2026-08-12 launch-readiness audit also overstate the
  current verified state — resume hint: choose one primary local desktop path,
  align `run_all`/`run_desktop`/README to it, and remove stale “100% ready”
  wording once re-verified — resolved 2026-08-16: `scripts/run_desktop.bat`
  now `cd`s into `desktop_shell/` and runs `npm run tauri:dev`;
  `scripts/run_all.bat` launches the Tauri window (not PySide6) and
  `scripts/setup.bat` printed `v1.5.3`; version string was reconciled in that
  pass and is now `v1.5.4`
  (canonical source `config/app_config.json`) across `README.md` and
  `frontend/src/pages/Login.tsx` (was `v0.6`); `README.md` intelligence
  doubled-prefix bug claim (line 142) removed — confirmed fixed by reading
  `backend/routes/intelligence.py` (no doubled segment); AI Narrative note and
  Documentation index updated to reference `SESSIONGUARDREVIVAL1.5.md`; the
  2026-08-12 audit's "100% GREEN" claim annotated as time-bound, not current
  status.
- [2026-08-16] frontend UI coverage for API-only backend features: evidence
  package management, clustering, dataset summary/anomalies, and AI
  compare/review-suggestion endpoints exist and are tested in the backend
  (`frontend/src/services/api.ts` has typed helpers) but have no routed page
  in `frontend/src/App.tsx` — resume hint: add routed pages for these under
  `frontend/src/pages/` and wire nav entries, or keep deliberately API-only —
  documented as API-only in `README.md`'s Feature Completeness section
  2026-08-16; still open (no UI added this pass, scope was doc-accuracy +
  the two code fixes above, not new feature build).
- [2026-08-17] tagged GitHub release automation/docs drift: the desktop build
  workflow published against a literal `v__VERSION__` placeholder instead of
  the pushed tag name, while top-level docs still framed Windows installer and
  bundled-runtime readiness as mostly future work even after local verify and
  GitHub packaging had passed — resume hint: switch the workflow to
  `${{ github.ref_name }}`-driven release metadata, publish from a real `v*`
  tag, and reconcile README/docs with the current desktop release path —
  resolved 2026-08-17: `.github/workflows/build.yml` now publishes on the real
  tag name with non-draft releases, version strings were bumped to `v1.5.4`,
  and `README.md`/`docs/README.md` were updated to describe the current local
  run + GitHub release flow.
- [2026-08-19] non-Windows packaged desktop releases: the current desktop
  runtime contract is Windows-specific (`python_win`, `tesseract_win`,
  `ffmpeg_win`) and GitHub CI can only build a valid installer after hydrating
  Windows embeddable Python in the workflow; macOS/Linux packaged releases are
  therefore deferred rather than pretending they are supported — resume hint:
  introduce platform-native runtime hydration/bundling for macOS/Linux and then
  restore those jobs in `.github/workflows/build.yml` — open
