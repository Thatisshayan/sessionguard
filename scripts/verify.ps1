# Repo-adaptive governance verification (PowerShell / Windows).
# Mirrors scripts/verify.sh: secret-scan, doc-freshness, build, test, deploy-dry.
$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRoot

$failed = $false
function Notice($t,$m){ Write-Host "::notice title=$t::$m" }
function Err($t,$m){ Write-Host "::error title=$t::$m"; $script:failed = $true }

# 1. secret-scan (fallback grep; gitleaks if available)
Write-Host "== secret-scan =="
if (Get-Command gitleaks -ErrorAction SilentlyContinue) {
  gitleaks detect --no-banner --redact
  if ($LASTEXITCODE -ne 0) { Err "secret-scan" "gitleaks found secrets" }
} else {
  # (a) filename-based
  $badFiles = Get-ChildItem -Recurse -File -Include *.p8,*.p12,*credential*,*.pem,*.key `
    -Exclude node_modules,.git,audits/private -ErrorAction SilentlyContinue
  if ($badFiles) { Err "secret-scan" "secret files present: $($badFiles.FullName -join ', ')" }
  # (b) content-based: code/config only, require an assigned value (not prose mentions)
  $hits = Get-ChildItem -Recurse -File -Include *.json,*.env*,*.ts,*.js,*.py,*.yml,*.yaml,*.toml,*.sh `
    -Exclude node_modules,.git,audits/private -ErrorAction SilentlyContinue `
    | Where-Object { Select-String -Path $_.FullName -Pattern '(API_KEY|SECRET|PRIVATE_KEY|TOKEN|PASSWORD)\s*[=:]\s*["'']?[A-Za-z0-9/+_-]{8,}' -Quiet }
  if ($hits) { Err "secret-scan" "possible hardcoded secrets in: $($hits.FullName -join ', ')" }
}

# 2. doc-freshness
Write-Host "== doc-freshness =="
if (-not (Test-Path README.md)) { Err "doc-freshness" "README.md missing" }
$newest = Get-ChildItem -Path audits -Recurse -Filter *.md -Exclude private -ErrorAction SilentlyContinue `
  | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $newest) { Err "doc-freshness" "no audit found under audits/" }
else {
  $age = ([datetime]::Now - $newest.LastWriteTime).Days
  if ($age -gt 30) { Err "doc-freshness" "newest audit is $age days old (>30)" }
}
if (-not (Test-Path docs/_baseline.json)) {
  $cnt = (Get-ChildItem -Path docs -Recurse -Filter *.md -ErrorAction SilentlyContinue).Count
  "{ `"md_count`": $cnt }" | Out-File docs/_baseline.json -Encoding utf8
  Notice "doc-freshness" "captured docs baseline md_count=$cnt"
}
$base = ([int]((Get-Content docs/_baseline.json) -match '"md_count":\s*(\d+)' | ForEach-Object { $Matches[1] }))
$cur = (Get-ChildItem -Path docs -Recurse -Filter *.md -ErrorAction SilentlyContinue).Count
if ($cur -lt $base) { Err "doc-freshness" "docs md count $cur < baseline $base (deletion without approval)" }

# 3. build / test (adaptive)
Write-Host "== build / test =="
$PM = $null
if (Test-Path pnpm-lock.yaml) { $PM = 'pnpm' }
elseif (Test-Path yarn.lock) { $PM = 'yarn' }
elseif (Test-Path package-lock.json) { $PM = 'npm' }

function RunTimed($secs, $label, $cmd) {
  $p = Start-Process -NoNewWindow -PassThru -RedirectStandardError NUL -Wait $cmd[0] $cmd[1..($cmd.Count-1)]
  if ($p.ExitCode -eq 124) { Err $label "timed out after ${secs}s (likely network/install hang)" }
  elseif ($p.ExitCode -ne 0) { Err $label "failed (rc=$($p.ExitCode))" }
  else { Notice $label "ok" }
}

if ($PM) {
  switch ($PM) {
    'pnpm' { RunTimed 300 build @('pnpm','install','--frozen-lockfile') }
    'yarn' { RunTimed 300 build @('yarn','install','--frozen-lockfile') }
    'npm'  { RunTimed 300 build @('npm','ci') }
  }
  if (-not $failed) {
    @('npm','pnpm','yarn') | ForEach-Object {
      $c = if ($_ -eq 'npm') { 'npm run build --if-present' } elseif ($_ -eq 'pnpm') { 'pnpm run build --if-present' } else { 'yarn build' }
      if (Get-Command $_ -ErrorAction SilentlyContinue) {
        Invoke-Expression $c >$null 2>&1; if ($LASTEXITCODE -eq 0) { Notice build "build ok" } else { Err build "build failed" }
      }
    }
    @('npm','pnpm','yarn') | ForEach-Object {
      $c = if ($_ -eq 'npm') { 'npm test --if-present' } elseif ($_ -eq 'pnpm') { 'pnpm test --if-present' } else { 'yarn test' }
      if (Get-Command $_ -ErrorAction SilentlyContinue) {
        Invoke-Expression $c >$null 2>&1; if ($LASTEXITCODE -eq 0) { Notice test "test ok" } else { Err test "test failed" }
      }
    }
  }
} elseif (Test-Path (Join-Path $RepoRoot pyproject.toml) -or (Test-Path requirements.txt)) {
  if (Test-Path requirements.txt) { pip install -q -r requirements.txt }
  pytest -q; if ($LASTEXITCODE -ne 0) { Err "test" "pytest failed" }
} elseif (Test-Path Cargo.toml) {
  cargo build --release; if ($LASTEXITCODE -ne 0) { Err "build" "cargo build failed" }
  cargo test --release; if ($LASTEXITCODE -ne 0) { Err "test" "cargo test failed" }
} else {
  Notice "build" "no build system detected; docs/static repo — skipping build/test"
}

# 4. deploy-dry
Write-Host "== deploy-dry =="
if (Test-Path vercel.json) {
  vercel build --dry-run; if ($LASTEXITCODE -ne 0) { Err "deploy" "vercel dry-run failed" }
} elseif (Test-Path railway.json -or (Test-Path railway.toml)) {
  Notice "deploy" "railway target present; run 'railway up --detach' manually"
} elseif (Test-Path eas.json) {
  npx eas build --platform all --local --no-wait --non-interactive; if ($LASTEXITCODE -ne 0) { Err "deploy" "eas dry build failed" }
} elseif (Test-Path netlify.toml) {
  Notice "deploy" "netlify target present; manual deploy"
} else {
  Notice "deploy" "no deploy target; smoke build already covered"
}

if ($failed) { Write-Host "VERIFY FAILED"; exit 1 }
Write-Host "VERIFY PASSED"
