# SESSIONGUARD — REPO_DIRECTIVE

> Goal-layer constitution. `REPO_RULES.md` is the law; this is the mission. Every task
> MUST carry `traces-to:`. Orphan tasks rejected by CI (scripts/verify.sh → directive-lint) + Sentinel.
> Note: remote is Thatisshayan/sessionguard (Shayan handles push/PR). This file is committed
> locally on the governance branch.

## Vision

SESSIONGUARD is a Local-First Session Intelligence Platform for casino/slot analysis:
real OCR (Tesseract 5), behavior-pattern detection (scikit-learn), live screen monitoring,
video→event pipelines, AI narrative insights (NVIDIA NIM + Ollama offline fallback),
multi-format exports, and evidence packages with hash manifests. Desktop + Web.
North-star: a trustworthy, local-first analysis tool that produces auditable evidence
packages with zero credential leakage and explicit, consented use only.

## Non-Goals

- NOT a surveillance tool outside explicit, consented casino/slot analysis use.
- NOT sending session captures to third parties; local-first, Ollama offline fallback.
- NOT storing raw captures with secrets in repo.

## Phases

### P1 — Current-State Audit (CURRENT)
  exit criteria: README accurate (v1.5.2); build green; secrets gitignored.
### P2 — Analysis Core
  exit criteria: OCR + behavior detection + insight pipeline tested.
### P3 — Evidence & Safety
  exit criteria: hash-manifest exports; safe defaults; audit log.

## Sprints

### S1 (maps to P1) — truth + green
  goal: verify.sh passes; README matches v1.5.2.
### S2 (maps to P2) — pipeline
  goal: OCR→detection→insight tested.

## Epics / Chapters

### E1 — Capture & OCR (maps to P2)
  screen monitor + Tesseract 5.
### E2 — Intelligence (maps to P2)
  scikit-learn patterns + NIM/Ollama insights.
### E3 — Evidence & Safety (maps to P1/P3)
  exports + hash manifests + credential hygiene.

## Tasks

- [ ] T1 — Verify build+test green in CI (verify.sh) | traces-to: P1/S1/E3 | acceptance: PR gate passes
- [ ] T2 — Ensure no captures/creds committed (.gitignore correct) | traces-to: P1/S1/E3 | acceptance: secret-scan clean
- [ ] T3 — Add tests for OCR→behavior→insight pipeline | traces-to: P2/S2/E1 | acceptance: pipeline covered end-to-end
- [ ] T4 — Verify Ollama offline fallback path works (no NIM needed) | traces-to: P2/S2/E2 | acceptance: insight generated offline
- [ ] T5 — Add hash-manifest to evidence export + audit log | traces-to: P3/S2/E3 | acceptance: export has verifiable hashes; actions logged

## Sentinel Constraints

- auto-approve: docs/tests/typing tracing to P1/E3.
- review-required: capture, OCR, model calls, credential handling, exports.
- locked: `main`; captures/credentials never; scope needs Shayan.
