$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$windowsContent = Get-Content -Raw -LiteralPath (Join-Path $root "install.ps1")
$unixContent = Get-Content -Raw -LiteralPath (Join-Path $root "install.sh")

if ($windowsContent -notmatch "winget\s+install.*Python\.Python\.3\.12") {
    Write-Error "Windows bootstrap does not offer Python installation through winget"
}
foreach ($manager in @("brew install python", "apt-get install", "dnf install", "pacman")) {
    if ($unixContent -notmatch [regex]::Escape($manager)) {
        Write-Error "Unix bootstrap is missing Python support for: $manager"
    }
}
if ($windowsContent -notmatch "AGENT_SETUP_NO_BOOTSTRAP" -or $unixContent -notmatch "AGENT_SETUP_NO_BOOTSTRAP") {
    Write-Error "Bootstrap scripts need an opt-out for managed or test environments"
}

Write-Output "Python bootstrap checks passed."
