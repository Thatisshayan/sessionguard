# 2026-07-25 OpenCode Revival 1.3 Gap-Fix Audit

## Trigger

User called out that the previous session summary was misleading: it claimed
completion without distinguishing "committed locally" vs "pushed to origin" vs
"CI-verified". This audit documents the honest state and what was done to close
the gaps.

## What was actually wrong

| Gap | Previous claim | Truth |
|-----|---------------|-------|
| Push status | Implicitly "done" | C5 (c05bb3e) and D1 (a2b4ee4) were committed locally but **not pushed** |
| CI verification | None stated | None of these 12 commits have ever been through a CI run on GitHub |
| Audit docs for C5/D1 | None existed | The existing audits predated C5/D1 work |
| verify.ps1 | Mentioned but never run | The script hangs/times out in this sandbox; this is documented in DEFERRED_WORK.md but was not flagged to the user |
| Sprint Definition of Done | "CI gate must be green" | No commit on this branch has ever passed a CI run |

## What was fixed in this pass

1. **Pushed unpushed commits**: `git push origin agent/revival-1-3-followup` —
   commits c05bb3e (C5) and a2b4ee4 (D1) are now on origin.
2. **Test suite re-verified**: `python -m pytest tests/` — **204 passed, 6 skipped,
   2 warnings, 25s**. Coverage 54%. The 6 skips are the existing encryption/OCR
   dependency skips (unchanged from previous passes).
3. **verify.ps1 attempted**: Timed out at 60s. The script does a recursive file
   content scan that is too slow for this sandbox. Not a code problem — an
   environment limitation documented in DEFERRED_WORK.md.

## What still gaps

- **Zero CI runs have executed on `agent/revival-1-3-followup`** — the
  bundled-backend-smoke workflow, packaging-resource tests, and all other CI
  steps exist structurally but have never been exercised by GitHub Actions.
  Until a PR to main or a direct push trigger runs them, the CI column in the
  Definition of Done is unfilled.
- **No real NVIDIA NIM call** has been made (B3). Mocked contract tests exist;
  live verification requires an approved API key per REPO_RULES R24.
- **verify.ps1** cannot complete in this environment. A future agent in a
  fuller environment should run it before merging.

## Commit evidence

```
% git log origin/agent/revival-1-3-followup --oneline -5
a2b4ee4 feat(revival): targeted AI-layer observability (D1)
c05bb3e feat(revival): add opt-in request-dedup middleware + tests (C5)
46106f1 test(revival): raise roi_calibrator coverage to 75% (B4)
4d7fa2b test(revival): cover export ImportError + live PDF/Excel generation (B2)
53e2b56 test(revival): raise video_pipeline coverage to 38% (B1)
```

```
% python -m pytest tests/ -q --tb=no
204 passed, 6 skipped, 2 warnings in 25.34s
```

## Summary for next agent

All 12 commits are on `origin/agent/revival-1-3-followup`. The branch has never
been through CI. Before merging to main: (1) create a PR, (2) wait for CI green,
(3) run `scripts/verify.ps1` in a full environment, (4) verify the
bundled-backend smoke workflow and packaging tests on GitHub runners.
