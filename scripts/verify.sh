#!/usr/bin/env bash
# Repo-adaptive governance verification.
# Implements REPO_RULES.md checks: secret-scan, doc-freshness, build, test, deploy-dry.
# Emits GitHub Actions annotations (::error / ::notice) when run in CI.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

FAIL=0
notice() { echo "::notice title=$1::$2"; }
error()  { echo "::error title=$1::$2"; FAIL=1; }

# ---------------------------------------------------------------- 1. secret-scan
echo "== secret-scan =="
if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --no-banner --redact || error "secret-scan" "gitleaks found secrets"
else
  # (a) filename-based: private key / credential files must not be committed.
  #     Use git-tracked files only — directory-name exclusions cannot hide committed source.
  tracked=$(git ls-files 2>/dev/null || find . -type f -not -path '*/.git/*')
  bad_files=$(echo "$tracked" \
    | grep -E '(\.p8$|\.p12$|credential|\.pem$|\.key$)' \
    | grep -v '^audits/private/' || true)
  if [ -n "$bad_files" ]; then error "secret-scan" "secret files present: $bad_files"; fi
  # (b) content-based: scan only git-tracked code/config, require an ASSIGNED VALUE.
  # Filter hits against .verify/.secret-scan-ignore.json if present
  raw_hits=$(echo "$tracked" \
    | grep -E '\.(json|env|ts|js|py|yml|yaml|toml|sh)$' \
    | xargs grep -lE "(API_KEY|SECRET|PRIVATE_KEY|TOKEN|PASSWORD)[[:space:]]*[=:][[:space:]]*[\"']?[A-Za-z0-9/+_-]{8,}" \
    2>/dev/null || true)
  
  hits=""
  if [ -f .verify/.secret-scan-ignore.json ]; then
    for f in $raw_hits; do
      if ! grep -q "\"file\": \"$f\"" .verify/.secret-scan-ignore.json; then
        hits="$hits $f"
      fi
    done
  else
    hits=$raw_hits
  fi
  
  if [ -n "$(echo $hits | xargs)" ]; then error "secret-scan" "possible hardcoded secrets in: $hits"; fi
fi

# ---------------------------------------------------------------- 2. doc-freshness
echo "== doc-freshness =="
[ -f README.md ] || error "doc-freshness" "README.md missing"
# link integrity (mandatory — fail if tool is unavailable)
if command -v markdown-link-check >/dev/null 2>&1; then
  MLC_CMD="markdown-link-check"
elif command -v npx >/dev/null 2>&1; then
  MLC_CMD="npx markdown-link-check"
else
  MLC_CMD=""
fi

if [ -z "$MLC_CMD" ]; then
  error "doc-freshness" "markdown-link-check not installed (required for doc-link validation)"
else
  find . -name '*.md' -not -path './node_modules/*' -not -path './.git/*' \
    -not -path './audits/private/*' -not -path './desktop_shell/*' -not -path './.venv/*' -print0 2>/dev/null \
    | xargs -0 -r -n1 $MLC_CMD -c .markdown-link-check.json || error "doc-freshness" "broken doc links"
fi
# audit age (≤ 30 days, from ISO date in filename, not mtime)
newest_audit=$(find audits -name '????-??-??_*.md' -not -path '*/private/*' 2>/dev/null \
  | sed 's|.*/\([0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}\)_.*|\1|' \
  | sort -r | head -1)
if [ -z "$newest_audit" ]; then
  error "doc-freshness" "no audit found under audits/"
else
  audit_epoch=$(date -d "$newest_audit" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$newest_audit" +%s)
  age=$(( ($(date +%s) - audit_epoch) / 86400 ))
  if [ "$age" -gt 30 ]; then error "doc-freshness" "newest audit ($newest_audit) is $age days old (>30)"; fi
fi
# doc baseline (must exist — bootstrap creates it; verification only validates)
if [ ! -f docs/_baseline.json ]; then
  error "doc-freshness" "docs/_baseline.json missing — run bootstrap (apply script) first"
fi
base=$(grep -o '"md_count": *[0-9]*' docs/_baseline.json | grep -o '[0-9]*$')
cur=$(find docs -name '*.md' 2>/dev/null | wc -l)
if [ "${cur:-0}" -lt "${base:-0}" ]; then
  error "doc-freshness" "docs md count $cur < baseline $base (deletion without approval)"
fi

# ---------------------------------------------------------------- 3. build / test
echo "== build / test =="

# check frontend if present
if [ -d frontend ] && [ -f frontend/package.json ]; then
  echo "-- frontend --"
  (cd frontend && ([ -d node_modules ] || npm ci) && npx tsc --noEmit && npm run build) || error "frontend" "frontend build/type-check failed"
fi

# pick the package manager from lockfiles (respect pnpm/yarn, don't assume npm)
PM=""
if [ -f pnpm-lock.yaml ]; then PM=pnpm
elif [ -f yarn.lock ]; then PM=yarn
elif [ -f package-lock.json ]; then PM=npm
fi
run_with_timeout() { # $1=seconds $2=label $3..=cmd
  local t="$1"; shift; local label="$1"; shift
  local out; out=$(timeout "$t" "$@" 2>&1); local rc=$?
  if [ $rc -eq 124 ]; then error "$label" "timed out after ${t}s (likely network/install hang)"; return; fi
  if [ $rc -ne 0 ]; then error "$label" "failed (rc=$rc): $(printf '%s' "$out" | tail -3)"; return; fi
  notice "$label" "ok"
}
if [ -n "$PM" ]; then
  case "$PM" in
    pnpm) run_with_timeout 300 build pnpm install --frozen-lockfile
          pnpm run build --if-present 2>&1 | tail -3 ;;
    yarn) run_with_timeout 300 build yarn install --frozen-lockfile ;;
    npm)  run_with_timeout 300 build npm ci ;;
  esac
  if [ $FAIL -eq 0 ]; then
    case "$PM" in
      npm)  npm run build --if-present >/dev/null 2>&1 && notice build "build ok" || error build "build failed"
            npm test --if-present >/dev/null 2>&1 && notice test "test ok" || error test "test failed" ;;
      pnpm) pnpm run build --if-present >/dev/null 2>&1 && notice build "build ok" || error build "build failed"
            pnpm test --if-present >/dev/null 2>&1 && notice test "test ok" || error test "test failed" ;;
      yarn) yarn build >/dev/null 2>&1 && notice build "build ok" || error build "build failed"
            yarn test >/dev/null 2>&1 && notice test "test ok" || error test "test failed" ;;
    esac
  fi
elif [ -f pyproject.toml ] || [ -f requirements.txt ]; then
  pip install -q -r requirements.txt 2>/dev/null || true
  pytest -q || error "test" "pytest failed"
elif [ -f Cargo.toml ]; then
  cargo build --release || error "build" "cargo build failed"
  cargo test --release || error "test" "cargo test failed"
else
  notice "build" "no build system detected; docs/static repo — skipping build/test"
fi

# ---------------------------------------------------------------- 4. desktop-bundle smoke
echo "== desktop-bundle smoke =="
if [ -f desktop_shell/stage-backend.js ]; then
  echo "-- staging bundled backend --"
  node desktop_shell/stage-backend.js || error "bundle" "staging script failed"
  
  if [ -d desktop_shell/src-tauri/bundled_app ]; then
    # check for residue
    residue=$(find desktop_shell/src-tauri/bundled_app -name "__pycache__" -o -name "*.db" 2>/dev/null)
    if [ -n "$residue" ]; then
      error "bundle" "staging contains runtime residue: $residue"
    fi
    # minimal startup smoke
    echo "-- backend smoke --"
    SMOKE_LOG=$(mktemp)
    trap "rm -f $SMOKE_LOG" EXIT
    OLD_PWD=$(pwd)
    cd desktop_shell/src-tauri/bundled_app
    SESSIONGUARD_DEV_MODE=true python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8011 --no-access-log > "$SMOKE_LOG" 2>&1 &
    PID=$!
    cd "$OLD_PWD"
    sleep 3
    if curl -fsS http://127.0.0.1:8011/health >/dev/null 2>&1; then
      notice "bundle" "bundled backend smoke ok"
    else
      error "bundle" "bundled backend smoke failed (check $SMOKE_LOG)"
      tail -20 "$SMOKE_LOG"
    fi
    kill $PID || true
  fi
fi

# ---------------------------------------------------------------- 5. deploy-dry
echo "== deploy-dry =="
if [ -f vercel.json ]; then
  vercel build --dry-run >/dev/null 2>&1 || error "deploy" "vercel dry-run failed"
elif [ -f railway.json ] || [ -f railway.toml ]; then
  notice "deploy" "railway target present; run 'railway up --detach' manually"
elif [ -f eas.json ]; then
  npx eas build --platform all --local --no-wait --non-interactive >/dev/null 2>&1 \
    || error "deploy" "eas dry build failed"
elif [ -f netlify.toml ]; then
  notice "deploy" "netlify target present; manual deploy"
else
  notice "deploy" "no deploy target; smoke build already covered"
fi

# ---------------------------------------------------------------- 5. directive-lint
# REPO_DIRECTIVE.md is the goal-layer constitution. Every task must trace to a
# Phase/Sprint/Epic id defined in the same file. Orphan tasks = divergence risk.
# ROLLOUT NOTE: missing directive is a `notice` (not `error`) during P8 rollout
# so repos without one yet don't red-break main. Flip to `error` once every
# portfolio repo has a linted REPO_DIRECTIVE.md (see project-sentinel P8).
echo "== directive-lint =="
if [ ! -f REPO_DIRECTIVE.md ]; then
  notice "directive-lint" "REPO_DIRECTIVE.md not present yet (required after P8 rollout)"
else
  # collect defined ids: P<num>, S<num>, E<num>
  defined=$(grep -oE '\b(P[0-9]+|S[0-9]+|E[0-9]+)\b' REPO_DIRECTIVE.md | sort -u)
  # find task lines: "- [ ] T..." and require a traces-to: <id>
  orphans=0
  while IFS= read -r line; do
    if echo "$line" | grep -qE '^[[:space:]]*- \[ \] T[0-9]+'; then
      if ! echo "$line" | grep -qE 'traces-to:'; then
        error "directive-lint" "orphan task (no traces-to): ${line:0:80}"
        orphans=1
      else
        ref=$(echo "$line" | grep -oE 'traces-to:[^|]*' | sed 's/traces-to://' | tr -d ' ' | cut -d/ -f1)
        if ! echo "$defined" | grep -qx "$ref"; then
          error "directive-lint" "task references undefined id '$ref': ${line:0:80}"
          orphans=1
        fi
      fi
    fi
  done < <(grep -E '^[[:space:]]*- \[ \] T[0-9]+' REPO_DIRECTIVE.md)
  if [ "$orphans" -eq 0 ]; then notice "directive-lint" "all tasks trace to a defined phase/sprint/epic"; fi
fi

if [ "$FAIL" -ne 0 ]; then
  echo "VERIFY FAILED"
  exit 1
fi
echo "VERIFY PASSED"
