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
if ($psInstallContent -notmatch '\$PSScriptRoot') {
    Write-Error "install.ps1 does not anchor module execution to its own directory"
}
if ($shInstallContent -notmatch 'dirname.*\$0') {
    Write-Error "install.sh does not anchor module execution to its own directory"
}

Write-Output "Remote bootstrap checks passed."
