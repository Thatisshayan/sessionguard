# SessionGuard Full-Spectrum Audit

Date: 2026-08-11
Auditor: Codex
Scope: Build/test/CI, architecture/code quality, revival-gap revalidation, desktop runtime bundling, UX/frontend completeness, docs accuracy, security, and production-local-desktop readiness planning.

## Executive Summary

SessionGuard is not production-local-desktop ready as of 2026-08-11. The codebase has a substantial amount of implemented functionality, and several of the 2026-07-23 revival findings are fixed in the working tree, but the verification story is still materially incomplete. The local required verify path is red, the required governance gate does not actually validate the frontend or desktop bundle, true zero-dependency desktop runtime bundling is still unstarted, several authenticated surfaces are inconsistently exposed without auth, the desktop staging area contains generated/runtime artifacts, and the docs still overstate or misstate current reality in multiple places. The fastest path to 100000/100000 is not more feature work first; it is truthful verification, packaging completion, auth/endpoint hardening, UX completion for already-built backend capabilities, and a clean release rehearsal on fresh VMs.

## Evidence Used

- Governance: `REPO_RULES.md`, `AGENTS.md`, `docs/governance/DEFERRED_WORK.md`
- Prior/project context: `SessionGuardRevival.md`, `SESSIONGUARDREVIVAL1.3.md`, `SESSIONGUARDREVIVAL1.4.md`, `10072026auditbytopencode.md`
- External project brief: `D:/AgentDevWork/repos/OBSIDIAN-TEAM-BOARDROOM/project-docs/SESSIONGUARD.md`
- Workflows/scripts: `.github/workflows/gate.yml`, `.github/workflows/build.yml`, `.github/workflows/test.yml`, `.github/workflows/bundled-backend-smoke.yml`, `scripts/verify.ps1`
- Core code: `backend/main.py`, `backend/routes/{ai_analysis,alerts,auth,health,intelligence,jobs,uploads}.py`, `backend/auth/{service,access}.py`, `database/db.py`, `desktop_shell/stage-backend.js`, `desktop_shell/src-tauri/{tauri.conf.json,src/main.rs}`, `frontend/src/{App.tsx,services/api.ts}`
- Local verification run:
  - Command: `pwsh scripts/verify.ps1`
  - Result: failed on 2026-08-11

## 1. Build, Test, And CI Actual Pass Status

### Current local status

`pwsh scripts/verify.ps1` is red today. It failed in four relevant ways:

1. `secret-scan` failed on heuristic matches in auth/API files.
2. `doc-freshness` failed because `markdown-link-check` is required but not installed locally.
3. `test` failed after dependency bootstrap fell back to an ambient Python environment and imported an incompatible FastAPI/Starlette stack, ending at:
   - `TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'`
4. `deploy-dry` was skipped legitimately because there is no deploy target.

### Important CI/gate truth gap

The repository states that the required merge gate is `gate` and that it covers `secret-scan`, `build`, `test`, `doc-freshness`, and `deploy-dry`. In practice, the required path does not validate the frontend or desktop build:

- `.github/workflows/gate.yml` runs only `bash scripts/verify.sh`.
- `scripts/verify.ps1` and the corresponding shell flow detect Node projects only from repo-root manifests.
- This repo’s actual frontend lives under `frontend/`, not repo root.
- Result: the required gate is Python-only in practice and can pass while React/Tauri regress.

### Additional CI observations

- `build.yml` and `test.yml` exist and are broader than `gate`, but they are not the required green path described by the repo rules.
- `bundled-backend-smoke.yml` is useful and aligned with the 2026-07-23 trust findings, but it validates bundled backend source startup, not full runtime bundling.
- I could not verify current remote GitHub run status from this sandbox, so the only confirmed actual pass/fail state is the local verify failure above.

### Assessment

- Local verify path: failing
- Required merge gate coverage: incomplete
- Frontend/desktop verification in the required gate: missing
- Remote CI green status: unverified from this environment

## 2. Architecture And Code Quality

### Architecture strengths

- The repo still has a workable local-first split between FastAPI backend, React frontend, SQLite storage, and Tauri shell.
- Business logic is mostly separated into `engines/`.
- Version-source unification is partly fixed through `backend/version.py` loading `config/app_config.json`.
- Bundled backend staging via `desktop_shell/stage-backend.js` is directionally correct and clearly better than the old hardcoded-machine-path behavior.

### Architecture and code-quality weaknesses

1. Verification architecture is weaker than product architecture.
   - The repo has more implemented features than proven features.
   - Required CI does not represent the real shipped surface.

2. Critical files remain large and multi-purpose.
   - Largest backend hotspots include `backend/services/export_service.py`, `engines/ai_insights_engine.py`, and `engines/video_pipeline.py`.
   - Largest frontend hotspots include `frontend/src/services/api.ts`, `frontend/src/pages/LiveMonitor.tsx`, `frontend/src/pages/Dashboard.tsx`, and `frontend/src/App.tsx`.

3. Startup/bootstrap remains monolithic.
   - `backend/main.py` still owns path setup, env loading, Tesseract pinning, middleware, auth gate behavior, DB migrations, demo seeding, and route registration in one place.

4. Schema and bootstrap remain over-centralized.
   - `database/db.py` still mixes connection policy, async wrappers, raw schema strings, migrations, and demo seeding in one file.

5. Generated/runtime artifacts are living too close to source.
   - `desktop_shell/src-tauri/bundled_app` currently contains staged code plus `__pycache__`, `config/sessionguard.db`, and `storage/` directories.
   - That is a drift hazard for packaging truth and reviewability.

6. Frontend shell quality is uneven.
   - `frontend/src/App.tsx` contains mojibake/corrupted glyphs in comments, labels, and version text.
   - The app shell is wired, but polish and correctness of presentation have slipped.

## 3. Revival Gap Revalidation

### Broken CI

Status: still materially unresolved at the governance level.

- The 2026-07-23 workflow syntax/build issues described in `SESSIONGUARDREVIVAL1.3.md` appear addressed in the separate workflow files.
- But the repo’s required `gate` path still does not prove frontend or desktop correctness.
- Local `verify.ps1` is still red today.

Conclusion: the specific July workflow breakages may be fixed, but the broader “CI tells the truth” problem is not closed.

### Installer shipping stale code

Status: the original stale-code fallback is fixed, but packaging truth is still incomplete.

- `desktop_shell/src-tauri/src/main.rs` now resolves bundled backend source via Tauri resources and no longer guesses a hardcoded dev-machine checkout.
- `desktop_shell/stage-backend.js` stages `backend/`, `engines/`, `database/`, and `config/`.
- However, the runtime is still not self-contained because the desktop shell still falls back to system `python` when bundled Python is absent.

Conclusion: “ships stale code from a hardcoded path” is fixed; “ships a truly self-sufficient desktop runtime” is not.

### AI-insights router never mounted

Status: fixed in code.

- `backend/main.py` includes `app.include_router(ai_analysis.router, prefix="/api/v1")`.
- `backend/routes/ai_analysis.py` is present and wired.

Residual gap:

- Real end-to-end NVIDIA NIM validation remains unverified in this sandbox and is already recorded in deferred work.

### Async gaps

Status: still open.

- `backend/routes/alerts.py` and `backend/routes/insights.py` are now `async def`, but they still wrap sync engine calls with `asyncio.to_thread()`.
- The async DB helpers exist in `database/db.py`, but engine-level conversion is incomplete.

Conclusion: the code matches the “partial async migration” description from deferred work, not a completed async architecture.

## 4. Desktop Runtime Bundling Status

Status: backend source bundling is implemented; Python/Tesseract/FFmpeg runtime bundling is not.

### Confirmed present

- Tauri bundle resources include `bundled_app/**/*` in `desktop_shell/src-tauri/tauri.conf.json`.
- `desktop_shell/stage-backend.js` stages backend source into `desktop_shell/src-tauri/bundled_app`.
- `main.rs` uses bundled backend source when present.

### Confirmed absent/incomplete

- No bundled Python runtime was found under the staged app tree.
- No bundled Tesseract runtime was found under the staged app tree.
- No bundled FFmpeg runtime was found under the staged app tree.
- `desktop_shell/bundle/README.md` still documents a manual bundle-drop workflow that was never operationalized.

### Additional packaging concerns

- The staged `bundled_app` currently contains generated/runtime residue (`__pycache__`, local DB, storage folders), which is not a clean release artifact.
- `main.rs` logs a fallback to system `python`, which is acceptable for a dev shell but not for production-local-desktop readiness.

Conclusion: desktop runtime bundling is not ready for “install on a clean machine and use offline” acceptance.

## 5. UX / Frontend Completeness

Status: partially complete, but the backend has materially outgrown the routed UI.

### What is present

- 18 routed pages exist under `frontend/src/pages`.
- `SessionDetail` mounts `AiAnalysisPanel`.
- Live monitoring, upload, import, jobs, admin, parser benchmark, and settings pages exist.

### What is still incomplete or mismatched

1. Several backend capabilities do not have first-class routed UI surfaces.
   - No dedicated routed UI was found for AI cost tracking.
   - No dedicated routed UI was found for prompt versioning/A-B management.
   - No dedicated routed UI was found for clustering exploration.
   - No dedicated routed UI was found for dataset quality.
   - No dedicated routed UI was found for evidence-package management.
   - No dedicated routed UI was found for event validation review.

2. The shell presentation quality is inconsistent.
   - `frontend/src/App.tsx` contains visibly corrupted characters and stale “Phase 7 / v0.8” shell text that does not align with current product versioning.

3. The app still carries large page components.
   - `LiveMonitor.tsx` is still the largest page at 389 lines.
   - `Dashboard.tsx`, `Compare.tsx`, `ImportWizard.tsx`, and `Admin.tsx` remain fairly dense.

4. AI UX is still verification-light.
   - The AI panel exists, but the live API path has not been proven against a real NVIDIA endpoint in this environment.

Conclusion: the frontend is no longer “missing,” but it is not yet complete relative to the backend capability set or to a polished desktop-ready standard.

## 6. Docs Accuracy Vs Reality

Status: mixed; some docs are candid, some are stale or too thin to be trustworthy.

### Accurate/useful documents

- `SESSIONGUARDREVIVAL1.3.md` is still the most honest and operationally useful document in the repo.
- `SESSIONGUARDREVIVAL1.4.md` accurately describes the runtime-bundling gap.
- `docs/governance/DEFERRED_WORK.md` is aligned with several still-open issues.

### Stale or misleading documentation

1. `D:/AgentDevWork/repos/OBSIDIAN-TEAM-BOARDROOM/project-docs/SESSIONGUARD.md`
   - Extremely thin and outdated.
   - Does not reflect current repo state, readiness, or active gaps.

2. `README.md`
   - Better than older docs overall, but still contains mismatches.
   - It claims the `intelligence` AI sub-routes still double their own path segment; the current `backend/routes/intelligence.py` does not show that doubled-prefix bug.
   - It still mixes historical truth, current truth, and capability claims in a way that makes quick trust hard.

3. Version/documentation residue
   - Several source file headers still identify the app as `v1.2.0`.
   - The frontend shell still shows older/stale phase/version language.

4. Governance docs vs implemented gate
   - Repo rules describe a required gate that covers the product surface more completely than the actual `gate` workflow does.

Conclusion: docs are better than they were, but the repo still does not have a single concise, current, trustworthy operator/developer source of truth for “what works today, what is only mocked, and what is only scaffolded.”

## 7. Security Assessment

### Positive findings

- JWT auth, PBKDF2 hashing, and refresh-token hashing are implemented sanely for a local-first product.
- SQL queries are parameterized in the inspected paths.
- The backend binds to `127.0.0.1` by default in config and desktop startup.
- Demo-user seeding now requires `SESSIONGUARD_DEMO_PASSWORD` rather than always creating a predictable default account.

### Security issues and risks

1. Auth coverage is inconsistent for stateful endpoints.
   - `backend/main.py` explicitly exempts `/api/v1/upload` and `/api/v1/jobs` from the auth middleware.
   - `backend/routes/uploads.py` allows anonymous uploads when no authenticated user is present.
   - `backend/routes/jobs.py` allows anonymous job submission, polling, listing, cancellation, and worker cleanup behavior with optional auth only.
   - For a product that otherwise has role/user/session access controls, this is a real authorization gap.

2. Secret-key fallback remains operationally risky.
   - `backend/auth/service.py` still falls back to a per-process random secret if `SECRET_KEY` is unset and config has no key.
   - That is acceptable for ad hoc local dev, but not for production-local-desktop release quality because auth continuity changes across restart.

3. Secret scanning is red until triaged.
   - The current verify path fails on heuristic secret hits.
   - These may be false positives, but from a release-governance perspective the state is still red until reviewed and tuned.

4. Upload metadata exposure risk.
   - Upload endpoints return and list stored file paths.
   - Combined with weak auth on upload/job routes, that leaks local file-system details to any caller that can hit the localhost API.

5. Desktop/runtime artifact hygiene is weak.
   - A staged bundle tree containing local DB/storage/runtime residue is not a direct exploit by itself, but it increases accidental data leakage risk in packaged artifacts.

### Security rating

- Internet-facing production: not acceptable
- Local-only desktop with trusted single user: tolerable for development, not release-ready
- Production-local-desktop readiness: blocked until auth coverage and packaging hygiene are fixed

## 8. Overall Readiness Verdict

Current state: not ready for production-local-desktop release.

Blocking themes:

- Verification is not trustworthy enough.
- Required CI does not cover the shipped surface.
- True runtime bundling is missing.
- Auth/authorization is inconsistent on important write/control endpoints.
- Frontend does not yet expose or polish the backend capability set sufficiently.
- Docs still require forensic reading rather than quick trust.

## 9. 100000/100000 Completion Plan

The path below is ordered for maximum truth and minimum rework. Effort is expressed in focused engineer-days.

### Phase 1: Verification Truth First

Effort: 3-5 days

Tasks

- Make the required `gate` workflow actually cover:
  - backend install + tests
  - frontend `npm ci` + `npm run build` + `npx tsc --noEmit`
  - desktop bundle smoke, at least staged backend startup plus Tauri config/build validation
- Make `scripts/verify.sh` and `scripts/verify.ps1` repo-aware for the `frontend/` subproject.
- Triage/tune `secret-scan` so known-safe code patterns stop red-breaking while real secrets still fail.
- Make doc-link validation self-bootstrapping or vendor the tool path so local verify does not depend on ambient global installs.

Acceptance criteria

- `pwsh scripts/verify.ps1` passes on a clean local dev environment with documented prerequisites.
- `bash scripts/verify.sh` passes in CI.
- A PR cannot merge green if backend passes but frontend or staged desktop path breaks.
- Audit/reporting commands are explicitly documented in the repo.

### Phase 2: Desktop Runtime Completion

Effort: 8-12 days

Tasks

- Implement true bundling of Python, Tesseract, and FFmpeg per `SESSIONGUARDREVIVAL1.4.md`.
- Remove manual dependency-drop assumptions from `desktop_shell/bundle/README.md` and replace them with scripted staging.
- Clean the staged artifact so release inputs exclude `__pycache__`, local DBs, and storage residue.
- Update runtime resolution paths in Python/OCR/video code to prefer bundled binaries consistently.

Acceptance criteria

- A fresh Windows machine with no Python/Tesseract/FFmpeg can install and run SessionGuard successfully.
- OCR and video pipeline smoke tests pass against bundled binaries.
- The desktop startup path does not fall back to system Python in release builds.
- Release artifacts are reproducible and contain no local data residue.

### Phase 3: Auth And Local Security Hardening

Effort: 3-5 days

Tasks

- Require authentication for upload/job endpoints, or explicitly document and constrain a guest mode if that is intentional.
- Add per-resource authorization to job listing/cancel/poll paths.
- Stop returning unnecessary absolute file paths from upload APIs.
- Promote `SECRET_KEY` from optional dev convenience to required release configuration.
- Review local-only threat model and document it clearly.

Acceptance criteria

- Anonymous callers cannot submit/cancel/list other users’ jobs.
- Anonymous callers cannot enumerate upload history or local storage paths.
- Release builds fail fast when required auth/config secrets are missing.
- Security model is documented for local-desktop deployment.

### Phase 4: Async/Runtime Reliability Cleanup

Effort: 4-6 days

Tasks

- Complete the engine/db async migration or deliberately standardize on sync-with-worker pools and document that choice.
- Reduce startup monolith pressure by separating DB bootstrap, config loading, and route registration concerns.
- Split `database/db.py` responsibilities into connection/migrations/seeding modules.
- Re-run the bundled backend smoke path after refactor.

Acceptance criteria

- No major route group is “async in name only” without explicit rationale.
- Startup/import behavior is deterministic and testable.
- DB/bootstrap modules are separated enough that packaging and test failures are easier to isolate.

### Phase 5: Frontend Capability Completion And Shell Polish

Effort: 5-8 days

Tasks

- Fix the shell/UI mojibake and stale version/phase text in `frontend/src/App.tsx`.
- Add routed or well-integrated UI surfaces for the already-built backend capabilities that are currently API-only:
  - AI cost
  - prompt management
  - clustering
  - dataset quality
  - evidence package flows
  - event validation/review
- Reduce the biggest page hotspots where they still impair maintainability or UX.
- Add at least one end-to-end happy path for AI/session/evidence UX with mocks where external services are unavailable.

Acceptance criteria

- No visible corrupted glyphs or stale internal phase labels remain in the shipped UI.
- Every major backend feature advertised in README has a discoverable UI path or is explicitly marked admin/API-only.
- Desktop navigation and settings feel coherent rather than historical.
- Frontend build/typecheck/e2e smoke are part of the verified release path.

### Phase 6: Docs And Source-Of-Truth Consolidation

Effort: 2-3 days

Tasks

- Rewrite the external brief `OBSIDIAN-TEAM-BOARDROOM/project-docs/SESSIONGUARD.md` to reflect real status or mark it historical.
- Tighten `README.md` so it separates:
  - verified working today
  - implemented but unverified externally
  - intentionally deferred
- Remove or correct stale claims about route bugs that are already fixed.
- Normalize stale version headers in source files where they create confusion.

Acceptance criteria

- A new engineer can read README plus one active status doc and know exactly what is release-ready.
- No current doc claims a known-fixed bug is still open or a known-open gap is already done.
- File-header version residue no longer conflicts with actual runtime versioning.

### Phase 7: Clean-Machine Release Rehearsal

Effort: 3-4 days

Tasks

- Run a scripted release rehearsal on clean Windows VM first, then macOS/Linux as packaging matures.
- Verify install, launch, login, upload, OCR, AI fallback behavior, export/evidence, and updater behavior.
- Produce a release checklist artifact and attach logs/screenshots.

Acceptance criteria

- Clean-machine Windows acceptance succeeds end to end offline except where external AI is intentionally optional.
- macOS/Linux smoke reaches parity for the supported installer targets.
- Release checklist is green and saved under `audits/` or `docs/operations/`.

## 10. Recommended Exit Criteria For “Production-Local-Desktop Ready”

Do not call SessionGuard production-local-desktop ready until all of the below are true:

- Required CI proves backend, frontend, and desktop packaging surfaces.
- Local verify is green and reproducible from documented prerequisites.
- The shipped app runs on a clean Windows machine without system Python/Tesseract/FFmpeg.
- Upload/job endpoints have consistent authentication and authorization.
- README and active revival docs agree with actual code behavior.
- A clean-machine release rehearsal has passed and been captured in an audit artifact.

## Final Verdict

SessionGuard is closer to a trustworthy local product than it was before the 2026-07-23 recovery work, but it is still in the “implemented, partially verified, operationally inconsistent” band rather than the “release-ready local desktop” band. The remaining work is finite and mostly unblocked, but it must be driven by verification truth, packaging completion, and security/UX closure rather than by adding more backend features.
