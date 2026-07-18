$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$ps1 = Join-Path $root "install.ps1"
$cmd = Join-Path $root "install.cmd"

$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile($ps1, [ref]$tokens, [ref]$errors) | Out-Null
if ($errors.Count -ne 0) {
    Write-Error "install.ps1 has parser errors: $($errors -join '; ')"
}

if (-not (Test-Path -LiteralPath $cmd)) {
    Write-Error "install.cmd is missing"
}

$content = Get-Content -Raw -LiteralPath $cmd
$psContent = Get-Content -Raw -LiteralPath $ps1
if ($content -notmatch '-ExecutionPolicy\s+Bypass') {
    Write-Error "install.cmd does not use a process-scoped execution-policy bypass"
}
if ($content -notmatch '%\*') {
    Write-Error "install.cmd does not forward command-line arguments"
}
if ($psContent -match '(?m)^\s*exit(?:\s|$)') {
    Write-Error "install.ps1 must not terminate the user's existing PowerShell session with exit"
}

$fakePython = Join-Path ([System.IO.Path]::GetTempPath()) "agent-setup-fake-python.cmd"
try {
    Set-Content -LiteralPath $fakePython -Encoding ASCII -Value "@echo off`r`nexit /b 1"
    $env:AGENT_SETUP_PYTHON = $fakePython
    $env:AGENT_SETUP_NO_BOOTSTRAP = "1"
    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $runOutput = (& cmd.exe /d /c "`"$cmd`" --list" 2>&1 | Out-String)
    $runExit = $LASTEXITCODE
    $ErrorActionPreference = $oldErrorActionPreference
    if ($runExit -eq 0) {
        Write-Error "install.cmd should fail when the configured Python command is unusable"
    }
    if ($runOutput -notmatch "working Python") {
        Write-Error "install.cmd should explain that no working Python interpreter was found; output was: $runOutput"
    }
} finally {
    $ErrorActionPreference = "Stop"
    Remove-Item Env:AGENT_SETUP_PYTHON -ErrorAction SilentlyContinue
    Remove-Item Env:AGENT_SETUP_NO_BOOTSTRAP -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $fakePython -ErrorAction SilentlyContinue
}

Write-Output "Windows bootstrap checks passed."
