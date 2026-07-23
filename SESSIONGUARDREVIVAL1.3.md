# SessionGuard Revival 1.3 — Trust & Verification Sprint

**Created**: 2026-07-23 · **Status**: Active · **Parent doc**: [`SessionGuardRevival.md`](SessionGuardRevival.md)
**Previous sprint doc**: [`SESSIONGUARDREVIVAL1.2.md`](SESSIONGUARDREVIVAL1.2.md) — superseded by this document, kept for history
**Next / related doc**: [`SESSIONGUARDREVIVAL1.4.md`](SESSIONGUARDREVIVAL1.4.md) — dedicated sprint for full embeddable-runtime bundling (Python + Tesseract + FFmpeg), deliberately split out of this one

**If you're picking up this repo for the first time**: read `AGENTS.md` first, then `SessionGuardRevival.md`, then this document. This is the active plan as of 2026-07-23.

---

## Why this document exists

On 2026-07-23, a routine "audit this repo" request turned into a multi-hour session that found the project's CI pipeline had been failing on every single push, and — more seriously — that the desktop installer, when actually run, silently executed six-phases-stale backend code instead of the code it was built from. Neither of these had been caught by anything in the existing test suite or roadmap docs, because nothing had ever actually run the packaged app or watched CI go green.

**The theme connecting every fix in this session: things were marked "✅ Done" based on the code existing and compiling, not on anyone actually running it.** That's the problem this sprint targets directly — not a new feature, a change in how "done" gets verified.

---

## What this session found and fixed (2026-07-23)

Read this section before assuming anything below it still needs doing — it's the reason this document exists.

| # | Finding | Fix | Verified how |
|---|---------|-----|---------------|
| 1 | `build.yml` had an invalid GitHub Actions expression (`trimPrefix(...)`, not a real function) — the whole workflow failed to parse, instantly, on every push | Removed the dead `env:` block that used it | CI run stopped instant-failing after the fix |
| 2 | `build.yml` + `test.yml` both ran `pip install -e .` with no `pyproject.toml`/`setup.py` anywhere in the repo — every Python install step was broken | Switched to `pip install -r requirements.txt` | CI installs succeed |
| 3 | Pinned `pytest-asyncio==0.23.0` crashes on collection (`AttributeError: 'Package' object has no attribute 'obj'`) on a clean install — never caught locally because the dev venv had silently drifted to 0.21.0 | Bumped to `0.23.8` | 134 passed, 6 skipped, reproduced against the *exact* pinned version |
| 4 | `Cargo.toml` pinned `sentry-tauri = "0.7"`, a version that doesn't exist on crates.io (max published: 0.3.1) — desktop build could never resolve dependencies | Removed the phantom dep; added the real `sentry` crate the code actually imports (`use sentry::{init, ...}`), which had never been declared at all | CI Rust build compiles |
| 5 | `global-shortcut-all` Tauri feature kept vanishing from `Cargo.toml` — root cause: `tauri.conf.json`'s allowlist had no `globalShortcut` entry, so the Tauri CLI's feature auto-sync silently stripped it every build | Added the allowlist entry | Feature persists across rebuilds |
| 6 | macOS build: `macos-latest` runners are Apple Silicon by default (only `aarch64-apple-darwin` installed), but the workflow hardcoded `--target x86_64-apple-darwin` | Added `rustup target add x86_64-apple-darwin` | macOS job green |
| 7 | macOS build: bundler tried to codesign with a **blank identity** because GitHub Actions sets `APPLE_SIGNING_IDENTITY` to an empty string (not omitted) when the secret doesn't exist, and tauri-bundler treats mere *presence* of that env var as "sign now" | Split into signed/unsigned `tauri-action` steps gated on a job-level env check (`secrets` can't be used directly in `if:` — see #9) | macOS job produces a `.dmg` |
| 8 | Linux build: installed `libwebkit2gtk-4.1-dev` (pulls in libsoup3), but Tauri v1 needs libsoup 2.4 | Switched to `libwebkit2gtk-4.0-dev` | Linux job produces AppImage/deb/rpm |
| 9 | GitHub Actions doesn't allow the `secrets` context inside `if:` conditionals at all — using it isn't a runtime failure, it's a workflow-file validation error, so **the whole workflow failed to parse again** | Routed the check through a job-level `env` var instead | Workflow parses and runs |
| 10 | Windows build actually succeeded (`.msi` + NSIS `.exe`) but failed at release creation — default `GITHUB_TOKEN` is read-only on this repo | Added explicit `permissions: contents: write` | Draft release created with all assets |
| 11 | `build.yml` ran its full build+release flow on **every push to `main`**, not just version tags — every commit would draft (or clobber) a release | Removed the `branches: [main]` push trigger; `tags: ['v*']` only | No more spurious drafts |
| 12 | Version drift: `desktop_shell/package.json`, `Cargo.toml`, `tauri.conf.json` were all still `1.0.0` while `README.md`/`config/app_config.json` claimed `1.5.0` | Synced all to a single version, bumped through this session as `1.5.1` → `1.5.2` | — |
| 13 | **The installed app silently ran the wrong code.** `find_project_root()` had no way to locate backend source unless bundled (it never was — "bundle deps" was marked done in Phase 4 but never completed), so it fell back to a hardcoded path, `C:\Projects\SessionGuard\sessionguard`, that happened to exist on the original dev machine as a stale, six-phases-old checkout (reported API version `0.6.0`, missing Phases 3–5 and the entire NVIDIA migration) | Actually bundles `backend/engines/database/config` into the installer via a build-time staging script (`desktop_shell/stage-backend.js`) + Tauri `resources`; resolves it via Tauri's own platform-correct `path_resolver`; removed the hardcoded fallback entirely — fails loudly (visible in-window alert + `sessionguard.log`) instead of silently guessing | Reinstalled clean, confirmed `sessionguard.log` shows `Starting backend from: ...\bundled_app`, confirmed via a route that only exists in current code (see #14) |
| 14 | **`backend/routes/ai_analysis.py` — the entire AI insights/streaming/model-selector feature — was never imported or mounted in `main.py`.** Every endpoint the "NVIDIA NIM Migration" built (`/ai/models`, `/ai/model`, `/sessions/{id}/ai`, `/sessions/{id}/ai/stream`) 404'd. The frontend's model-selector dropdown could never have worked against a real deployment | Added the import and `app.include_router(ai_analysis.router, prefix="/api/v1")` | Live curl against a running instance returns the real NVIDIA model list; full test suite still green |
| 15 | Personal, machine-specific hardcoded path (`C:\Users\Shaya\...`) in `find_python()` | Removed; falls back cleanly to bundled-Python-if-present, else system `python` on PATH | — |

**Not yet fixed, found in passing, worth reading before you touch these areas:**

- `intelligence.py`'s routes appear to double their own path segment under the outer mount prefix (`/api/v1/intelligence/intelligence/ai/status`) — likely why the frontend's `getAiStatus()` (which calls `/intelligence/ai/status`) doesn't match either that route or the newly-mounted `ai_analysis` one. Needs its own investigation; not fixed in this session (found very late, scoping it properly needs more than the few minutes left).
- Every `/ai/status`-adjacent call incurs several seconds of latency from a synchronous, uncached Ollama-reachability check (`urllib.request.urlopen(..., timeout=3)`) on every request. Not wrong, just slow — a real UX cost if a user has Ollama unreachable (the common case if it isn't installed).
- Backend has at least three independent hardcoded version strings that don't agree with each other or with `config/app_config.json`: `backend/main.py`'s FastAPI app (`"1.2.0"`), `backend/routes/health.py` (`"0.6.0"`, in two places). None of them are read from a single source of truth.

---

## Task Board

### Track A — Close the "done but never run" gap (do this first)

This is the direct lesson of the session above. Every task here exists because something was claimed complete and wasn't verified end-to-end, and the fix is to make that failure mode structurally harder to repeat, not just to patch the specific instance found this time.

| ID | Task | Why | Impact | Status |
|----|------|-----|--------|--------|
| A1 | Add a CI job that installs the built app (or at minimum runs the bundled backend) and hits `/health`, failing the build if it doesn't respond in time | CI currently proves the app *compiles and bundles*. It has never once proven the app *runs*. That gap is exactly what let the stale-backend bug (finding #13) ship silently for who knows how long | Turns "build succeeded" from a weak signal into a real one — the single highest-leverage test in the whole pipeline | ⏳ Not started |
| A2 | Test the bundled resource path across all four packaging formats (MSI, NSIS, DMG, AppImage/deb/rpm) — I only observed the NSIS layout directly | `resolve_resource()` is documented as platform-correct, but four different bundlers have four different resource-layout conventions, and this project has been burned by packaging-format-specific quirks three separate times in one session (Linux libsoup, macOS codesign, Windows release perms) | Catches a platform-specific resource bug before a user does | ⏳ Not started |
| A3 | Canonical-repo drift alarm: a scheduled check (or pre-push hook) diffing `_repo_clone`/origin against `C:\Projects\SessionGuard\sessionguard`, failing loudly if they've diverged | `SessionGuardRevival.md` asserted the two trees were "merged and in sync" as of 2026-07-21. They were **six phases apart** by 2026-07-23. The project's own Risk Register predicted this exact failure mode ("Divergent local copies drift again... High likelihood") — it happened anyway because nothing automated the check | This is the actual mechanism that produced finding #13. An automated check turns a predicted risk into a caught one | ⏳ Not started |
| A4 | Grep the whole repo for other instances of the hardcoded-dev-machine-path pattern | Found and fixed it in `main.rs`; `init_db.py` had a near-identical bug fixed back in Phase 1 (hardcoded `sys.path`). Two independent instances of the same mistake suggests there may be a third | Cheap, mechanical, closes off a whole *class* of "works on my machine" bugs rather than one instance | ⏳ Not started |
| A5 | Fix the `intelligence.py` doubled-path-segment bug and reconcile `getAiStatus()`'s frontend call with whatever the correct backend route turns out to be | Found in passing while verifying A-track fixes; directly adjacent to finding #14 and likely has the same "looks wired, isn't" shape | Restores whatever `getAiStatus()` was supposed to show in the AI panel — currently returns 404 silently | ⏳ Not started |

### Track B — Test the code that actually matters, prioritized by consequence, not by convenience

| ID | Task | Why | Impact | Status |
|----|------|-----|--------|--------|
| B1 | `video_pipeline.py` — raise coverage off 10% | 374 lines, the one engine every downstream feature (alerts, insights, evidence packages, review queue) depends on. A silent regression here corrupts everything built on top before anyone notices | Highest blast-radius-to-coverage ratio in the repo | ⏳ Not started |
| B2 | `export_service.py` + evidence-package builder — real tests, not just structural | 685 lines at 3%. This produces the "court/regulatory-ready" evidence ZIP — the one feature where being *wrong* has consequences beyond an annoyed user | If this product is ever used for its stated regulatory purpose, an untested export path is a liability | ⏳ Not started |
| B3 | Verify AI streaming against a **real** NVIDIA NIM endpoint, once, with a real API key, and add regression coverage | Flagged since Sprint 2 as never tested against a live API; now doubly relevant since the whole router wasn't even mounted (finding #14) — everything about this feature needs re-verification from zero, not just the streaming part | Either confirms a real feature works end-to-end, or catches that it doesn't before a user hits "Analyze" | ⏳ Not started |
| B4 | `roi_calibrator.py` — first tests, period | 0% coverage; it's the entry point for onboarding any *new* slot game, meaning it's exposed to the most unpredictable input (arbitrary uploaded screenshots) with the least safety net | New-game onboarding is presumably how this product grows past the games it already supports | ⏳ Not started |
| B5 | Reconcile the three disagreeing hardcoded version strings (`main.py`, `health.py` ×2) against `config/app_config.json`, ideally reading from one source of truth | Small, but "what version is actually running" was a real question I had to answer forensically today (checking `/health`, checking file hashes, checking git log) instead of just reading a number | Makes "which version is this" trustworthy instead of requiring detective work | ⏳ Not started |

### Track C — Finish what Phase 5 / Sprint 1–2 started but didn't land

Carried forward from `SESSIONGUARDREVIVAL1.2.md`; re-justified rather than copy-pasted, since the informing context (a repo that fixes things partially and calls them done) has changed how urgently these matter.

| ID | Task | Why | Impact | Status |
|----|------|-----|--------|--------|
| C1 | Finish the async DB migration — 7 routes in `alerts.py`/`insights.py` still `def`, all engine functions still fundamentally sync underneath `asyncio.to_thread()` wrapping | Already documented as partial in 1.2's "Honest Task Audit"; worth doing early specifically *because* it's small, contained, and well-scoped — a good low-risk task to rebuild confidence in the status board with | Closes a known, already-scoped gap | ⏳ Not started |
| C2 | Tauri v2 migration (deferred since Phase 3 as E1) | Every CI/build bug found this session was a Tauri v1 quirk (silent Cargo feature stripping, bundler codesign behavior, resource layout differences) — not code bugs, tooling-fragility bugs. v2's tooling is materially more mature and the installer is ~10× smaller | Reduces future CI-fragility, not just installer size — most of this session's multi-hour debugging was fighting v1-specific bundler behavior | ⏳ Not started |
| C3 | Frontend state consolidation (Zustand + React Query + URL params → one source of truth) | Pre-existing (F5 in 1.2), unrelated to this session's findings, still real and untouched | Lower urgency than Tracks A/B; shovel-ready whenever picked up | ⏳ Not started |
| C4 | Virtualized lists (F1), LiveMonitor WebSocket (F2), keyboard nav/ARIA (F4) | Pre-existing, well-scoped, no new information changes their priority | Sequence after Tracks A/B, not before | ⏳ Not started |
| C5 | Request-dedup middleware (B5 in 1.2), DB backup/restore UI (D2 in 1.2) | Pre-existing, unaffected by this session | Same as above | ⏳ Not started |

### Track D — Make failures visible everywhere, not just in the desktop shell

Generalizes the fix already made to `main.rs` (silent failure → visible alert + log file) to the rest of the system.

| ID | Task | Why | Impact | Status |
|----|------|-----|--------|--------|
| D1 | Audit the backend for the same "print()-into-the-void" pattern the desktop shell had | The desktop shell hid all diagnostics because it's a windowless subsystem build — now fixed. Does every *background* failure path (job worker retries, OCR fallback, offline-AI fallback) actually surface somewhere a user or operator would see it, or just log to a file nobody reads? `structlog` (A4, done) covers HTTP requests; worth checking whether it's uniform elsewhere rather than assuming | Cheap to audit; directly extends this session's biggest lesson: a failure nobody can see is worse than a crash | ⏳ Not started |
| D2 | Health/diagnostics page inside the desktop app itself, not just an API endpoint | D3 in 1.2 ("health monitoring dashboard") is already backlogged as a JSON endpoint. Given finding #13, I'd promote this and make sure it surfaces *inside the app UI*, not just via curl | Turns "is the app actually running the code I think it's running" from the forensic exercise I had to do this session into a five-second in-app check | ⏳ Not started |

---

## Explicitly out of scope for this document

- **Full embeddable-runtime bundling** (Python interpreter + Tesseract + FFmpeg, true zero-dependency portability) — this session's backend-bundling fix (#13) ships the *source*, not the *runtime*; the app still depends on a system Python being present. That's a meaningfully large, separate chunk of work (downloading, packaging, and testing three third-party runtimes across three OSes) and deserves its own dedicated sprint rather than being squeezed in here. See [`SESSIONGUARDREVIVAL1.4.md`](SESSIONGUARDREVIVAL1.4.md).
- **Phase 6 / SaaS / multi-tenant work** — already correctly gated behind a business decision that hasn't been made (see `SessionGuardRevival.md`). Not revisited here.

---

## Definition of Done for this sprint

- [ ] Track A (trust-rebuilding) complete — CI actually proves the app runs, not just builds
- [ ] `video_pipeline.py` and `export_service.py` off their current near-zero coverage
- [ ] AI streaming verified against a real NVIDIA NIM endpoint
- [ ] `intelligence.py` path bug fixed, `getAiStatus()` returns real data
- [ ] Async DB migration actually finished (not partially, per the 1.2 audit)
- [ ] This document's own status column updated as each task lands — don't let it go stale the way 1.2's did

---

*This document lives at `SESSIONGUARDREVIVAL1.3.md` in the repo root. Update status columns as tasks are completed. When this sprint closes, write the next one and update `SessionGuardRevival.md`'s pointer — don't leave this doc as the last word the way `SESSIONGUARDREVIVAL1.2.md` almost did.*
