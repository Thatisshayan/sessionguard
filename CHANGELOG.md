# SessionGuard Application Changelog
Automated conventional commit release log.
## Features
- `3dcda64` feat(admin): add DB restore endpoint + Settings restore UI (C5) (thatisshayan, 2026-08-14)
- `2b9f42c` feat: Roadmap Execution Final Batch 7 - i18n Translations & Playwright E2E CI Workflow (#15) (Shayan, 2026-08-13)
- `2cecaed` feat: Roadmap Execution Batch 6 - Production Dockerfile, FTS5 Search & Gzip Middleware (#14) (Shayan, 2026-08-13)
- `509113c` feat(roadmap-batch-5): Tasks 14, 23, 27, 30, 38, 46, 47, 50 - Gzip middleware, changelog generator, and admin diagnostics panel (#13) (Shayan, 2026-08-13)
- `47e143a` feat(roadmap-batch-4): Tasks 13, 28, 29 - SQLite connection pooling timeout, AI token usage route, and automated session tagging (#12) (Shayan, 2026-08-13)
- `e0bcfbe` feat: Roadmap Execution Batch 3 - Martingale Detector, Volatility Index & RTP Decay Alerts (#11) (Shayan, 2026-08-13)
- `065fda3` feat: Roadmap Execution Batch 2 - Dual-Engine OCR, Ollama Fallback & WebSocket Event Replay (#10) (Shayan, 2026-08-13)
- `f20144f` feat(roadmap-batch-1): Tasks 1, 2, 4, 7, 8, 20, 44, 45 - RBAC helpers, HMAC audit log exporter, DB backup, idle session lock, and shortcut modal (#9) (Shayan, 2026-08-13)
- `b22fdac` feat: Execute 20 Strategic Roadmap Tasks across Packaging, Security, AI, Performance & Dx (#6) (Shayan, 2026-08-13)
- `6bc75fc` feat: SessionGuard Launch Readiness & Runtime Bundling (#5) (Shayan, 2026-08-12)
- `a2b4ee4` feat(revival): targeted AI-layer observability (D1) (thatisshayan, 2026-07-24)
- `c05bb3e` feat(revival): add opt-in request-dedup middleware + tests (C5) (thatisshayan, 2026-07-24)
- `609b8d9` feat(revival): verify runtime and unify app version (thatisshayan, 2026-07-24)

## Bug Fixes
- `c1c7bdc` fix(settings): use btn-danger CSS class for restore button (Codacy param count) (thatisshayan, 2026-08-14)
- `b6a4e2e` fix(settings): hoist restore button style to variable (thatisshayan, 2026-08-14)
- `1187993` fix(settings): extract restore button style const to satisfy Codacy (thatisshayan, 2026-08-14)
- `57c0563` fix(admin): use sqlite3 backup API for safety backup; clear Codacy findings (thatisshayan, 2026-08-14)
- `5a66024` fix(admin): add noqa suppression for VACUUM INTO path safety (thatisshayan, 2026-08-14)
- `1db028b` fix(admin): address Codacy findings on restore endpoint + Settings UI (thatisshayan, 2026-08-14)
- `93f1663` fix(coach): resolve payload parsing and pattern detection robustness (#16) (Shayan, 2026-08-13)
- `d270d67` fix: address 3 remaining CodeRabbit corners (thatisshayan, 2026-07-25)
- `04409b5` fix: wrap ScreenRecorder sync calls in asyncio.to_thread (thatisshayan, 2026-07-25)
- `c062d72` fix: address all CodeRabbit/Qodo review comments on PR #4 (thatisshayan, 2026-07-25)
- `8ecfa2a` fix: wrap all remaining sync engine calls in async routes (thatisshayan, 2026-07-25)
- `20d3887` fix: flaky test_check_repo_drift + async is_ollama_available (thatisshayan, 2026-07-25)
- `8d84e67` fix(revival): proper async gap fixes for C1, DB timeout, and coverage (thatisshayan, 2026-07-25)
- `bcd287c` fix: ignore localhost/127.0.0.1 URLs in doc-freshness link check (thatisshayan, 2026-07-25)
- `e1397c7` fix(gate): install markdown-link-check for doc-freshness step in CI (thatisshayan, 2026-07-25)
- `36a4280` fix: authenticate CSV upload test and update sample_session_data fixture (thatisshayan, 2026-07-25)
- `e429f81` fix: address all CodeRabbit review comments across governance and auth layers (thatisshayan, 2026-07-25)
- `beeb749` fix(exports): close connection on missing session (thatisshayan, 2026-07-24)

## Documentation
- `c8efd4e` docs(governance): add REPO_DIRECTIVE.md (goal-layer constitution) (thatisshayan, 2026-07-24)
- `ea9c0f6` docs(audit): honest gap-fix audit for C5/D1 push and CI status (thatisshayan, 2026-07-25)
- `e777900` docs(revival): align sprint status and audit evidence (thatisshayan, 2026-07-24)
- `4387ccc` docs(governance): add REPO_DIRECTIVE.md (goal-layer constitution) (thatisshayan, 2026-07-24)

## Refactoring & Performance
- `4754100` refactor: clean up 4 corners from review fixes (thatisshayan, 2026-07-25)

## Maintenance & Chores
- `e17903e` chore: Frontend API-consistency, coach URL fix, version alignment (#17) (Shayan, 2026-08-14)
- `e562f7a` Merge pull request #4 from Thatisshayan/fix/revival13-gap-fixes (Shayan, 2026-07-25)
- `96524cb` Merge branch 'main' of https://github.com/Thatisshayan/sessionguard (thatisshayan, 2026-07-25)
- `5674a84` Revival 1.3: CI repair, desktop bundling fix, AI router mount + doc updates (Shayan, 2026-07-25)
- `46106f1` test(revival): raise roi_calibrator coverage to 75% (B4) (thatisshayan, 2026-07-24)
- `4d7fa2b` test(revival): cover export ImportError + live PDF/Excel generation (B2) (thatisshayan, 2026-07-24)
- `53e2b56` test(revival): raise video_pipeline coverage to 38% (B1) (thatisshayan, 2026-07-24)
- `fc81bca` test(revival): add repo-drift CI workflow + packaging/static tests (A2, A3) (thatisshayan, 2026-07-24)
- `d9e4ecb` test(revival): add mocked NVIDIA NIM contract tests + fix insight persistence (B3) (thatisshayan, 2026-07-24)
- `dc8b5a7` test(revival): add bundled-backend smoke regression (A1) (thatisshayan, 2026-07-24)
- `37e089b` test(evidence): cover successful package assembly (thatisshayan, 2026-07-24)
- `bf6dc5b` test(revival): cover video evidence roi and packaging (thatisshayan, 2026-07-24)
- `4a64b6f` Merge pull request #2 from Thatisshayan/codex_app_hardening_2026_07_24 (Shayan, 2026-07-24)
- `f234481` merge main into app hardening branch (thatisshayan, 2026-07-24)

