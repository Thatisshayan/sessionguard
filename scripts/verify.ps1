# Repo-adaptive governance verification (PowerShell / Windows).
# Mirrors scripts/verify.sh: secret-scan, doc-freshness, build, test, deploy-dry.
# Scoped to $RepoRoot only (does NOT walk outside the repo).
$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRoot

$failed = $false
function Notice($t,$m){ Write-Host "::notice title=$t::$m" }
function Err($t,$m){ Write-Host "::error title=$t::$m"; $script:failed = $true }

# ---------------------------------------------------------------- 1. secret-scan
Write-Host "== secret-scan =="
if (Get-Command gitleaks -ErrorAction SilentlyContinue) {
  gitleaks detect --no-banner --redact
  if ($LASTEXITCODE -ne 0) { Err "secret-scan" "gitleaks found secrets" }
} else {
  # (a) filename-based: private key / credential files must not be committed.
  #     Use git-tracked files only — directory-name exclusions cannot hide committed source.
  $tracked = &{ git ls-files 2>$null } | ForEach-Object { $_ }
  $badFiles = $tracked | Where-Object { $_ -match '\.(p8|p12|pem|key)$' -or $_ -match 'credential' } |
    Where-Object { $_ -notmatch '^audits/private/' }
  if ($badFiles) { Err "secret-scan" "secret files present: $($badFiles -join ', ')" }
  # (b) content-based: scan only git-tracked code/config, require an assigned value.
  $trackedFiles = $tracked | Where-Object { $_ -match '\.(json|env|ts|js|py|yml|yaml|toml|sh)$' }
  $rawHits = $trackedFiles | ForEach-Object {
    $f = Join-Path $RepoRoot $_
    if (Test-Path $f) {
      $m = Select-String -Path $f -Pattern '(API_KEY|SECRET|PRIVATE_KEY|TOKEN|PASSWORD)\s*[=:]\s*["'']?[A-Za-z0-9/+_-]{8,}' -Quiet
      if ($m) { $_ } # Return relative path for matching ignore list
    }
  }

  $hits = $rawHits
  $ignoreFile = Join-Path $RepoRoot '.verify\.secret-scan-ignore.json'
  if (Test-Path $ignoreFile) {
    $ignoreList = Get-Content $ignoreFile | ConvertFrom-Json
    $hits = $rawHits | Where-Object { 
      $currentFile = $_ -replace '\\', '/'
      $isIgnored = $false
      foreach ($item in $ignoreList) {
        if ($item.file -eq $currentFile) { $isIgnored = $true; break }
      }
      -not $isIgnored
    }
  }

  if ($hits) { Err "secret-scan" "possible hardcoded secrets in: $($hits -join ', ')" }
}

# ---------------------------------------------------------------- 2. doc-freshness
Write-Host "== doc-freshness =="
if (-not (Test-Path (Join-Path $RepoRoot 'README.md'))) { Err "doc-freshness" "README.md missing" }
# link integrity (mandatory — fail if tool is unavailable)
$hasMLC = Get-Command markdown-link-check -ErrorAction SilentlyContinue
$hasNPX = Get-Command npx -ErrorAction SilentlyContinue
if (-not $hasMLC -and -not $hasNPX) {
  Err "doc-freshness" "markdown-link-check not installed (required for doc-link validation)"
} else {
  $configFile = Join-Path $RepoRoot '.markdown-link-check.json'
  $mdFiles = Get-ChildItem -Path $RepoRoot -Recurse -Filter *.md -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '[\\/](node_modules|\.git|audits[\\/]private)[\\/]' }
  
  $mdFiles | ForEach-Object -Parallel {
    $cf = $using:configFile
    markdown-link-check -q -c $cf $_.FullName >>$null 2>&1
  } -ThrottleLimit 16

  if ($LASTEXITCODE -ne 0) { Err "doc-freshness" "broken doc links" }
}
# audit age (≤ 30 days, from ISO date in filename, not mtime)
$newestAudit = Get-ChildItem -Path (Join-Path $RepoRoot 'audits') -Recurse -Filter '????-??-??_*.md' -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch '[\\/]audits[\\/]private[\\/]' } |
  Sort-Object Name -Descending | Select-Object -First 1
if (-not $newestAudit) { Err "doc-freshness" "no audit found under audits/" }
else {
  $dateStr = $newestAudit.Name.Substring(0, 10)
  $auditDate = [datetime]::ParseExact($dateStr, 'yyyy-MM-dd', $null)
  $age = ([datetime]::UtcNow.Date - $auditDate).Days
  if ($age -gt 30) { Err "doc-freshness" "newest audit ($dateStr) is $age days old (>30)" }
}
# doc baseline (must exist — bootstrap creates it; verification only validates)
$baselinePath = Join-Path $RepoRoot 'docs/_baseline.json'
if (-not (Test-Path $baselinePath)) {
  Err "doc-freshness" "docs/_baseline.json missing — run bootstrap (apply script) first"
}
$base = 0
if (Test-Path $baselinePath) {
  $m = (Get-Content $baselinePath) -match '"md_count":\s*(\d+)'
  if ($m) { $base = [int]($Matches[1]) }
}
$cur = (Get-ChildItem -Path (Join-Path $RepoRoot 'docs') -Recurse -Filter *.md -ErrorAction SilentlyContinue).Count
if ($cur -lt $base) { Err "doc-freshness" "docs md count $cur < baseline $base (deletion without approval)" }

# ---------------------------------------------------------------- 3. build / test (adaptive)
Write-Host "== build / test =="

# check frontend if present
if (Test-Path (Join-Path $RepoRoot 'frontend')) {
  Write-Host "-- frontend --"
  Push-Location (Join-Path $RepoRoot 'frontend')
  try {
    if (-not (Test-Path 'node_modules')) {
      npm ci; if ($LASTEXITCODE -ne 0) { Err "frontend" "npm ci failed" }
    }
    npx tsc --noEmit; if ($LASTEXITCODE -ne 0) { Err "frontend" "tsc check failed" }
    npm run build; if ($LASTEXITCODE -ne 0) { Err "frontend" "npm run build failed" }
  } finally {
    Pop-Location
  }
}

$PM = $null
if (Test-Path (Join-Path $RepoRoot 'pnpm-lock.yaml')) { $PM = 'pnpm' }
elseif (Test-Path (Join-Path $RepoRoot 'yarn.lock')) { $PM = 'yarn' }
elseif (Test-Path (Join-Path $RepoRoot 'package-lock.json')) { $PM = 'npm' }

function RunTimed($secs, $label, $cmd) {
  $p = Start-Process -NoNewWindow -PassThru $cmd[0] $cmd[1..($cmd.Count-1)]
  $exited = $p.WaitForExit($secs * 1000)
  if (-not $exited) {
    $p.Kill()
    Err $label "timed out after ${secs}s (likely network/install hang)"
  } elseif ($p.ExitCode -ne 0) {
    Err $label "failed (rc=$($p.ExitCode))"
  } else {
    Notice $label "ok"
  }
}

if ($PM) {
  switch ($PM) {
    'pnpm' { RunTimed 300 build @('pnpm','install','--frozen-lockfile') }
    'yarn' { RunTimed 300 build @('yarn','install','--frozen-lockfile') }
    'npm'  { RunTimed 300 build @('npm','ci') }
  }
  if (-not $failed) {
    foreach ($m in @('npm','pnpm','yarn')) {
      if (Get-Command $m -ErrorAction SilentlyContinue) {
        $c = if ($m -eq 'npm') { 'npm run build --if-present' } elseif ($m -eq 'pnpm') { 'pnpm run build --if-present' } else { 'yarn build' }
        Invoke-Expression $c >$null 2>&1; if ($LASTEXITCODE -eq 0) { Notice build "build ok" } else { Err build "build failed" }
        $c = if ($m -eq 'npm') { 'npm test --if-present' } elseif ($m -eq 'pnpm') { 'pnpm test --if-present' } else { 'yarn test' }
        Invoke-Expression $c >$null 2>&1; if ($LASTEXITCODE -eq 0) { Notice test "test ok" } else { Err test "test failed" }
      }
    }
  }
} elseif ((Test-Path (Join-Path $RepoRoot 'pyproject.toml')) -or (Test-Path (Join-Path $RepoRoot 'requirements.txt'))) {
  if (Test-Path (Join-Path $RepoRoot 'requirements.txt')) { pip install -q -r (Join-Path $RepoRoot 'requirements.txt') }
  pytest -q; if ($LASTEXITCODE -ne 0) { Err "test" "pytest failed" }
} elseif (Test-Path (Join-Path $RepoRoot 'Cargo.toml')) {
  cargo build --release; if ($LASTEXITCODE -ne 0) { Err "build" "cargo build failed" }
  cargo test --release; if ($LASTEXITCODE -ne 0) { Err "test" "cargo test failed" }
} else {
  Notice "build" "no build system detected; docs/static repo — skipping build/test"
}

# ---------------------------------------------------------------- 4. deploy-dry
Write-Host "== desktop-bundle smoke =="
if (Test-Path (Join-Path $RepoRoot 'desktop_shell\stage-backend.js')) {
  Write-Host "-- staging bundled backend --"
  node desktop_shell\stage-backend.js; if ($LASTEXITCODE -ne 0) { Err "bundle" "staging script failed" }

  $dest = Join-Path $RepoRoot 'desktop_shell\src-tauri\bundled_app'
  if (Test-Path $dest) {
    # check for residue
    $residue = Get-ChildItem -Path $dest -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue
    $residue += Get-ChildItem -Path $dest -Recurse -Filter "*.db" -ErrorAction SilentlyContinue
    if ($residue) {
      Err "bundle" "staging contains runtime residue: $($residue.Name -join ', ')"
    }
    # minimal startup smoke
    Write-Host "-- backend smoke --"
    $smokeLog = Join-Path $env:TEMP "sg-smoke.log"
    $smokeErr = Join-Path $env:TEMP "sg-smoke-err.log"
    $p = Start-Process -FilePath "python" -ArgumentList "-m uvicorn backend.main:app --host 127.0.0.1 --port 8012 --no-access-log" -NoNewWindow -PassThru -RedirectStandardOutput $smokeLog -RedirectStandardError $smokeErr -Environment @{SESSIONGUARD_DEV_MODE='true'}
    Start-Sleep -Seconds 3
    try {
      $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8012/health" -UseBasicParsing -ErrorAction Stop
      if ($resp.StatusCode -eq 200) {
        Notice "bundle" "bundled backend smoke ok"
      } else {
        Err "bundle" "bundled backend smoke failed"
        if (Test-Path $smokeLog) { Get-Content $smokeLog | Select-Object -Last 10 }
        if (Test-Path $smokeErr) { Get-Content $smokeErr | Select-Object -Last 10 }
      }
    } catch {
      Err "bundle" "bundled backend smoke failed: $($_.Exception.Message)"
      if (Test-Path $smokeLog) { Get-Content $smokeLog | Select-Object -Last 10 }
      if (Test-Path $smokeErr) { Get-Content $smokeErr | Select-Object -Last 10 }
    }
    if ($p) {
      Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
      cmd /c "taskkill /F /T /PID $($p.Id)" >$null 2>&1
    }
  }
}

Write-Host "== deploy-dry =="
if (Test-Path (Join-Path $RepoRoot 'vercel.json')) {
  vercel build --dry-run; if ($LASTEXITCODE -ne 0) { Err "deploy" "vercel dry-run failed" }
} elseif ((Test-Path (Join-Path $RepoRoot 'railway.json')) -or (Test-Path (Join-Path $RepoRoot 'railway.toml'))) {
  Notice "deploy" "railway target present; run 'railway up --detach' manually"
} elseif (Test-Path (Join-Path $RepoRoot 'eas.json')) {
  npx eas build --platform all --local --no-wait --non-interactive; if ($LASTEXITCODE -ne 0) { Err "deploy" "eas dry build failed" }
} elseif (Test-Path (Join-Path $RepoRoot 'netlify.toml')) {
  Notice "deploy" "netlify target present; manual deploy"
} else {
  Notice "deploy" "no deploy target; smoke build already covered"
}

# ---------------------------------------------------------------- 5. directive-lint
# REPO_DIRECTIVE.md is the goal-layer constitution. Every task must trace to a
# Phase/Sprint/Epic id defined in the same file. Orphan tasks = divergence risk.
# ROLLOUT NOTE: missing directive is a Notice (not Err) during P8 rollout so
# repos without one yet don't red-break main. Flip to Err once every portfolio
# repo has a linted REPO_DIRECTIVE.md (see project-sentinel P8).
Write-Host "== directive-lint =="
$dirFile = Join-Path $RepoRoot 'REPO_DIRECTIVE.md'
if (-not (Test-Path $dirFile)) {
  Notice "directive-lint" "REPO_DIRECTIVE.md not present yet (required after P8 rollout)"
} else {
  $text = Get-Content $dirFile -Raw
  $defined = [regex]::Matches($text, '\b(P[0-9]+|S[0-9]+|E[0-9]+)\b') | ForEach-Object { $_.Value } | Sort-Object -Unique
  $orphans = $false
  $taskLines = Select-String -Path $dirFile -Pattern '^\s*- \[ \] T[0-9]+' | ForEach-Object { $_.Line }
  foreach ($line in $taskLines) {
    if ($line -notmatch 'traces-to:') {
      Err "directive-lint" "orphan task (no traces-to): $($line.Substring(0, [Math]::Min(80,$line.Length)))"
      $orphans = $true
    } else {
      $ref = ([regex]::Match($line, 'traces-to:([^|]*)')).Groups[1].Value.Trim() -split '/' | Select-Object -First 1
      if ($defined -notcontains $ref) {
        Err "directive-lint" "task references undefined id '$ref': $($line.Substring(0, [Math]::Min(80,$line.Length)))"
        $orphans = $true
      }
    }
  }
  if (-not $orphans) { Notice "directive-lint" "all tasks trace to a defined phase/sprint/epic" }
}

if ($failed) { Write-Host "VERIFY FAILED"; exit 1 }
Write-Host "VERIFY PASSED"
