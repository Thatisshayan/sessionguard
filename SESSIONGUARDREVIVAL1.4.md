# SessionGuard Revival 1.4 — True Zero-Dependency Portability

**Created**: 2026-07-23 · **Status**: Not started (deliberately deferred) · **Parent doc**: [`SessionGuardRevival.md`](SessionGuardRevival.md)
**Sibling doc**: [`SESSIONGUARDREVIVAL1.3.md`](SESSIONGUARDREVIVAL1.3.md) — active trust/verification sprint; this work was split out of it on purpose

---

## Why this is its own document instead of a task in 1.3

`SESSIONGUARDREVIVAL1.3.md` fixed the installer so it actually **ships and runs its own backend source** instead of silently depending on a stale dev-machine checkout (see that document's finding #13). That was a correctness bug and needed an immediate fix.

This document is different: it's not fixing a bug, it's finishing a feature that was *never actually attempted* despite being marked done. `SessionGuardRevival.md`'s Phase 4 (E4, "Bundle deps") claims:

> ✅ Done (2026-07-22) — `tauri.conf.json` updated with `externalBin`, `resources`, expanded bundle targets; `main.rs` checks bundled paths first; `bundle/README.md` with setup instructions

What actually existed was a config that referenced binaries nobody had ever placed, and a `README.md` describing a manual process nobody had completed — confirmed empty during the 1.3 session (`desktop_shell/bundle/` contained only its own instructions, no binaries). The "done" status was true only in the sense that the *scaffolding* existed.

Doing this properly — downloading, packaging, licensing-checking, and testing a full embeddable Python interpreter plus Tesseract OCR plus FFmpeg across Windows, macOS, and Linux — is a genuinely large amount of work with a lot of platform-specific failure surface. Cramming it into 1.3 alongside urgent correctness fixes would repeat exactly the mistake this whole revival effort keeps finding: rushing packaging work and calling it done before it's verified. This document exists so that doesn't happen again.

---

## What "done" has to mean this time

A single, testable acceptance bar, because the whole reason this document exists is that the previous attempt at this exact feature didn't have one:

> **On a Windows, macOS, and Linux VM with *nothing* pre-installed** — no Python, no Tesseract, no FFmpeg, no dev tools of any kind — installing the SessionGuard package and launching the app results in a fully working session: OCR extraction succeeds on a sample screenshot, a session can be created and viewed, and `sessionguard --version` (or the equivalent) works with the network disconnected.

Anything short of that (e.g., "it works if Python happens to already be there") is Track 1.3 territory, already handled by the graceful-degradation behavior that exists today. This document is specifically about eliminating the "happens to already be there" dependency.

---

## Task Board

### Python runtime

| ID | Task | Notes |
|----|------|-------|
| P1 | Download and stage the Windows embeddable Python (`python-3.12.x-embed-amd64.zip` from python.org) into the build pipeline, not manually per `bundle/README.md`'s current instructions | Should be a scripted download-and-verify step (checksum-pinned), not a human downloading a zip and dropping it in a folder — that's exactly the manual step that never got done |
| P2 | Install all `requirements.txt` dependencies into the embeddable Python's `Lib/site-packages` as part of the same automated step | `pip install -t python/Lib/site-packages -r requirements.txt`, scripted, run in CI so it's verified on every build rather than assumed |
| P3 | Repeat for macOS and Linux — decide between a statically-linked Python build (e.g., python-build-standalone) vs. relying on system Python with a bundled venv; the two platforms have different norms here and picking one without checking will likely repeat this document's own origin story | This is the one where "3 different runtimes across 3 OSes" gets real — budget real time for it |
| P4 | Update `find_python()` in `main.rs` to check the bundled interpreter path *before* falling back to system PATH (the check already exists in code from 1.3 — `resources/bundled_app/python/python.exe` — but currently always misses since nothing is ever placed there) | Small Rust change once P1–P3 land; the fallback behavior is already correct, it just needs something to find |

### Tesseract OCR

| ID | Task | Notes |
|----|------|-------|
| T1 | Package Tesseract 5.x binaries + `tessdata` (language files) per platform | Windows: UB-Mannheim builds (already referenced in `bundle/README.md`); macOS/Linux: check licensing and redistribution terms before bundling — Tesseract is Apache 2.0 but verify the specific build/binary source's terms too |
| T2 | Update `ocr_engine.py`'s Tesseract-path resolution to check the bundled location first, same pattern as Python | Should mirror whatever pattern P4 establishes for consistency |
| T3 | Verify OCR accuracy benchmarks (`tests/test_ocr_benchmark.py`, already exists from Phase 5/C9) still pass against the *bundled* binary, not just a system install | This test suite exists — use it, don't just assume the bundled binary behaves identically to whatever was tested in CI's `apt-get install tesseract-ocr` step |

### FFmpeg

| ID | Task | Notes |
|----|------|-------|
| F1 | Package FFmpeg static builds per platform (Windows: gyan.dev builds, already referenced in `bundle/README.md`; macOS/Linux: evaluate static build sources) | Same licensing-check discipline as Tesseract — FFmpeg's licensing varies by which codecs are compiled in (GPL vs LGPL builds) |
| F2 | Update `video_pipeline.py`'s FFmpeg invocation to check the bundled path first | Same pattern as P4/T2 |
| F3 | Verify video chunking/resume (Phase 5, C10) still works against the bundled binary | Existing feature, existing tests presumably — re-run against the bundled binary specifically |

### Cross-cutting

| ID | Task | Notes |
|----|------|-------|
| X1 | **Actually provision the clean VMs** (Windows/macOS/Linux, nothing pre-installed) and run the acceptance test from this document's top section on all three, manually, at the end | This is the step the previous "done" claim skipped entirely. Do not mark this document's work complete without doing this — that's precisely the mistake being corrected |
| X2 | Wire the download/staging steps into CI (`build.yml`) so the bundled runtime is verified on every tagged release build, not assembled by hand once | Prevents this from becoming stale the way the original `bundle/README.md` manual instructions did — nobody was ever going to run them by hand repeatedly |
| X3 | Update installer size expectations in `SessionGuardRevival.md`'s "Expected Outcome" table — bundling three full runtimes will grow the installer meaningfully past the "<20MB" target that assumed Tauri v2's slimness alone; decide whether that target still holds or needs revising once real sizes are known | Small doc-hygiene task, but worth doing before the number becomes another stale claim |
| X4 | Decide and document the update story: does the auto-updater (E2, already shipped) redownload the full bundle on every update, or only the app binary with runtimes cached separately? | Affects update size/speed meaningfully once runtimes are ~150-300MB combined; better decided before shipping than discovered by a user's slow update |

---

## Sequencing note

This is a big enough scope that it should be its own sprint, worked start-to-finish, rather than interleaved with `SESSIONGUARDREVIVAL1.3.md`'s trust-rebuilding work. Recommended order once started: Python first (P1–P4, since Tesseract/FFmpeg invocation both depend on *a* working bundled environment to test against), then Tesseract, then FFmpeg, then the cross-cutting verification (X1–X4) at the end — not interspersed, so the final acceptance test (X1) is a true end-to-end check of everything together.

---

## Definition of Done

- [ ] Python, Tesseract, and FFmpeg all bundled and resolved correctly on Windows, macOS, and Linux
- [ ] Acceptance test (top of this document) passes on all three platforms, on genuinely clean VMs, verified manually — not assumed
- [ ] CI verifies the bundle on every tagged build (X2)
- [ ] Update story decided and documented (X4)
- [ ] `SessionGuardRevival.md`'s Phase 4 E4 entry corrected to point here, and its "Expected Outcome" installer-size table updated if needed

---

*This document lives at `SESSIONGUARDREVIVAL1.4.md` in the repo root. Do not mark this complete based on the bundling code existing — mark it complete based on the acceptance test in this document actually passing on clean VMs. That distinction is the entire reason this document exists.*
