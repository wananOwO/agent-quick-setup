$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$psBootstrap = Join-Path $root "bootstrap.ps1"
$shBootstrap = Join-Path $root "bootstrap.sh"

foreach ($path in @($psBootstrap, $shBootstrap)) {
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Error "Missing remote bootstrap: $path"
    }
}

$psContent = Get-Content -Raw -LiteralPath $psBootstrap
$shContent = Get-Content -Raw -LiteralPath $shBootstrap
$psInstallContent = Get-Content -Raw -LiteralPath (Join-Path $root "install.ps1")
$shInstallContent = Get-Content -Raw -LiteralPath (Join-Path $root "install.sh")
$readmeContent = Get-Content -Raw -LiteralPath (Join-Path $root "README.md")
$expectedRepo = "wananOwO/agent-quick-setup"

if ($psContent -notmatch [regex]::Escape($expectedRepo)) {
    Write-Error "bootstrap.ps1 does not target $expectedRepo"
}
if ($shContent -notmatch [regex]::Escape($expectedRepo)) {
    Write-Error "bootstrap.sh does not target $expectedRepo"
}
if ($shContent -match "--no-check-certificate|-k(?:\s|$)") {
    Write-Error "bootstrap.sh disables TLS certificate verification"
}
if ($psContent -notmatch "Expand-Archive") {
    Write-Error "bootstrap.ps1 does not extract the downloaded repository archive"
}
if ($shContent -notmatch "mktemp" -or $shContent -notmatch "trap") {
    Write-Error "bootstrap.sh does not use and clean a temporary directory"
}
if ($shContent -notmatch 'exec\s+3</dev/tty' -or $shContent -notmatch 'install\.sh.*<&3') {
    Write-Error "bootstrap.sh does not preserve /dev/tty for interactive input when its source is piped"
}
if ($psInstallContent -notmatch '\$PSScriptRoot') {
    Write-Error "install.ps1 does not anchor module execution to its own directory"
}
if ($shInstallContent -notmatch 'dirname.*\$0') {
    Write-Error "install.sh does not anchor module execution to its own directory"
}
if ($readmeContent -notmatch 'powershell(?:\.exe)?\s+-NoProfile\s+-ExecutionPolicy\s+Bypass\s+-Command\s+.*(?:Invoke-RestMethod|irm)') {
    Write-Error "README Windows one-liner is not compatible with both CMD and PowerShell"
}

try {
    $env:AGENT_SETUP_ARCHIVE_URL = "not-a-valid-uri"
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "powershell.exe"
    $startInfo.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$psBootstrap`""
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::Start($startInfo)
    $failureOutput = $process.StandardOutput.ReadToEnd() + $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($failureOutput -notmatch "Agent Quick Setup failed:") {
        Write-Error "bootstrap.ps1 does not provide a concise top-level failure message; output was: $failureOutput"
    }
    if ($failureOutput -match "CategoryInfo|FullyQualifiedErrorId") {
        Write-Error "bootstrap.ps1 leaks a PowerShell stack trace; output was: $failureOutput"
    }
} finally {
    Remove-Item Env:AGENT_SETUP_ARCHIVE_URL -ErrorAction SilentlyContinue
}

Write-Output "Remote bootstrap checks passed."
