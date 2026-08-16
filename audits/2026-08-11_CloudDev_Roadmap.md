# SessionGuard — Cloud-Dev Roadmap (VERTEX HANDOFF, 2026-08-11 session)

**Source:** reconciled from `audits/2026-08-11_ClaudeCode_FullSpectrum_Audit.md` + `audits/2026-08-11_Codex_FullSpectrum_Audit.md`, then **VERIFIED against live repo state** (`git fetch` / `gh pr view` / `gh run list`) in a separate session. Verbatim body below is from `C:\Users\AgentDev\.claude\plans\verify-these-and-layour-velvet-haven.md`.

## Session constraints (Shayan, 2026-08-11)
- **Cloud-only execution this session:** only Vertex AI agents burn the $400 GCP credit. No local Claude Code / Codex phase execution.
- **WS2 (Security & auth hardening) DEFERRED** — local-first, not SaaS yet. Revisit post-launch. (Loopback bind already verified safe; **W1.4 secret-scan triage stays** — it's CI-truth, not auth hardening.)
- **W5.2 (live NVIDIA key call) requires explicit approval** — flag and pause, don't spend.
- **MERGE ALREADY DONE:** PR #4 merged 2026-07-25, CI green on GitHub runners. Do NOT re-merge. Start at WS1 (gate fidelity), not "merge branch."

---

# SessionGuard — Verified Completion Roadmap (local-first desktop track, excl. SaaS)

## Context

Two full-spectrum audits were written today (2026-08-11) — Claude Code's (`audits/2026-08-11_ClaudeCode_FullSpectrum_Audit.md`, phases A–E) and Codex's (`audits/2026-08-11_Codex_FullSpectrum_Audit.md`, phases 1–7). Both were cross-checked this session against the live repo (`git fetch`, `gh pr view`, `gh run list`, direct file reads via two parallel Explore agents) before trusting them, per this repo's own "truth over velocity" doctrine (`REPO_RULES.md`).

**Purpose of this document**: a single, de-duplicated, verified task list to hand to Vertex AI cloud agents for an unattended ~48-hour run, targeting 100% completion of the local-first desktop product (Phase 6/SaaS explicitly out of scope, per `SessionGuardRevival.md`). Structured as one merged phase list (supersedes both audits' own numbering) with a crosswalk table back to each audit's original IDs, so an agent picking up either source document can map forward into this one.

---

## Corrections to both source audits (verified this session, not present in either document)

Both audits state their **top/#1 risk** is that `fix/revival13-gap-fixes` is unmerged to `main` for 2.5 weeks with no observed GitHub Actions run. **This is false as of right now** — neither audit ran `git fetch origin main` before writing that finding, so both were reading a stale local `main` ref.

Verified via `git fetch`, `gh pr view 4`, `gh run list`:
- PR #4 (`fix/revival13-gap-fixes` → `main`) **merged 2026-07-25T10:50:04Z**, merge commit `e562f7a5`. All 7 commits from the branch are in `origin/main` today.
- Real GitHub Actions runs **did** execute on GitHub's own runners and passed: `governance-gate`, `Test Suite`, `Bundled Backend Smoke`, and `build.yml` all show `success` both on PR #4 and on the post-merge push to `main`.
- The only workflow that fails consistently (on every push, PR, and the merge itself) is `.github/workflows/repo-drift-check.yml` — 0-second duration, consistent with an opt-in check short-circuiting because its `DRIFT_CANONICAL_REPO` secret isn't set in this environment, not a real failure. Needs a decision (make it a true no-op/skip status, or configure it), not a "branch is unmerged" panic.

This changes the roadmap materially: **Phase A1/Phase-1's "merge branch + observe green CI" is already done.** What's still real and still open:
- The required gate (`gate.yml` → `governance-gate`) genuinely never builds/typechecks `frontend/` — confirmed independently (see Workstream 1). This is a real, still-open gap, just not the same gap as "CI never ran."
- Everything else both audits found in security, UX, bundling, async, and docs was independently re-confirmed this session (see per-workstream verification notes below) and is real.

Three uncommitted items currently sit in the working tree from this session: `docs/governance/DEFERRED_WORK.md` (5 lines added), and the two new audit `.md` files (untracked). These should be committed via a fresh PR (there is no open PR right now) as part of Workstream 6, not left dangling.

---

## Crosswalk: this plan → original audit IDs

| This plan | Claude Code audit | Codex audit |
|---|---|---|
| WS1 — Gate fidelity & CI truth | A1, A5, Finding #1, #10 | Phase 1, Finding (CI/gate truth gap) |
| WS2 — Security & auth hardening | A2, A4, B4, Finding #2, #8, #9 | Phase 3, Security §7 |
| WS3 — Desktop runtime bundling | Phase D (D1–D6), Finding #6 | Phase 2, §4 |
| WS4 — Frontend UX completion + shell polish | Phase C (C1–C7), Finding #3, #4 | Phase 5, §5 |
| WS5 — Async engine migration | B1, Finding #5 | Phase 4 |
| WS6 — Docs consolidation & hygiene | A3, Phase E, Finding #10 | Phase 6 |
| WS7 — Clean-VM release rehearsal | D5 (X1) | Phase 7 |

---

## Verified ground truth (this session, both Explore agents + direct reads)

- `git`: branch already merged to `main`; nothing outstanding to merge. Uncommitted: `DEFERRED_WORK.md` diff + 2 new audit files.
- `gate.yml` → `bash scripts/verify.sh` only; `scripts/verify.sh`/`verify.ps1` detect Node projects only via **root-level** lockfiles (`pnpm-lock.yaml`/`yarn.lock`/`package-lock.json`), which don't exist at repo root (only `frontend/package-lock.json` does) — so the required gate **never runs `npm ci`/`tsc`/build against `frontend/`**. Confirmed via direct read of `scripts/verify.sh:68-73`, `verify.ps1:74-77`, `gate.yml:22-39`.
- `test.yml` and `build.yml` **do** check frontend (`cd frontend && npm ci && npx tsc --noEmit`, `npm run build`) but neither is the required merge gate.
- `desktop_shell/bundle/` — only `README.md`, confirmed empty of binaries.
- `desktop_shell/src-tauri/bundled_app/` — **exists and is polluted with runtime residue**: `config/sessionguard.db`, 8× `__pycache__` dirs with compiled `.pyc`, a full `storage/` tree (`exports`, `recordings/live`, `uploads`). This is generated/runtime output living inside what should be a clean staged-source directory — a packaging-hygiene bug not previously called out as sharply as this in either audit.
- `backend/main.py:60-79` — `/api/v1/auth`, `/api/v1/health`, `/api/v1/upload`, `/api/v1/jobs` are all globally exempt from the auth middleware. `uploads.py` and `jobs.py` confirmed to allow fully anonymous access (job submit/poll/cancel/list all proceed with `user_id = None` when no token is present — `jobs.py` raises no `HTTPException` for missing auth at all).
- `backend/auth/service.py:41-49` — `SECRET_KEY` falls back to `secrets.token_hex(32)` (random per-process) if unset in env and absent from config — confirmed, invalidates JWTs across restarts unless explicitly set.
- Backend host binding — confirmed **loopback-only everywhere** (`127.0.0.1` in all launcher scripts and `main.rs`); no `0.0.0.0` bind found anywhere. This closes out Claude Code audit's open item #9 as **verified safe, no action needed**.
- `backend/routes/intelligence.py` — **no doubled path segment** confirmed (router has no own prefix, mounted once at `/api/v1/intelligence`, route paths don't repeat "intelligence"). The bug both audits' predecessor docs described is already fixed; Codex's audit already noted README is stale on this point. No code fix needed — only a doc correction.
- `frontend/src/App.tsx` — confirmed extensive mojibake (21+ lines, `â€"`/`Â·`-style UTF-8-as-Latin-1 corruption) in comments, nav icons, and **user-visible UI text** (`v0.8 · Phase 7` renders in the sidebar, line 192). Also found (new, not in either audit): a dead duplicate function `useKeyboardShortcutsWithImport` (lines 98-123) with an identical body to `useKeyboardShortcuts`, never called.

---

## Roadmap

### Workstream 1 — Gate fidelity & CI truth (do first — everything else's "done" claims depend on this being trustworthy)
> **DEFERRED in this session per Shayan: WS2 (auth hardening) below. WS1, WS3–WS7 active.**

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W1.1 | Make `scripts/verify.sh`/`verify.ps1` detect and run the `frontend/` subproject (`npm ci`, `npx tsc --noEmit`, `npm run build`) in addition to root-level checks | Running `bash scripts/verify.sh` locally fails if a `frontend/` TS error or build break is introduced; passes clean today | S |
| W1.2 | Add a minimal desktop-bundle smoke step to the required gate (reuse `bundled-backend-smoke.yml`'s logic, or at minimum validate `tauri.conf.json` + confirm `stage-backend.js` produces a clean `bundled_app/`) | `gate.yml` fails if bundled backend startup regresses or `bundled_app/` staging breaks | M |
| W1.3 | Resolve `repo-drift-check.yml`'s constant 0s failure — either configure `DRIFT_CANONICAL_REPO` properly so it's a real check, or change its no-secret path to report `skipped`/neutral instead of `failure` so it stops looking like a red build | Workflow shows `success` or `skipped`, never `failure`, when the secret is intentionally absent | S |
| W1.4 | Resolve the open secret-scan review (`DEFERRED_WORK.md` 2026-07-24 item) — classify each of the 8 flagged files as true/false positive; fix true positives, add scoped exclusions with a documented reason | Secret-scan step passes with zero unexplained flags; each exclusion has an inline comment or governance-doc note | M |
| W1.5 | Fix `test_check_repo_drift` flakiness (git repo setup race in parallel temp dirs) | 10 consecutive full-suite runs, 0 failures on this test | S |
| W1.6 | Commit the currently-uncommitted `DEFERRED_WORK.md` change + both 2026-08-11 audit files, and open a fresh PR (there is currently no open PR) | Clean working tree; PR opened, all gate/test/build/smoke checks green on GitHub's runners | S |

**Definition of Done**: the required gate actually proves backend + frontend + desktop-staging correctness; every workflow shows a real pass/fail, not a silent skip disguised as failure.

### Workstream 2 — Security & auth hardening  ⛔ DEFERRED THIS SESSION (local-only, not SaaS yet — per Shayan 2026-08-11)

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W2.1 | Require authentication for `/api/v1/upload` and `/api/v1/jobs`, or explicitly scope and document an intentional guest mode if anonymous local use is desired | Anonymous callers cannot submit/cancel/list/poll another user's jobs or uploads without an explicit, documented guest-mode decision | M |
| W2.2 | Promote `SECRET_KEY` from optional-with-random-fallback to required at release-build startup (fail fast with a clear message if unset), keeping the dev-convenience fallback only behind an explicit `SESSIONGUARD_DEV_MODE`-style flag | Release build refuses to start without `SECRET_KEY` set; dev/local mode still works without friction | S |
| W2.3 | Stop returning raw local filesystem paths from upload-listing endpoints | Upload API responses no longer leak absolute host paths to any localhost caller | S |
| W2.4 | Document the local-only threat model explicitly (single-user-local, loopback-only bind, no multi-tenant auth) now that host-binding is verified safe, so this isn't re-litigated by a future audit | A short section in `SessionGuardRevival.md` or `REPO_RULES.md` states the threat model and cites this session's verified loopback-bind finding | S |

### Workstream 3 — Desktop runtime bundling (the largest single scope item; execute `SESSIONGUARDREVIVAL1.4.md`'s existing task board as written)

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W3.0 | Clean `desktop_shell/src-tauri/bundled_app/` of runtime residue (`__pycache__`, `config/sessionguard.db`, `storage/*`) and add `.gitignore`/staging-script rules so `stage-backend.js` never re-introduces it | Staged bundle contains only source needed for packaging; verified via a fresh `node desktop_shell/stage-backend.js` run producing a clean tree | S |
| W3.1 | 1.4 P1–P4: scripted, checksum-pinned Windows embeddable Python + `pip install` into `Lib/site-packages`; `find_python()` in `main.rs` checks bundled path first | `pip install -t python/Lib/site-packages -r requirements.txt` runs in CI; bundled interpreter found before system PATH | L |
| W3.2 | 1.4 P3: macOS/Linux Python bundling decision (python-build-standalone vs. bundled venv), executed | Same acceptance bar as W3.1, cross-platform | XL |
| W3.3 | 1.4 T1–T3: Tesseract bundling + licensing check + `tests/test_ocr_benchmark.py` re-verified against the bundled binary | OCR benchmark passes against bundled Tesseract specifically, not system install | L |
| W3.4 | 1.4 F1–F3: FFmpeg bundling + licensing check + chunking/resume re-verification against bundled binary | Video chunking/resume tests pass against bundled FFmpeg | L |
| W3.5 | 1.4 X1: provision genuinely clean Windows/macOS/Linux VMs, run the acceptance test manually (OCR on a sample screenshot, session create/view, `sessionguard --version` offline) | Passes on all three, nothing pre-installed — do not mark done without this step | M + VM time |
| W3.6 | 1.4 X2–X4: wire bundling into CI on tagged releases; update installer-size expectations in docs; decide and document the auto-updater's bundle-vs-binary-only update story | CI verifies the bundle on every tagged release; docs reflect real installer sizes; update mechanism documented | M |

### Workstream 4 — Frontend UX completion + shell polish

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W4.0 | Fix `frontend/src/App.tsx` mojibake (re-save as clean UTF-8, no `â€"`/`Â·`-corrupted glyphs) and remove stale `v0.8 · Phase 7` UI text (line 192) + header comment; delete dead `useKeyboardShortcutsWithImport` duplicate (lines 98-123) | No corrupted characters anywhere in the shipped UI; version/phase text reads correctly from `backend/version.py`'s single source of truth or an equivalent frontend constant; dead code removed | S |
| W4.1 | Alert Explanations UI — surface `GET /alerts/{id}/explain` | Clicking an alert shows the LLM root-cause explanation with evidence citations | M |
| W4.2 | AI Cost Tracking + Budget UI — surface `GET /api/v1/ai-cost/usage` | Settings/Dashboard shows $/session, running total, budget threshold, fallback status | M |
| W4.3 | Prompt Versioning + A/B UI — surface `GET/POST /api/v1/prompts` | Admin-gated panel lists versions, lets an operator activate one or trigger A/B comparison | M |
| W4.4 | Evidence Package UI — surface `POST /sessions/{id}/evidence` + verify endpoint | Session detail page has an "Export Evidence Package" button; downloads ZIP; verify badge shown | M |
| W4.5 | Clustering UI — surface `GET /intelligence/clusters` | Page/panel shows session cohorts (a grouped table is sufficient for v1) | M |
| W4.6 | Dataset Quality UI — surface `GET /intelligence/dataset-quality` | Admin panel shows completeness/bias/distribution metrics, exportable | M |
| W4.7 | Projects/Teams frontend + desktop parity | Basic CRUD UI for existing backend Projects API; desktop parity | L |
| W4.8 | DB backup/restore UI (`DEFERRED_WORK.md` C5 second half) | `GET /api/v1/admin/backup` (SQLite `VACUUM INTO`) + Settings panel with download/restore + confirm-restore modal | M |
| W4.9 | Live Monitor (screen mode) — bring frontend/desktop from ⚠️ to ✅, add tests, fix docs | README's feature table shows consistent ✅ across backend/frontend/desktop/tests for this row | L |

**Definition of Done**: README's Feature Completeness table has zero `❌` in the Frontend column for any row where Backend is `✅`, or an explicit justified exception is documented.

### Workstream 5 — Async engine migration

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W5.1 | Convert the 6 sync engine files to natively async (`aiosqlite` or equivalent); remove `asyncio.to_thread()` wrapping now unneeded | All engine DB calls use an async driver; wrapper calls removed from routes; full test suite still green | L |
| W5.2 | Live-verify AI streaming against a real NVIDIA NIM endpoint with an approved key (REPO_RULES R24 approval required first — do not proceed without approval) | One real call recorded, `source == "nvidia_ai"` confirmed, tokens logged in `ai_cost_log`, regression test added (can stay mocked after) | S once key approved |

### Workstream 6 — Docs consolidation & hygiene

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W6.1 | Rewrite `D:/AgentDevWork/repos/OBSIDIAN-TEAM-BOARDROOM/project-docs/SESSIONGUARD.md` — confirmed today to still describe PySide6 as the desktop shell and contain no real status; reflect current reality (Tauri primary, PySide6 legacy) or mark historical | Boardroom brief matches current architecture and status | S |
| W6.2 | Correct `README.md`'s stale claim about `intelligence.py`'s doubled path segment (confirmed fixed this session, not a live bug) | README no longer claims a fixed bug is open | S |
| W6.3 | Normalize stale version headers (several files still say `v1.2.0`) against `backend/version.py`'s single source of truth | No conflicting version strings anywhere in source headers or UI | S |
| W6.4 | Tighten `README.md` to separate "verified working today" / "implemented but externally unverified" / "intentionally deferred" | A new reader can determine release-readiness from README + one active status doc | M |

### Workstream 7 — Clean-machine release rehearsal (final gate, depends on WS1 + WS3)

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W7.1 | Scripted release rehearsal on a clean Windows VM (then macOS/Linux as packaging matures): install, launch, login, upload, OCR, AI fallback, export/evidence, updater | Clean-machine Windows acceptance succeeds end-to-end offline except where external AI is intentionally optional | M |
| W7.2 | Produce a release checklist artifact with logs/screenshots, saved under `audits/` or `docs/operations/` | Checklist green and committed | S |

---

## Exit criteria for "100% complete, local-first desktop track"

- WS1: required gate proves backend + frontend + desktop-staging; no phantom-red workflows.
- WS2: no anonymous write access to upload/job endpoints without an explicit documented guest mode; `SECRET_KEY` required in release builds. ⛔ (deferred this session)
- WS3: clean-VM acceptance test (Windows/macOS/Linux, nothing pre-installed) passes per `SESSIONGUARDREVIVAL1.4.md`'s own bar.
- WS4: README's Feature Completeness table has no unjustified `❌` in Frontend where Backend is `✅`.
- WS5: engine layer natively async; one real NVIDIA NIM call verified.
- WS6: all docs (README, revival docs, boardroom brief) agree with actual code state; no stale version/bug claims.
- WS7: a documented, green clean-machine release rehearsal exists under `audits/` or `docs/operations/`.

## Notes for the Vertex AI agent handoff

- WS1 should land first (or at minimum W1.1/W1.6) since every other workstream's "tests pass" claim is only as trustworthy as the gate that checks it — this mirrors the repo's own established "trust gap first" doctrine from `SESSIONGUARDREVIVAL1.3.md`.
- WS2, WS3, WS4, WS5, WS6 are largely independent of each other and can run in parallel across separate agents/branches once WS1 lands, merging via separate PRs (this repo works PR-per-branch, confirmed via `gh pr list`).
- WS7 must run last — it's the acceptance gate for WS3 in particular, and per `SESSIONGUARDREVIVAL1.4.md`'s own explicit warning, do not mark bundling complete without it.
- W5.2 (live NVIDIA key call) requires human approval per REPO_RULES R24 before any agent spends real API budget — flag and pause rather than proceeding autonomously.
- Before starting, agents should re-run `git fetch origin main` and `gh pr list`/`gh run list` themselves rather than trusting either prior audit's "branch/CI state" section verbatim — this session already caught both audits stale on exactly that point.
- **This session is cloud-only (Vertex). Do NOT dispatch local Claude Code / Codex for phase execution.** WS2 is deferred (not SaaS yet) — skip unless Shayan reverses.
