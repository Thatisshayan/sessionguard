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
if (Test-Path package.json) {
  npm ci; if ($LASTEXITCODE -ne 0) { Err "build" "npm ci failed" }
  npm run build --if-present; if ($LASTEXITCODE -ne 0) { Err "build" "npm build failed" }
  npm test --if-present; if ($LASTEXITCODE -ne 0) { Err "test" "npm test failed" }
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
