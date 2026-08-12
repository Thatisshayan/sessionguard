# SessionGuard — Full-Spectrum Audit (Claude Code)

**Date:** 2026-08-11
**Agent:** Claude Code (Sonnet 5)
**Scope:** Full-spectrum (build/test/CI, architecture, revival-gap status, desktop bundling, UX completeness, docs accuracy, security) — not security-only
**Rule:** Rule 5 (base on code + docs + prior audits), Rule 6 (save under `audits/`)

## 0. How this audit was produced, and its own honesty disclosure

Per this repo's own Rule 3/R4 ("no fake completions, no invented verification"), stated up front:

- **I could not execute `python -m pytest`, `npm run build`, `npx tsc --noEmit`, or any GitHub Actions run in this session.** The harness's permission mode required interactive approval for every test/build invocation (Bash and PowerShell both), and no interactive approver was available in this non-interactive audit session. Every attempt is logged as denied, not skipped silently.
- Where a fact depends on "did it actually run," I have used **the repo's own most recent locally-verified evidence** (`audits/2026-07-25_OpenCode_Revival13_ProperFix_Audit.md`: "Full test suite: 245 passed, 6 skipped") and cross-checked its claims against current code (grep/read), rather than re-asserting an unverified pass/fail myself.
- Where I *could* verify statically (router mounts, frontend URL construction, file existence, requirements.txt contents, workflow YAML), I did, and say so explicitly below.
- I did not have filesystem access to `D:\AgentDevWork\repos\OBSIDIAN-TEAM-BOARDROOM\project-docs\SESSIONGUARD.md` (outside this session's allowed working directory) — that source, requested in the task prompt, could not be read. This audit is based on the in-repo docs instead (`SessionGuardRevival.md`, `SESSIONGUARDREVIVAL1.3.md`, `SESSIONGUARDREVIVAL1.4.md`, `README.md`, `AGENTS.md`, `REPO_RULES.md`, prior `audits/*.md`, and direct code inspection).

**Repository state at time of audit:**
- Working directory: `D:\AgentDevWork\repos\SESSIONGUARD`, branch `fix/revival13-gap-fixes`, clean working tree, up to date with `origin/fix/revival13-gap-fixes`.
- This branch is **7 commits ahead of `main`, unmerged** (`git log main..fix/revival13-gap-fixes --oneline` → 7 commits). `main`'s tip is `96524cb`. The branch tip is `4754100`.
- Last commit timestamp: 2026-07-25. Today is 2026-08-11 — **~2.5 weeks of no repo activity**, and the most substantive recent work (async-gap fixes, CodeRabbit review fixes) is sitting unmerged on a feature branch, not in `main`. Anyone reading `main` alone is looking at code from before the 1.3 sprint's gap-fix pass.

---

## 1. Executive Summary

SessionGuard is a single-user, local-first desktop/web app for casino-session analysis (OCR from screen recordings → structured events → behavioral/AI insights → exports/evidence packages). The project has a genuinely unusual amount of self-audit discipline: three generations of prior agents (Codex, OpenCode, Hermes) have already found and fixed severe "marked done but never run" bugs (broken CI, a desktop installer silently running six-phases-stale code, an entire AI router that 404'd end-to-end). That process is still working — this audit did **not** find a new instance of that failure class in the areas it could statically verify (AI router mount ✅, intelligence path-doubling fix ✅, version single-source-of-truth ✅).

What this audit adds beyond the existing `SESSIONGUARDREVIVAL1.3.md`/1.4 task boards:

1. **The branch/main divergence itself is now the top risk** — 7 commits of correctness fixes (admin-auth-check async conversion across 27 routes, SQLite lock-contention fix, async HTTP calls for AI) are sitting on an unmerged branch 2.5 weeks old. If `main` is what any packaging/release process reads, it is missing these fixes.
2. **This session could not independently re-verify "245 passed, 6 skipped"** — that number is one audit-cycle old (2026-07-25) and self-reported by the same iterative process being audited. It is plausible and consistent with static code inspection, but is not re-confirmed here. Flagging per R38 (claims need evidence) rather than restating it as newly-verified.
3. **The core desktop-runtime-bundling gap (1.4) remains completely unstarted**, confirmed by direct inspection: `desktop_shell/bundle/` contains only `README.md`, no binaries. The product cannot yet run on a machine without a pre-installed Python/Tesseract/FFmpeg, despite backend *source* bundling being fixed.
4. **UX completeness has real, currently-undocumented-as-audit-findings gaps**: 8 of ~30 features in the README's own completeness table are frontend-`❌` (Alert Explanations, AI Cost Tracking UI, Prompt Versioning UI, Evidence Package UI, Clustering UI, Dataset Quality UI, Projects/Teams frontend+desktop, Admin Panel desktop) — meaning backend capability with no way for the single target user to reach it through the app.
5. **Security posture is reasonable for the stated single-user-local threat model** and has improved materially (rate limiting, structured logging, SQLCipher option, secret-key rotation, upload validation) — but two specific items below (an unauthenticated local network bind, and a deferred secret-scan review) are worth a second look even under that model.

**Bottom line:** the project's engineering process is unusually self-correcting, but the audit trail shows a repeated pattern worth naming directly: work gets done, tested against mocks, marked "done," and only found wrong when someone actually runs it end-to-end. That pattern has now happened three times (CI, installer, AI router) across three different agents. The single highest-leverage next action is **merging `fix/revival13-gap-fixes` to `main` and getting one real CI run to go green on GitHub's runners** (not just locally) — until that happens, every "done" claim on this branch is provisional by the project's own stated standard (`SESSIONGUARDREVIVAL1.3.md`'s Track A rationale, applied to itself).

---

## 2. Build / Test / CI — Actual Status

### 2.1 What I verified directly (static, this session)

| Claim | Verification method | Result |
|---|---|---|
| `ai_analysis.router` mounted in `main.py` | `grep` on `backend/main.py:46,136` | ✅ Confirmed — imported line 46, `app.include_router(ai_analysis.router, prefix="/api/v1")` line 136 |
| `intelligence.py` path-doubling bug fixed | Read `intelligence.router` mount (`/api/v1/intelligence`) + route defs (`/ai/status` etc., no duplicate `/intelligence` segment) | ✅ Confirmed fixed — resolves to `/api/v1/intelligence/ai/status`, no longer doubled |
| Frontend `getAiStatus()` hits the right route | Read `frontend/src/services/api.ts:242` (`client.get('/ai/status')`) + axios interceptor (`API_VERSION` prefix logic, lines 8–24) | ✅ Confirmed — resolves through the `ai_analysis` router's `/api/v1/ai/status`, not `intelligence`'s. Two different backend routers both expose an `/ai/status`-shaped endpoint under different final paths (`/api/v1/ai/status` vs `/api/v1/intelligence/ai/status`) — this isn't a bug (frontend picks one correctly) but is a naming trap for the next person who greps for "ai/status" and finds two plausible candidates. Worth a comment or rename. |
| Backend version single-source-of-truth (B5, 1.3) | `grep` — not exhaustively re-read line-by-line this session, spot-checked `backend/version.py` exists | ✅ Present, consistent with 1.3's claim |
| `desktop_shell/bundle/` still empty (1.4 not started) | `ls desktop_shell/bundle` | ✅ Confirmed — only `README.md`, no binaries. 1.4's entire task board is genuinely unstarted, not partially done and mis-marked. |
| `desktop_shell/stage-backend.js` exists (1.3 finding #13 fix) | file existence check | ✅ Confirmed present |
| CI workflow files are structurally sane | Read `test.yml`, `gate.yml` in full | ✅ No obvious syntax errors; `test.yml` runs backend pytest + frontend `tsc --noEmit` + OCR benchmarks on `windows-latest`; `gate.yml` runs `scripts/verify.sh` on `ubuntu-latest` for non-`main` pushes and PRs to `main`. Did not verify `build.yml`, `bundled-backend-smoke.yml`, `repo-drift-check.yml` line-by-line this session (read in prior sessions per 1.3's finding log, not re-read here) |

### 2.2 What I could not verify this session

- **No actual `pytest` run.** Cannot confirm 245/6 or any other number as of *today*. The last locally-executed number on record is `audits/2026-07-25_OpenCode_Revival13_ProperFix_Audit.md`'s "Full test suite: 245 passed, 6 skipped (excluding pre-existing flaky `test_check_repo_drift`)" — 17 days stale relative to today's date, though only ~0 commits stale relative to the branch tip (no commits landed between that audit and now on this branch per `git log`).
- **No `npx tsc --noEmit` run.** `SessionGuardRevival.md` records "0 TS errors" as of 2026-07-22, before several since-then route/type changes (27 routes converted `def`→`async def` in the gap-fix branch — a mechanical change type unlikely to introduce TS errors since it's backend-only, but genuinely unverified this session).
- **No GitHub Actions run observed.** `docs/governance/DEFERRED_WORK.md` already lists this as open as of 2026-07-24: *"A1/A2 GitHub runner execution... no GitHub Actions run has been observed for this branch."* Still true as of this audit. This is the single most important unresolved verification gap given this project's history of CI silently failing (1.3 finding #1–#11) for an unknown period before anyone looked.
- **`gh pr status`/`gh pr list` were blocked by the permission system** in this session (required approval, none available) — could not confirm whether a PR exists for `fix/revival13-gap-fixes` → `main`, or its CI check status if one does.

### 2.3 Known-flaky test (carried forward, still open)

`test_check_repo_drift.py::test_in_sync_repos_exit_zero` — documented in `DEFERRED_WORK.md` (2026-07-25) as failing ~40% of the time in full-suite runs due to a git-repo-setup race in parallel temp directories. Not re-verified this session (would require a live run), but the root-cause description is plausible and specific enough to trust as accurate. **This is a CI-gate reliability risk**: an opt-in test that fails intermittently on a *governance* check (canonical-repo drift) undermines confidence in the one thing that's supposed to catch drift.

### 2.4 CI/test verdict

**Structurally sound, functionally unconfirmed.** The workflows read correctly, the last known local run was green, and the fixes since then are the kind (async/await mechanical conversion, timeout parameter) that are low-risk for silent regression — but this project's own history is three-for-three on "looked done, wasn't" when nobody actually watched it run. Recommend: do not treat this branch as release-ready until an actual GitHub Actions run against `fix/revival13-gap-fixes` (or its merge to `main`) is observed green, per the project's own Track A doctrine.

---

## 3. Architecture

Confirmed from `README.md`'s architecture section, cross-checked with `ls`/`grep` this session (routes count: 41 files under `backend/routes/`, engines: 25 files under `engines/`, tests: 31 `test_*.py` files under `tests/`):

- **Backend**: FastAPI, 41 route files (README claims "30+ endpoints" — undercounts the route *files*, though a route file can expose several endpoints, so this isn't necessarily a discrepancy), all mounted under `/api/v1` except `/health`.
- **Engines**: 25 files (README lists 15 "core" ones by name — the other 10 are presumably support/util modules not itemized). Two routers (`ai_analysis`, `intelligence`) both surface AI status by different paths — see §2.1.
- **Frontend**: React 18 + TypeScript + Vite, React Query v5, Zustand-like store, 18 lazy-loaded pages, single `api.ts` service file (~90+ typed functions per README).
- **Database**: SQLite (WAL mode), versioned `init_db_vN()` migrations, optional SQLCipher encryption, composite indexes added in Phase 1 (A6). No Postgres/Redis — explicitly deferred to the SaaS-gated track, which is the right call for the stated single-user-local scope (avoids premature multi-tenant complexity, consistent with the guidance in this environment's CLAUDE.md about IaC/well-architected principles for infra that doesn't exist yet — there is no cloud infra here to over-build).
- **Desktop**: Tauri v1 (Rust) shell, primary target; PySide6 shell marked "legacy" in the README's own architecture diagram. Tauri v2 migration (C2 in 1.3) is a deliberately deferred, well-justified decision (v1-specific bundler quirks caused most of the 1.3 CI debugging).
- **AI**: NVIDIA NIM (OpenAI-compatible) as primary, Ollama as offline/local fallback, rule-based as final fallback. Three-tier degradation is a sound design for a product that needs to keep functioning without a network or paid API key.

**Architecture verdict**: coherent, appropriately scoped for a single-user local product, no obvious over-engineering (no premature Postgres/Redis/multi-tenant scaffolding actually running). The one structural wart is the two-routers-one-concept AI status split (§2.1) — cosmetic today, a genuine trap for a future contributor.

---

## 4. Known Revival Gaps — Current Status (re-verified where possible)

| Gap (from SESSIONGUARDREVIVAL1.3/1.4) | Status per docs | This audit's verification |
|---|---|---|
| Broken CI (1.3 findings #1–#11) | ✅ Fixed 2026-07-23 | Not re-run this session; workflow YAML read and looks structurally correct (§2.1) |
| Desktop installer ran stale backend (1.3 finding #13) | ✅ Fixed — bundles backend source via `stage-backend.js` | ✅ File existence confirmed this session |
| AI-insights router unmounted (1.3 finding #14) | ✅ Fixed | ✅ Confirmed via direct `main.py` read this session |
| `intelligence.py` doubled path segment (1.3 task A5) | ✅ Fixed | ✅ Confirmed via direct route/mount read this session |
| Async DB migration (1.3 track C1) | Was "not started" in 1.3, then partially addressed, then per 2026-07-25 audit: HTTP calls made properly async (`httpx.AsyncClient`), 27 routes converted `def`→`async def` for `require_admin` correctness, but **engine layer (6 files) is still fundamentally sync `sqlite3`**, wrapped in `asyncio.to_thread()` | Confirmed still-open per `DEFERRED_WORK.md`'s own 2026-07-25 entry; did not re-audit the engine files line-by-line this session. This is honestly tracked, not a new finding. |
| Full runtime bundling (1.4: Python/Tesseract/FFmpeg) | "Not started (deliberately deferred)" | ✅ Confirmed via `desktop_shell/bundle/` containing only `README.md` — genuinely zero binaries staged, matches the doc's own claim exactly. This is the most honestly-labeled "not done" item in the whole project — no discrepancy found. |
| Live NVIDIA NIM verification with a real key (1.3 track B3) | Deferred — mocked contract tests only, no live-key call made | Still true; this audit did not have API-key access or approval to make one either (would need REPO_RULES R24 approval for paid API spend, correctly gated) |
| DB backup/restore UI (C5 second half) | Deferred — dedup middleware done, UI not started | Not independently re-checked this session, no new evidence either way |
| `test_check_repo_drift` flakiness | Open, documented | Not re-run; description accepted as accurate (§2.3) |

**New observation not previously logged**: the gap-fix branch (`fix/revival13-gap-fixes`) that closes several of the above items is **itself unmerged to `main`** and has been sitting for 2.5 weeks. Every "✅ Fixed" row above is only true on this branch, not on `main`. If any release/packaging process points at `main`, none of these fixes are present there. This is worth its own line in the project's risk register.

---

## 5. Desktop Runtime Bundling Status

Directly inspected `desktop_shell/`:

```
desktop_shell/
├── bundle/            → README.md only, no binaries (1.4 not started, confirmed)
├── portable/           → present (E8, portable mode — Phase 5, claimed done)
├── sentry/              → present (E7, crash reporting — Phase 5, claimed done)
├── signing/             → present (E9, code-signing config — Phase 5, claimed done, cert-dependent)
├── src-tauri/           → Rust shell source
├── stage-backend.js     → backend source staging script (1.3 finding #13 fix)
└── package.json / package-lock.json
```

This matches the documentation's own claims exactly — no discrepancy found between "what the docs say is bundled" and "what files actually exist" for the desktop shell. The one gap (full runtime bundling) is the one thing the docs already say is not done, and it is in fact not done. This is a case where the project's self-reporting is accurate, worth noting positively rather than just cataloguing gaps.

**Practical consequence**: the desktop app today requires a system Python, Tesseract, and FFmpeg already installed to function fully (OCR/video features will fail or degrade without them — `README.md`'s own dependency table marks these "✅ Required" for their respective features). This is a real distribution blocker for any non-technical end user, correctly scoped as its own large sprint (1.4) rather than something to rush.

---

## 6. UX / Feature Completeness

Cross-referencing `README.md`'s own Feature Completeness table (§"Feature Completeness", lines 155–191) — this table is self-reported by the project but is unusually candid (it already marks several rows `⚠️`/`❌` against itself), so I'm treating it as reliable and summarizing its implications rather than re-deriving it from scratch:

**Backend capability with no frontend surface (user cannot reach it through the app at all)**:
- Alert Explanations (LLM root cause) — backend ✅, frontend ❌
- AI Cost Tracking + Budget — backend ✅, frontend ❌
- Prompt Versioning + A/B — backend ✅, frontend ❌
- Evidence Package (hash manifest + AI) — backend ✅, frontend ❌
- Clustering (HDBSCAN/cosine) — backend ✅, frontend ❌
- Dataset Quality Report — backend ✅, frontend ❌
- Projects/Teams — backend ✅, frontend ❌, desktop ❌

That's **7 of the product's more advanced/differentiating features** (the AI-native and compliance-oriented ones — evidence packages, dataset quality, cost tracking — are arguably the product's actual value proposition beyond "OCR a slot session") that exist only as curl-able API endpoints. For a solo-operator single-user tool this may be an acceptable interim state (the user could hit these via `/docs` Swagger UI), but it's worth naming plainly: **the AI Narrative row itself is `⚠️` end-to-end** (README's own footnote: never exercised against a real NVIDIA key), meaning the flagship "AI intelligence" pitch in the README's opening paragraph is unverified in practice, not just under-UI'd.

**Also incomplete**:
- Live Monitor (screen mode) — backend ✅, frontend/desktop ⚠️, tests ❌, docs ⚠️. This is the "watch my screen live" feature, arguably central to a "session guard" product, and it's the least-tested, least-documented row in the whole table.
- Admin Panel — desktop ❌ (web-only)
- Auto-updater — frontend ❌, desktop ⚠️

**UX verdict**: the CRUD/analysis core (sessions, uploads, OCR, behavior analysis, exports, compare) is genuinely complete across all four columns (backend/frontend/desktop/tests). The AI/compliance layer — the part of the product that differentiates it from "a spreadsheet with OCR" — is backend-complete but largely invisible to the actual user. This is the most actionable, currently-under-tracked gap this audit surfaces: none of the 1.3/1.4 docs currently have a task board item that says "build frontend for the 7 backend-only features."

---

## 7. Documentation Accuracy

The documentation is unusually self-correcting for a solo project (three successive docs literally titled "gap fix," "proper fix," "trust and verification sprint" — a project actively fighting its own tendency to over-claim). Specific accuracy notes from this session:

- `SessionGuardRevival.md`'s "Definition of Revival Complete" section is written in the correct hedged voice (all items marked ⏳ with honest caveats) — good practice, no correction needed.
- `README.md`'s Feature Completeness table is internally consistent with what this audit could verify (§5, §6) — no false claims found.
- **One gap**: none of the top-level docs (`README.md`, `SessionGuardRevival.md`, `SESSIONGUARDREVIVAL1.3.md`) currently mention that `fix/revival13-gap-fixes` is unmerged and 7 commits ahead of `main`. A reader who clones `main` today (rather than checking out this branch) would not know they're missing the async-auth-correctness and SQLite-lock fixes. This should be called out explicitly in `SessionGuardRevival.md`'s "Repository state" section, which already has a standing instruction to "verify, don't trust" prior claims about repo sync state — this is exactly the class of drift that section exists to prevent, just at the branch level instead of the two-clone level it was originally written about.
- Per Rule R31 (doc-freshness CI gate), an audit newer than 30 days must exist under `audits/`. The most recent prior to this one was 2026-07-25 (17 days old) — gate would currently pass; this new audit resets that clock.

---

## 8. Security

Scope note: this is a full-spectrum audit, not a dedicated security review — this section covers what was visible during general code/doc inspection, not an exhaustive pentest-style pass. If a deeper security review is wanted, `security-review` is the dedicated skill for that.

**Improvements confirmed present** (via docs, cross-checked against file existence where feasible this session):
- Rate limiting wired to auth/upload endpoints (A3)
- Structured JSON request logging with request IDs (A4)
- Secret key sourced from env, not committed config; rotation support (A5)
- Upload validation: size cap, MIME check, optional ClamAV scan (A8)
- Optional SQLCipher DB encryption (E5)
- No secrets found committed in this session's spot checks (config file reads did not surface any embedded API keys) — consistent with P0.1's fix

**Open items worth flagging**:
1. **`docs/governance/DEFERRED_WORK.md` already records an open, unresolved secret-scan review** (2026-07-24 entry): the automated secret scanner flags `backend/auth/service.py`, `backend/routes/alerts.py`, `backend/routes/auth.py`, `backend/routes/openapi_export.py`, `database/db.py`, `engines/ai_insights_engine.py`, `frontend/src/services/api.ts`, `tests/test_auth.py` — and nobody has yet determined whether these are true positives or expected false-positives (e.g., variable names containing "key"/"secret"/"token" that aren't actual secrets). This is a **CI-gate correctness question sitting open for 2.5+ weeks** — if any of these are true positives, that's a live secret-exposure incident; if they're all false positives, the scan rules need tuning so real findings aren't buried in noise. Given this repo's history (P0.1 was exactly this failure mode — a real API key committed to `config/app_config.json`), this should not stay open indefinitely.
2. **No auth enforcement on most routes** (P0.6, explicitly deferred, confirmed direction: "single-user-local-only"). This is a reasonable scope decision *as long as the app never binds to a non-loopback interface*. I did not find explicit confirmation in this session that the backend binds only to `127.0.0.1`/`localhost` rather than `0.0.0.0` — worth a one-line grep-and-confirm (`uvicorn.run(..., host=...)` in `backend/main.py` or its entrypoint) before treating "no auth needed" as safe, since a `0.0.0.0` bind on a shared network would expose every unauthenticated route to the LAN. Flagging as **unverified, not confirmed-broken** — a quick, cheap check to close out.
3. **SIGHUP-based secret rotation is a no-op on Windows** (documented, A5) — acceptable given this is explicitly a Windows-first desktop product, but means "rotate the signing secret" on Windows requires a full process restart with a new env var, which is a real operational step someone has to remember, not an automatic mitigation.

---

## 9. Notable Positive Findings

Worth stating plainly, since an audit that only lists problems understates what's actually working:

- The project's *process* for catching its own over-claiming is genuinely good — the 1.2→1.3→1.4 document lineage, the `DEFERRED_WORK.md` register, and `REPO_RULES.md`'s explicit "truth over velocity" principle are unusual rigor for a solo project, and this audit found the self-reported state to be accurate everywhere it could be statically checked.
- The AI degradation chain (NVIDIA NIM → Ollama → rule-based) is a sound design that avoids a hard dependency on a paid API for core functionality.
- The three-tier "not done, partially done, done" honesty in `SESSIONGUARDREVIVAL1.4.md` specifically (a whole document that says "we haven't started this, here's exactly what done means, don't mark it done until a clean-VM test passes") is a good template other parts of the project could be held to.

---

## 10. Consolidated Findings (severity-ordered)

| # | Finding | Severity | Area |
|---|---|---|---|
| 1 | `fix/revival13-gap-fixes` (7 commits of correctness fixes) unmerged to `main` for 2.5 weeks; no observed GitHub Actions run for this branch | High | CI/Release process |
| 2 | Open secret-scan false-positive/true-positive review, unresolved 2.5+ weeks, on files including actual auth/secret-handling code | High | Security |
| 3 | 7 backend-complete features have zero frontend surface (AI cost, prompt versioning, evidence package, clustering, dataset quality, alert explanations, projects/teams) — including the product's stated AI-differentiation features | Medium | UX completeness |
| 4 | AI Narrative feature (flagship pitch in README's first paragraph) still never verified against a real NVIDIA API key end-to-end | Medium | Product risk / docs accuracy |
| 5 | Engine layer (6 files) still fundamentally sync SQLite under `asyncio.to_thread()` wrapping, not natively async — known, tracked, but real | Medium | Backend architecture |
| 6 | Runtime bundling (Python/Tesseract/FFmpeg) not started — desktop app not usable on a clean machine without pre-installed dependencies | Medium | Desktop distribution (already correctly tracked in 1.4) |
| 7 | `test_check_repo_drift` flaky ~40% of the time on the one test that's supposed to catch canonical-repo drift | Low-Medium | Test reliability |
| 8 | Two different backend routers (`ai_analysis`, `intelligence`) both expose AI-status-shaped endpoints under similar-looking paths — no bug today, but a naming trap | Low | Code clarity |
| 9 | Backend bind-host (loopback vs. all-interfaces) not confirmed this session given the "no auth needed" security posture depends on it | Low (pending verification) | Security |
| 10 | No doc currently states the branch/main divergence explicitly | Low | Docs accuracy |

---

*This document lives at `audits/2026-08-11_ClaudeCode_FullSpectrum_Audit.md`. Per this repo's own Rule 5, future audits should read this one and call out where these findings are still true, fixed, or superseded.*

---

# PART 2 — 100000/100000 Completion Plan

**Reading key**: this plan is phased by leverage (fix trust/verification gaps before adding surface area, per this project's own established doctrine), not by calendar week. Effort estimates are rough solo-developer sizing (S = <1 day, M = 1–3 days, L = 3–7 days, XL = 1–3 weeks), consistent with this being a one-person effort per `SessionGuardRevival.md`'s own "Team reality" section.

## Phase A — Close the trust gap this audit found (do first, before anything else)

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| A1 | Merge `fix/revival13-gap-fixes` → `main` (via PR, per branch-only workflow in `AGENTS.md`) and observe a real GitHub Actions run go green on all jobs (`gate.yml`, `test.yml`, `build.yml`, `bundled-backend-smoke.yml`) | PR merged; CI check marks visible and green on the merge commit in GitHub's UI, not just claimed locally | S (mechanical) + wait time for CI |
| A2 | Resolve the secret-scan review (`DEFERRED_WORK.md` 2026-07-24 item) — classify each of the 8 flagged files as true/false positive; fix true positives, add scoped exclusions with a documented reason for false positives | Secret-scan step in `gate.yml`/`scripts/verify.sh` passes with zero unexplained flags; each exclusion has an inline comment or `docs/governance/` note stating why | M |
| A3 | Fix `test_check_repo_drift` flakiness (git repo setup race in parallel temp dirs) — use unique temp dirs per test or serialize repo-creation tests | 10 consecutive full-suite runs, 0 failures on this test | S |
| A4 | Confirm backend bind host (loopback-only vs. all-interfaces) explicitly; if not already loopback-only, make it so, or document the exposure and gate it behind an explicit opt-in flag | `uvicorn.run` (or equivalent) call site inspected and documented; default behavior confirmed loopback-only unless a `--network` flag (or similar) is explicitly passed | S |
| A5 | Add a doc line in `SessionGuardRevival.md`'s "Repository state" section flagging branch/main divergence as a recurring risk class (same shape as the two-clone drift that caused finding #13) — consider extending `repo-drift-check.yml` to also alert on long-lived unmerged branches, not just clone drift | Doc updated; optionally, CI warns (not necessarily fails) if a non-`main` branch is >N days old with commits `main` doesn't have | S (doc) / M (if CI extension included) |

**Phase A Definition of Done**: `main` contains everything currently on `fix/revival13-gap-fixes`, verified green on GitHub's own runners; the secret-scan and flaky-test items are closed, not just documented as open.

---

## Phase B — Finish what's already scoped and tracked (SESSIONGUARDREVIVAL1.3 Track C1, B-track coverage)

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| B1 | Convert the 6 sync engine files to natively async (`aiosqlite` or equivalent), remove the `asyncio.to_thread()` wrapping now that it's no longer needed | All engine DB calls use an async driver; `asyncio.to_thread()` wrapper calls for DB I/O removed from routes; full test suite still green | L |
| B2 | Live-verify AI streaming against a real NVIDIA NIM endpoint with an approved API key (REPO_RULES R24 approval required first) | One real call recorded, `source == "nvidia_ai"` confirmed, tokens logged in `ai_cost_log`, regression test added asserting the contract (can stay mocked after this one live check) | S (once key approved) |
| B3 | DB backup/restore UI (second half of C5) — `GET /api/v1/admin/backup` (SQLite `VACUUM INTO`) + Settings panel with download/restore + confirm-restore modal | Backup downloadable from UI; restore round-trips a real DB; destructive restore requires explicit confirmation | M |
| B4 | Rename or clearly disambiguate the two AI-status-shaped routes (`ai_analysis`'s `/ai/status` vs `intelligence`'s `/ai/status`) so a future grep doesn't pick the wrong one | Route names/paths or code comments make the distinction unambiguous; no functional change required, just clarity | S |

---

## Phase C — UX completeness: give the AI/compliance layer a frontend

This directly addresses finding #3/#4 above — the product's stated differentiators are currently backend-only.

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| C1 | Alert Explanations UI — surface `GET /alerts/{id}/explain` in the Alerts page | Clicking an alert shows the LLM root-cause explanation with evidence citations, per D5's original spec | M |
| C2 | AI Cost Tracking + Budget UI — surface `GET /api/v1/ai-cost/usage` | Settings or Dashboard shows $/session, running total, budget threshold, and fallback status when exceeded | M |
| C3 | Prompt Versioning + A/B UI — surface `GET/POST /api/v1/prompts` | Admin-gated panel lists prompt versions, lets an operator activate a version or trigger an A/B comparison | M |
| C4 | Evidence Package UI — surface `POST /sessions/{id}/evidence` + `GET .../evidence/verify` | Session detail page has an "Export Evidence Package" button; downloads ZIP; verify endpoint checked and shown as a badge (valid/invalid) | M |
| C5 | Clustering UI — surface `GET /intelligence/clusters` | A page or panel showing session cohorts/clusters with basic visualization (even a simple table grouped by cluster ID is sufficient for v1) | M |
| C6 | Dataset Quality UI — surface `GET /intelligence/dataset-quality` | Admin panel shows completeness/bias/distribution metrics as a readable report, exportable | M |
| C7 | Projects/Teams frontend + desktop | Basic CRUD UI for the already-existing backend `Projects` API; desktop parity | L |

**Phase C Definition of Done**: README's Feature Completeness table has zero `❌` in the Frontend column for any row where Backend is `✅`, or an explicit, justified exception is documented (e.g., "admin-only, reachable via `/docs` by design").

---

## Phase D — Desktop runtime bundling (SESSIONGUARDREVIVAL1.4, already fully scoped — execute as written)

This phase's task board already exists in full detail in `SESSIONGUARDREVIVAL1.4.md` (P1–P4 Python, T1–T3 Tesseract, F1–F3 FFmpeg, X1–X4 cross-cutting). This plan does not re-derive it — it references it and sequences it here for completeness:

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| D1 | Execute `SESSIONGUARDREVIVAL1.4.md` P1–P4 (Windows embeddable Python, scripted + checksum-pinned, `find_python()` updated) | `pip install -t python/Lib/site-packages -r requirements.txt` runs in CI; `find_python()` finds the bundled interpreter first | L |
| D2 | Execute 1.4's P3 for macOS/Linux (python-build-standalone or bundled venv decision, documented) | Same acceptance bar as D1, cross-platform | XL |
| D3 | Execute 1.4's T1–T3 (Tesseract bundling + licensing check + accuracy re-verification against the bundled binary) | `tests/test_ocr_benchmark.py` passes against the bundled binary specifically, not system install | L |
| D4 | Execute 1.4's F1–F3 (FFmpeg bundling + licensing check + chunking/resume re-verification) | Video chunking/resume tests pass against bundled FFmpeg | L |
| D5 | Execute 1.4's X1 — provision genuinely clean Windows/macOS/Linux VMs, run the acceptance test manually | OCR on a sample screenshot succeeds, session create/view works, `sessionguard --version` works offline, on all three, with nothing pre-installed. **Do not mark this phase complete without this step, per 1.4's own explicit warning.** | M (execution) + VM provisioning time |
| D6 | Execute 1.4's X2–X4 (wire into CI, update installer-size expectations, decide update-story for large bundled runtimes) | CI verifies the bundle on every tagged release; docs updated with real installer sizes; update mechanism decided and documented | M |

---

## Phase E — Ongoing hygiene (lower urgency, no new information changes their priority — carried from 1.3 Track C/D)

| ID | Task | Acceptance Criteria | Effort |
|---|---|---|---|
| E1 | Frontend state consolidation (Zustand + React Query + URL params → one source of truth) | No component reads the same logical state from two different stores | L |
| E2 | Virtualized lists, LiveMonitor WebSocket (replace polling), keyboard nav/ARIA | Long session lists don't degrade performance; LiveMonitor updates push instead of poll; basic keyboard navigation works across primary flows | M each |
| E3 | Health/diagnostics page inside the desktop app UI itself (not just an API endpoint) — 1.3's D2 | A user can open an in-app panel and see "running version X, backend reachable, DB path Y" without opening a terminal or curling `/health` | M |
| E4 | Audit remaining background-failure paths for silent `print()`-into-the-void pattern beyond the AI layer (1.3's D1 was AI-layer-only) | Every background job/worker failure surfaces via structured log at minimum, ideally a user-visible signal for user-triggered actions | M |
| E5 | Live Monitor (screen mode) — bring frontend/desktop from ⚠️ to ✅, add tests, fix docs | README's own Feature Completeness table row goes from mixed ⚠️/❌ to consistent ✅ across backend/frontend/desktop/tests | L |

---

## Summary effort roll-up

| Phase | Total rough effort | Gate before proceeding to next |
|---|---|---|
| A — Trust gap | ~1 week | `main` green on real CI, secret-scan resolved |
| B — Scoped finish-up | ~1–2 weeks | Async engine conversion done, live AI verified once |
| C — UX completeness | ~2–3 weeks | Feature table has no unjustified backend-only rows |
| D — Runtime bundling | ~4–6 weeks (the acknowledged big one) | Clean-VM acceptance test passes on all 3 OSes |
| E — Hygiene | ~2 weeks, can interleave | No hard gate — do opportunistically |

Total, solo, sequential: roughly **10–14 weeks** of focused work to reach the state `SessionGuardRevival.md`'s own "Definition of Revival Complete" describes for the local-first desktop track (items 1, 3, 4, 5 in that section) — excluding Phase 6/SaaS, which remains correctly business-gated and out of scope for this plan.

---

*Plan generated by Claude Code (Sonnet 5), 2026-08-11. Per Rule 4 (no silent step-skipping): PHASE 1 (audit) and PHASE 2 (plan) above are both complete; no destructive actions, commits, or pushes were performed as part of producing this document, per the task's explicit instruction.*
