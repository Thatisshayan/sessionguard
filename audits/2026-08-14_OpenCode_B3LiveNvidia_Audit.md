# Audit: B3 Live NVIDIA NIM Verification

Date: 2026-08-14
Agent: OpenCode
Scope: Revival 1.3 task B3 — live verification of the NVIDIA NIM AI path
Branch: `feat/b3-nvidia-live-verify`

## Summary

The mocked contract tests (`tests/test_ai_insights_contract.py`) pin the
transport/persistence/fallback contract entirely with mocks. B3 performs the
one thing they intentionally cannot: a real call to
`https://integrate.api.nvidia.com` with a real `NVIDIA_API_KEY`.

R24 (Spend / Cost Guardrail, REPO_RULES.md:189-190) requires explicit Shayan
approval for paid API calls. Approval was given: Shayan placed a real key in
`.env.example` and instructed its use. The key was read into the environment,
used for verification, and then **removed from `.env.example`** (restored to
the `nvapi-YOUR_KEY_HERE` placeholder). The key was never committed to git.

## Deliverable

`scripts/verify_nvidia_live.py` — live verification harness:

- Isolates the database via `SG_DATA_DIR` -> `tempfile.mkdtemp` (never touches
  the real `sessionguard.db`).
- Seeds one session + two events (mirrors the `seeded_session` test fixture).
- Runs `analyse_session_with_ai()` and asserts:
  1. `source == "nvidia_ai"` (not `rule_based`/`ollama_ai`)
  2. `ai_available is True` and active model matches `NVIDIA_MODELS[0]`
  3. `[AI]` insights persisted to the `insights` table
  4. A row landed in `ai_cost_log` with input/output tokens > 0
- Exit codes: 2 = no key, 1 = FAIL, 0 = PASS.

## Live run (final)

```
[B3] Model: nvidia/llama-3.3-nemotron-super-49b-v1  |  Endpoint: https://integrate.api.nvidia.com/v1/chat/completions
[B3] source=nvidia_ai model=nvidia/llama-3.3-nemotron-super-49b-v1 risk=AiInsightRiskLevel.LOW
[B3] headline: Controlled session with minimal loss despite low RTP
[B3] insights persisted: 3  cost rows: 1
[B3] cost_log: model=nvidia/llama-3.3-nemotron-super-49b-v1 in=537 out=244 cost=$0.000151
[B3] PASS
EXIT=0
```

## Bugs found and fixed

1. **Default model 404s for the account.** All five previously-hardcoded
   `NVIDIA_MODELS` entries failed with `404 Function not found for account`
   (and `nvidia/llama-3.3-70b-instruct`, `nvidia/mistral-large-2-instruct`
   with bare `404 page not found`). The account's `/v1/models` catalog was
   probed; `nvidia/llama-3.3-nemotron-super-49b-v1` (and v1.5) verified working
   (21/17 tokens). Fix: `NVIDIA_MODELS` reordered to put the verified model
   first (default), old models retained as alternatives. Pricing added:
   $0.10/M input, $0.40/M output (matches NVIDIA NIM catalog).
   `MODEL_PRICING`, the module docstring, `.env.example`, and
   `config/app_config.json` updated to match.

2. **`_log_ai_cost` recorded zero tokens.** NVIDIA NIM returns OpenAI-style
   usage keys (`prompt_tokens`/`completion_tokens`), but `_log_ai_cost` only
   read `input_tokens`/`output_tokens`, so cost was always $0.000000 even
   though the call succeeded. Fix: normalization added —
   `usage.get("input_tokens") or usage.get("prompt_tokens") or 0`
   (and `output_tokens` / `completion_tokens`).

## Regression checks

- `python -m pytest tests/test_ai_insights_contract.py -q` -> **11 passed**.
- Cost now lands with real token counts: in=537, out=244, cost=$0.000151.

## Notes / follow-ups

- The key was read into the environment only for the run and removed from
  `.env.example` afterwards (per Shayan's instruction). `.env.example` remains
  the committed template with the `nvapi-YOUR_KEY_HERE` placeholder.
- Leftover throwaway DBs from earlier failing runs (`%TEMP%\sg-b3-live-*`)
  should be cleaned up after the branch merges.
- Remaining deferred items: C1 async engine migration, WS3 clean-VM runtime
  rehearsal.