# 2026-07-24 Codex Revival 1.3 Coverage Audit

## Scope

Continued the Revival 1.3 plan on the dedicated `_repo_clone` branch after
the trust-track work recorded in the earlier audit.

## Changes

- A2 advanced to partial: `tests/test_packaging_resources.py` validates all
  configured MSI, NSIS, macOS, AppImage, deb, and rpm targets plus the staged
  backend/config entrypoints. Actual artifact execution remains a CI-runner
  responsibility.
- B1 advanced to partial: `tests/test_video_pipeline.py` covers missing input,
  frame cadence, scene-change detection, and perceptual-hash helpers. The
  module measured 19% coverage in the full run.
- B2 advanced to partial: `tests/test_evidence_package.py` covers valid,
  tampered, and missing manifest entries; `tests/test_export_service.py` covers
  missing-session failures for PDF and Excel. The Excel exporter now closes its
  DB connection on that early-return path. The module measured 25% coverage;
  full export generation remains open. A successful isolated evidence-package
  assembly test now covers the core ZIP contents and export registration.
- B4 advanced to partial: `tests/test_roi_calibrator.py` covers missing image,
  label recognition, and numeric OCR classification. The module measured 33%.

## Verification

`python -m pytest` from `_repo_clone`: **150 passed, 6 skipped**. Overall
coverage measured 46%. Skips are the existing encryption/OCR dependency skips.

## Deferred or blocked

- B3 live NVIDIA NIM verification requires an approved real API key and
  external network access; no paid/external call was made.
- A1 CI validation and A2 artifact execution require GitHub runner execution.
- C1 was not changed: converting synchronous engines to async requires a
  broader DB/transaction design pass than a safe route-signature edit.
- D1 audit found only startup `print()` calls in backend code; no backend
  failure path was found that relies solely on `print()`. Several broad
  `except Exception` fallbacks remain intentionally silent and are tracked for
  targeted observability work rather than changed indiscriminately.
