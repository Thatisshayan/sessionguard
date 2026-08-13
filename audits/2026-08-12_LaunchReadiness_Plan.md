# SessionGuard — 100% Functionality & Launch-Readiness Plan (Local-First Desktop, No SaaS)

**Date:** 2026-08-12
**Author:** Claude Code (Sonnet 5), refreshing `audits/2026-08-11_CloudDev_Roadmap.md`
**Handoff target:** Codestral 2 (cloud agent) — this document is self-contained; do not require the producing session's context.
**Scope:** Get SessionGuard to 100% functional, launch-ready as a **local-first desktop product**. Phase 6 / SaaS / multi-tenant is explicitly out of scope and must not be started under this plan.

---

## 0. What changed since the 2026-08-11 roadmap (re-verified 2026-08-12)

The prior roadmap (`audits/2026-08-11_CloudDev_Roadmap.md`) deferred **Workstream 2 (security & auth hardening)** because the product was local-only and not SaaS yet. **That deferral is lifted in this plan** — the user wants WS2 included in the launch-readiness bar now, while still explicitly not building SaaS/multi-tenant auth. WS2 below is scoped to what a genuinely *shippable* local-desktop product needs (no anonymous write access, no permanently-rotating session keys), not to SaaS-grade RBAC/multi-tenancy — that stays out of scope.

Re-verified directly against the repo on 2026-08-12 (do not re-trust unverified claims from older docs — re-check yourself before acting):

| Claim | Status |
|---|---|
| `fix/revival13-gap-fixes` branch merged to `main`, CI green | ✅ Confirmed — `origin/main` HEAD is merge commit `e562f7a5` (2026-07-25); local branch commits (`4754100`, `d270d67`, `04409b5`, `c062d72`, `8ecfa2a`) are all already contained in `origin/main`. No merge action needed. |
| `frontend/src/App.tsx` mojibake / stale "v0.8 · Phase 7" text | ❌ Still present — confirmed at lines 2, 192, 222, 252 (`â€"`, `Â·`, `â—`, `â³` corruption; stale phase/version string). WS4.0 still open. |
| `scripts/verify.sh` skips `frontend/` in the required gate | ❌ Still true — `scripts/verify.sh:72` only checks a root-level `package-lock.json`, which doesn't exist (only `frontend/package-lock.json` does). WS1.1 still open. |
| `desktop_shell/bundle/` has bundled Python/Tesseract/FFmpeg | ❌ Still only `README.md` — WS3 (runtime bundling) is fully unstarted, still the largest open scope item. |
| `desktop_shell/src-tauri/bundled_app/` staging residue | ⚠️ Partially improved — no longer shows `__pycache__`/`.db` residue in the top-level listing, but a `storage/` directory still exists inside the staged tree. Verify whether it's empty scaffolding or live runtime output before marking W3.0 done. |
| `/api/v1/upload`, `/api/v1/jobs` exempt from auth middleware | ❌ Still true — confirmed in `backend/main.py:68-69`. Anonymous upload/job submission is still possible. WS2.1 still open. |
| `SECRET_KEY` falls back to a random per-process value if unset | ❌ Still true — `backend/auth/service.py:49` (`_load_secret() or secrets.token_hex(32)`). WS2.2 still open. |
| Working tree has uncommitted files | ⚠️ `docs/governance/DEFERRED_WORK.md` modified, plus the three 2026-08-11 audit `.md` files and this plan are untracked. Also a stray `nul` file at repo root (Windows artifact from a misdirected command) — delete it, it's not real content. |

**Bottom line:** almost everything both 2026-08-11 audits found is still open today. The only workstream item that's fully resolved is the branch-merge itself. Treat every other row below as active work.

---

## 1. Ground rules for whoever executes this (Codestral 2 / any cloud agent)

- **Re-verify before trusting.** Every "still open" claim above was checked by direct file/grep read on 2026-08-12. Re-check the specific file/line yourself before starting each workstream — code may have moved since this plan was written.
- **No SaaS work.** Do not add multi-tenant auth, hosted billing, cloud deployment configs, or anything from `SessionGuardRevival.md`'s Phase 6. If a task looks like it's drifting toward SaaS, stop and flag it instead of proceeding.
- **WS2 (security) is now IN SCOPE**, scoped narrowly to local-desktop shippability (see WS2 below) — not SaaS-grade RBAC.
- **W5.2 (live NVIDIA API key call) requires human approval before spending** (REPO_RULES R24). Flag and pause; do not proceed autonomously.
- **Branch/PR workflow**: this repo works PR-per-branch (per `AGENTS.md`). Do not push directly to `main`.
- **Do not mark WS3 (runtime bundling) or WS7 (release rehearsal) complete without actually running the clean-VM acceptance test.** This project has a documented three-times-repeated failure pattern of "marked done, wasn't run" (see `audits/2026-08-11_ClaudeCode_FullSpectrum_Audit.md` §1) — do not add a fourth instance.
- Delete the stray `nul` file at repo root as a first housekeeping step (harmless, but it's Windows shell noise, not a stray user file — safe to remove).

---

## 2. Workstreams

### WS1 — Gate fidelity & CI truth (do first — everything else's "done" claims depend on this)

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W1.1 | Make `scripts/verify.sh`/`verify.ps1` detect and run the `frontend/` subproject (`npm ci`, `npx tsc --noEmit`, `npm run build`) in addition to root-level checks | `bash scripts/verify.sh` fails if a `frontend/` TS error or build break is introduced; passes clean today | S |
| W1.2 | Add a minimal desktop-bundle smoke step to the required gate (reuse `bundled-backend-smoke.yml` logic, or at minimum validate `tauri.conf.json` + confirm `stage-backend.js` produces a clean `bundled_app/`) | `gate.yml` fails if bundled backend startup regresses or staging breaks | M |
| W1.3 | Resolve `repo-drift-check.yml`'s constant 0s failure — either configure `DRIFT_CANONICAL_REPO` properly, or make its no-secret path report `skipped`/neutral instead of `failure` | Workflow shows `success` or `skipped`, never `failure`, when the secret is intentionally absent | S |
| W1.4 | Resolve the open secret-scan review (`DEFERRED_WORK.md` 2026-07-24 item) — classify each of the 8 flagged files as true/false positive; fix true positives, add scoped exclusions with a documented reason | Secret-scan step passes with zero unexplained flags; each exclusion has an inline comment or governance-doc note | M |
| W1.5 | Fix `test_check_repo_drift` flakiness (git repo setup race in parallel temp dirs) | 10 consecutive full-suite runs, 0 failures on this test | S |
| W1.6 | Commit currently-uncommitted files (`DEFERRED_WORK.md` diff, the 3 audit docs, this plan); delete stray `nul`; open a fresh PR | Clean working tree; PR opened, all gate/test/build/smoke checks green on GitHub's runners | S |

**Definition of Done:** the required gate actually proves backend + frontend + desktop-staging correctness; every workflow shows a real pass/fail, never a silent skip disguised as failure.

---

### WS2 — Security & auth hardening (local-desktop scope, now ACTIVE — not SaaS)

Scope discipline: this is "no anonymous write access, no accidental data exposure, no key that resets every restart" — not multi-user RBAC, not hosted auth. Keep it that narrow.

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W2.1 | Require authentication for `/api/v1/upload` and `/api/v1/jobs`, or explicitly scope and document an intentional single-user guest mode if anonymous local use is desired | Anonymous callers cannot submit/cancel/list/poll another session's jobs or uploads without an explicit, documented guest-mode decision | M |
| W2.2 | Promote `SECRET_KEY` from optional-with-random-fallback to required at release-build startup (fail fast with a clear message if unset); keep the dev-convenience fallback only behind an explicit `SESSIONGUARD_DEV_MODE`-style flag | Release build refuses to start without `SECRET_KEY` set; local dev mode still works without friction | S |
| W2.3 | Stop returning raw local filesystem paths from upload-listing endpoints | Upload API responses no longer leak absolute host paths to any localhost caller | S |
| W2.4 | Document the local-only threat model explicitly (single-user-local, loopback-only bind — already verified safe, no multi-tenant auth) so it isn't re-litigated by a future audit, and so it's clear this is deliberately not SaaS-grade | A short section in `SessionGuardRevival.md` or `REPO_RULES.md` states the threat model and cites the loopback-bind verification | S |
| W2.5 | Re-run `docs/governance/DEFERRED_WORK.md`'s secret-scan review as part of W1.4 rather than separately — do not duplicate | Covered by W1.4; no separate action | — |

**Definition of Done:** no endpoint accepts an unauthenticated write with real consequences (job control, uploads); the app fails fast rather than silently running with an insecure default key; the threat model is written down.

---

### WS3 — Desktop runtime bundling (the largest single scope item — execute `SESSIONGUARDREVIVAL1.4.md`'s existing task board as written)

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W3.0 | Clean `desktop_shell/src-tauri/bundled_app/` of any runtime residue (verify the `storage/` subdirectory found there on 2026-08-12 — confirm empty-scaffold vs. live output; remove if the latter) and add `.gitignore`/staging-script rules so `stage-backend.js` never re-introduces it | Staged bundle contains only source needed for packaging; verified via a fresh `node desktop_shell/stage-backend.js` run producing a clean tree | S |
| W3.1 | 1.4 P1–P4: scripted, checksum-pinned Windows embeddable Python + `pip install` into `Lib/site-packages`; `find_python()` in `main.rs` checks bundled path first | `pip install -t python/Lib/site-packages -r requirements.txt` runs in CI; bundled interpreter found before system PATH | L |
| W3.2 | 1.4 P3: macOS/Linux Python bundling decision (python-build-standalone vs. bundled venv), executed | Same acceptance bar as W3.1, cross-platform | XL |
| W3.3 | 1.4 T1–T3: Tesseract bundling + licensing check + `tests/test_ocr_benchmark.py` re-verified against the bundled binary | OCR benchmark passes against bundled Tesseract specifically, not system install | L |
| W3.4 | 1.4 F1–F3: FFmpeg bundling + licensing check + chunking/resume re-verification against bundled binary | Video chunking/resume tests pass against bundled FFmpeg | L |
| W3.5 | 1.4 X1: provision genuinely clean Windows/macOS/Linux VMs, run the acceptance test manually (OCR on a sample screenshot, session create/view, `sessionguard --version` offline) | Passes on all three, nothing pre-installed — do not mark done without this step | M + VM time |
| W3.6 | 1.4 X2–X4: wire bundling into CI on tagged releases; update installer-size expectations in docs; decide and document the auto-updater's bundle-vs-binary-only update story | CI verifies the bundle on every tagged release; docs reflect real installer sizes; update mechanism documented | M |

---

### WS4 — Frontend UX completion + shell polish

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W4.0 | Fix `frontend/src/App.tsx` mojibake (re-save as clean UTF-8) and remove stale `v0.8 · Phase 7` text (line 192) + header comment (line 2); delete dead `useKeyboardShortcutsWithImport` duplicate if still present | No corrupted characters anywhere in the shipped UI; version/phase text reads from `backend/version.py`'s single source of truth or an equivalent frontend constant; dead code removed | S |
| W4.1 | Alert Explanations UI — surface `GET /alerts/{id}/explain` | Clicking an alert shows the LLM root-cause explanation with evidence citations | M |
| W4.2 | AI Cost Tracking + Budget UI — surface `GET /api/v1/ai-cost/usage` | Settings/Dashboard shows $/session, running total, budget threshold, fallback status | M |
| W4.3 | Prompt Versioning + A/B UI — surface `GET/POST /api/v1/prompts` | Admin-gated panel lists versions, lets an operator activate one or trigger A/B comparison | M |
| W4.4 | Evidence Package UI — surface `POST /sessions/{id}/evidence` + verify endpoint | Session detail page has an "Export Evidence Package" button; downloads ZIP; verify badge shown | M |
| W4.5 | Clustering UI — surface `GET /intelligence/clusters` | Page/panel shows session cohorts (a grouped table is sufficient for v1) | M |
| W4.6 | Dataset Quality UI — surface `GET /intelligence/dataset-quality` | Admin panel shows completeness/bias/distribution metrics, exportable | M |
| W4.7 | Projects/Teams frontend + desktop parity | Basic CRUD UI for existing backend Projects API; desktop parity | L |
| W4.8 | DB backup/restore UI (`DEFERRED_WORK.md` C5 second half) | `GET /api/v1/admin/backup` (SQLite `VACUUM INTO`) + Settings panel with download/restore + confirm-restore modal | M |
| W4.9 | Live Monitor (screen mode) — bring frontend/desktop from ⚠️ to ✅, add tests, fix docs | README's feature table shows consistent ✅ across backend/frontend/desktop/tests for this row | L |

**Definition of Done:** README's Feature Completeness table has zero `❌` in the Frontend column for any row where Backend is `✅`, or an explicit justified exception is documented.

---

### WS5 — Async engine migration

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W5.1 | Convert the remaining sync engine files to natively async (`aiosqlite` or equivalent); remove `asyncio.to_thread()` wrapping now unneeded | All engine DB calls use an async driver; wrapper calls removed from routes; full test suite still green | L |
| W5.2 | Live-verify AI streaming against a real NVIDIA NIM endpoint with an approved key (**REPO_RULES R24 approval required first — do not proceed without approval**) | One real call recorded, `source == "nvidia_ai"` confirmed, tokens logged in `ai_cost_log`, regression test added (can stay mocked after) | S once key approved |

---

### WS6 — Docs consolidation & hygiene

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W6.1 | Rewrite `D:/AgentDevWork/repos/OBSIDIAN-TEAM-BOARDROOM/project-docs/SESSIONGUARD.md` to reflect current architecture/status (Tauri primary, PySide6 legacy) or mark historical | Boardroom brief matches current architecture and status | S |
| W6.2 | Correct any stale README claims (e.g. the already-fixed `intelligence.py` doubled-path-segment bug) | README no longer claims a fixed bug is open | S |
| W6.3 | Normalize stale version headers (files still saying `v1.2.0`) against `backend/version.py`'s single source of truth | No conflicting version strings anywhere in source headers or UI | S |
| W6.4 | Tighten `README.md` to separate "verified working today" / "implemented but externally unverified" / "intentionally deferred" | A new reader can determine release-readiness from README + one active status doc | M |

---

### WS7 — Clean-machine release rehearsal (final gate, depends on WS1 + WS3)

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| W7.1 | Scripted release rehearsal on a clean Windows VM (then macOS/Linux as packaging matures): install, launch, login, upload, OCR, AI fallback, export/evidence, updater | Clean-machine Windows acceptance succeeds end-to-end offline except where external AI is intentionally optional | M |
| W7.2 | Produce a release checklist artifact with logs/screenshots, saved under `audits/` or `docs/operations/` | Checklist green and committed | S |

---

## 3. Sequencing

```
WS1 (gate truth) ──┬─→ WS2 (security) ──┐
                    ├─→ WS3 (bundling) ──┤
                    ├─→ WS4 (UX)         ├─→ WS7 (release rehearsal, LAST)
                    ├─→ WS5 (async)      │
                    └─→ WS6 (docs)      ─┘
```

- **WS1 lands first** (or at minimum W1.1/W1.6) — every other workstream's "tests pass" claim is only as trustworthy as the gate that checks it.
- **WS2, WS3, WS4, WS5, WS6 are independent of each other** and can run in parallel across separate agents/branches once WS1 lands, merging via separate PRs.
- **WS7 must run last** — it's the acceptance gate for WS3 in particular; do not mark bundling complete without it.

---

## 4. Exit criteria for "100% complete, local-first desktop launch-ready"

- WS1: required gate proves backend + frontend + desktop-staging; no phantom-red workflows.
- WS2: no anonymous write access to upload/job endpoints without an explicit documented guest mode; `SECRET_KEY` required in release builds; threat model documented.
- WS3: clean-VM acceptance test (Windows/macOS/Linux, nothing pre-installed) passes per `SESSIONGUARDREVIVAL1.4.md`'s own bar.
- WS4: README's Feature Completeness table has no unjustified `❌` in Frontend where Backend is `✅`.
- WS5: engine layer natively async; one real NVIDIA NIM call verified (pending R24 approval).
- WS6: all docs (README, revival docs, boardroom brief) agree with actual code state; no stale version/bug claims.
- WS7: a documented, green clean-machine release rehearsal exists under `audits/` or `docs/operations/`.

## 5. Effort roll-up (rough, solo-equivalent sizing: S=<1d, M=1-3d, L=3-7d, XL=1-3wk)

| Workstream | Rough effort |
|---|---|
| WS1 — Gate fidelity | ~1 week |
| WS2 — Security (narrow, local-scope) | ~3-5 days |
| WS3 — Runtime bundling | ~4-6 weeks (largest item) |
| WS4 — UX completion | ~2-3 weeks |
| WS5 — Async migration | ~1-2 weeks |
| WS6 — Docs hygiene | ~2-3 days |
| WS7 — Release rehearsal | ~3-4 days |

Total, sequential-equivalent: roughly **10-14 weeks** of focused work — parallelizable across WS2/3/4/5/6 once WS1 lands, so wall-clock time with multiple agents working concurrently can be materially shorter than this sum.

---

*Plan refreshed by Claude Code (Sonnet 5) on 2026-08-12, building on `audits/2026-08-11_ClaudeCode_FullSpectrum_Audit.md`, `audits/2026-08-11_Codex_FullSpectrum_Audit.md`, and `audits/2026-08-11_CloudDev_Roadmap.md`. WS2 reactivated per explicit user instruction (2026-08-12): include security/auth hardening in the launch-readiness bar now, while keeping SaaS/multi-tenant work out of scope.*
