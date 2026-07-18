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
$firstPythonLookup = $psContent.IndexOf('$python = Find-WorkingPython')
$firstPathRefresh = $psContent.IndexOf('[Environment]::GetEnvironmentVariable("Path", "Machine")')
if ($firstPathRefresh -lt 0 -or $firstPathRefresh -gt $firstPythonLookup) {
    Write-Error "install.ps1 must refresh the persisted user and machine PATH before its first Python lookup"
}
if ($psContent -notmatch 'LOCALAPPDATA.*Programs.*Python') {
    Write-Error "install.ps1 does not search the standard per-user Python installation directory"
}

$fakePython = Join-Path ([System.IO.Path]::GetTempPath()) "agent-setup-fake-python.cmd"
try {
    Set-Content -LiteralPath $fakePython -Encoding ASCII -Value "@echo off`r`nexit /b 1"
    $env:AGENT_SETUP_PYTHON = $fakePython
    $env:AGENT_SETUP_NO_BOOTSTRAP = "1"
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "cmd.exe"
    $startInfo.Arguments = "/d /c `"`"$cmd`" --list`""
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::Start($startInfo)
    $runOutput = $process.StandardOutput.ReadToEnd() + $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    $runExit = $process.ExitCode
    if ($runExit -eq 0) {
        Write-Error "install.cmd should fail when the configured Python command is unusable"
    }
    if ($runOutput -notmatch "working Python") {
        Write-Error "install.cmd should explain that no working Python interpreter was found; output was: $runOutput"
    }
    if ($runOutput -match "CategoryInfo|FullyQualifiedErrorId|Traceback \(most recent call last\)") {
        Write-Error "install.cmd should print a concise error instead of a PowerShell or Python stack trace; output was: $runOutput"
    }
} finally {
    Remove-Item Env:AGENT_SETUP_PYTHON -ErrorAction SilentlyContinue
    Remove-Item Env:AGENT_SETUP_NO_BOOTSTRAP -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $fakePython -ErrorAction SilentlyContinue
}

Write-Output "Windows bootstrap checks passed."
